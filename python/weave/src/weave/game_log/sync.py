"""Sync D&D Beyond campaign game log into Weave storage."""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

import asyncpg

from weave.ddb.client import DdbAuthRequired, DdbClient, DdbError
from weave.ddb.gamelog import (
    fetch_ddb_user_id,
    fetch_game_log_messages,
    format_game_log_message,
    parse_game_log_ts,
)

logger = logging.getLogger(__name__)


async def list_game_log_for_campaign(
    pool: asyncpg.Pool,
    campaign_id: UUID,
    *,
    limit: int = 80,
) -> list[dict[str, Any]]:
    try:
        rows = await pool.fetch(
            """
            SELECT id, ddb_message_id, event_type, summary, payload, occurred_at, created_at
            FROM campaign_game_log_entries
            WHERE campaign_id = $1
            ORDER BY COALESCE(occurred_at, created_at) DESC
            LIMIT $2
            """,
            campaign_id,
            limit,
        )
    except asyncpg.UndefinedTableError:
        return []
    out: list[dict[str, Any]] = []
    for r in reversed(rows):
        ts = r["occurred_at"] or r["created_at"]
        out.append(
            {
                "id": str(r["id"]),
                "ddb_message_id": r["ddb_message_id"],
                "event_type": r["event_type"],
                "summary": r["summary"],
                "occurred_at": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
            }
        )
    return out


async def sync_campaign_game_log(
    pool: asyncpg.Pool,
    ddb: DdbClient,
    campaign_id: UUID,
    *,
    session_id: UUID | None = None,
    redis_client: Any | None = None,
) -> dict[str, Any]:
    """
    Pull DDB game log for a campaign and persist new entries.
    Requires campaigns.ddb_campaign_id and DDB_COBALT_SESSION.
    """
    row = await pool.fetchrow(
        """
        SELECT id, ddb_campaign_id, ddb_user_id
        FROM campaigns WHERE id = $1
        """,
        campaign_id,
    )
    if not row:
        raise ValueError("campaign not found")
    game_id = row.get("ddb_campaign_id")
    if not game_id:
        raise ValueError("campaign has no ddb_campaign_id — import party from D&D Beyond first")

    user_id = row.get("ddb_user_id")
    if not user_id:
        user_id = await fetch_ddb_user_id(ddb)
        await pool.execute(
            "UPDATE campaigns SET ddb_user_id = $2 WHERE id = $1",
            campaign_id,
            user_id,
        )

    try:
        messages = await fetch_game_log_messages(
            ddb, game_id=int(game_id), user_id=int(user_id)
        )
    except (DdbAuthRequired, DdbError) as exc:
        logger.warning("game log sync failed campaign=%s: %s", campaign_id, exc)
        raise

    inserted = 0
    for msg in messages:
        ddb_id = str(msg.get("id") or "")
        if not ddb_id:
            continue
        event_type = str(msg.get("eventType") or "unknown")
        summary = format_game_log_message(msg)
        if not summary:
            continue
        occurred = parse_game_log_ts(
            msg.get("timestamp") or msg.get("createdAt") or msg.get("date")
        )
        try:
            ins = await pool.fetchrow(
                """
                INSERT INTO campaign_game_log_entries
                    (campaign_id, ddb_message_id, event_type, summary, payload, occurred_at)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6)
                ON CONFLICT (campaign_id, ddb_message_id) DO NOTHING
                RETURNING id
                """,
                campaign_id,
                ddb_id,
                event_type,
                summary,
                json.dumps(msg),
                occurred,
            )
        except asyncpg.UndefinedTableError:
            logger.warning("campaign_game_log_entries missing; run migration 008")
            break
        if ins:
            inserted += 1
            if session_id and redis_client and event_type == "dice/roll/fulfilled":
                from weave.session_activity import log_activity

                await log_activity(
                    pool,
                    redis_client,
                    session_id,
                    event_type="game_log",
                    kind="dice_roll",
                    title="D&D Beyond roll",
                    body=summary,
                    payload={
                        "text": summary,
                        "summary": summary,
                        "ddb_message_id": ddb_id,
                        "event_type": event_type,
                    },
                    activity_id=f"ddb-roll-{ddb_id}",
                )

    await pool.execute(
        "UPDATE campaigns SET game_log_synced_at = NOW() WHERE id = $1",
        campaign_id,
    )
    logger.info(
        "game log sync campaign=%s game_id=%s inserted=%d total_fetched=%d",
        campaign_id,
        game_id,
        inserted,
        len(messages),
    )
    return {
        "campaign_id": str(campaign_id),
        "ddb_campaign_id": int(game_id),
        "inserted": inserted,
        "fetched": len(messages),
    }
