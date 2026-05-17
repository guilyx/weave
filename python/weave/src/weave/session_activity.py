"""Session activity feed: DB events + chat messages → unified timeline."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import asyncpg

from weave.live import LiveEvent, publish

# Shown in default session log (AI outputs only).
AI_FEED_KINDS = frozenset({"recap", "chronicle", "suggestion", "memory", "chat_assistant"})
NOTE_FEED_KINDS = frozenset({"note"})
PIPELINE_KINDS = frozenset(
    {
        "audio_chunk",
        "transcript",
        "agent_queued",
        "agent_done",
        "system",
        "chat_user",
        "dice_roll",
        "game_log",
    }
)


async def insert_event(
    pool: asyncpg.Pool,
    session_id: UUID,
    event_type: str,
    payload: dict[str, Any],
) -> UUID:
    row = await pool.fetchrow(
        """
        INSERT INTO session_events (session_id, event_type, payload)
        VALUES ($1, $2, $3::jsonb)
        RETURNING id
        """,
        session_id,
        event_type,
        json.dumps(payload),
    )
    return row["id"]


def activity_item_id(event_id: UUID) -> str:
    return f"event-{event_id}"


async def log_activity(
    pool: asyncpg.Pool,
    redis_client: Any,
    session_id: UUID,
    *,
    event_type: str,
    kind: str,
    title: str,
    body: str | None = None,
    payload: dict[str, Any] | None = None,
    activity_id: str | None = None,
) -> str:
    """Persist event and push a WebSocket activity item with a stable id."""
    data = dict(payload or {})
    if body is not None and "text" not in data and event_type in ("note", "transcript", "recap"):
        data["text"] = body
    if activity_id:
        data["_activity_id"] = activity_id
    event_id = await insert_event(pool, session_id, event_type, data)
    item_id = activity_id or activity_item_id(event_id)
    await publish(
        redis_client,
        session_id,
        LiveEvent.activity(
            kind=kind,
            title=title,
            body=body,
            meta=data,
            activity_id=item_id,
        ),
    )
    return item_id


async def append_session_story(pool: asyncpg.Pool, session_id: UUID, line: str) -> None:
    text = line.strip()
    if not text:
        return
    await pool.execute(
        """
        UPDATE sessions
        SET story = CASE
            WHEN COALESCE(story, '') = '' THEN $2
            ELSE story || E'\n' || $2
        END
        WHERE id = $1
        """,
        session_id,
        text,
    )


def _event_to_item(row: dict[str, Any]) -> dict[str, Any]:
    event_type = row["event_type"]
    payload = row.get("payload")
    if payload is None:
        payload = {}
    elif isinstance(payload, str):
        payload = json.loads(payload)
    elif not isinstance(payload, dict):
        payload = {}

    ts = row["ts"].isoformat() if hasattr(row["ts"], "isoformat") else str(row["ts"])
    item_id = activity_item_id(row["id"])

    if event_type == "audio_chunk":
        size_kb = (payload.get("bytes") or 0) / 1024
        return {
            "id": item_id,
            "kind": "audio_chunk",
            "ts": ts,
            "title": "Audio",
            "body": f"{size_kb:.0f} KB",
            "meta": payload,
        }
    if event_type == "transcript":
        text = payload.get("text") or ""
        return {
            "id": item_id,
            "kind": "transcript",
            "ts": ts,
            "title": "Heard",
            "body": text,
            "meta": payload,
        }
    if event_type == "note":
        return {
            "id": item_id,
            "kind": "note",
            "ts": ts,
            "title": "Note",
            "body": payload.get("text") or "",
            "meta": payload,
        }
    if event_type == "memory":
        return {
            "id": item_id,
            "kind": "memory",
            "ts": ts,
            "title": "Memory",
            "body": payload.get("text") or "",
            "meta": payload,
        }
    if event_type == "recap":
        stable_id = payload.get("_activity_id") or item_id
        is_chronicle = bool(payload.get("entry"))
        return {
            "id": stable_id,
            "kind": "chronicle" if is_chronicle else "recap",
            "ts": ts,
            "title": "Chronicle" if is_chronicle else "Recap update",
            "body": (payload.get("entry") or {}).get("body")
            or payload.get("text")
            or "",
            "meta": payload,
        }
    if event_type == "game_log":
        return {
            "id": payload.get("_activity_id") or item_id,
            "kind": "dice_roll",
            "ts": ts,
            "title": "D&D Beyond roll",
            "body": payload.get("text") or payload.get("summary") or "",
            "meta": payload,
        }
    if event_type == "suggestion":
        items = payload.get("items") or []
        return {
            "id": item_id,
            "kind": "suggestion",
            "ts": ts,
            "title": "Suggestions",
            "body": "\n".join(f"• {s}" for s in items) if items else None,
            "meta": payload,
        }
    if event_type == "agent_queued":
        return {
            "id": item_id,
            "kind": "agent_queued",
            "ts": ts,
            "title": "Recap queued",
            "body": payload.get("reason"),
            "meta": payload,
        }
    if event_type == "agent_done":
        return {
            "id": item_id,
            "kind": "agent_done",
            "ts": ts,
            "title": "Recap done",
            "body": payload.get("summary") or "",
            "meta": payload,
        }
    if event_type == "system":
        return {
            "id": item_id,
            "kind": "system",
            "ts": ts,
            "title": payload.get("title") or "System",
            "body": payload.get("body"),
            "meta": payload,
        }
    return {
        "id": item_id,
        "kind": event_type,
        "ts": ts,
        "title": event_type.replace("_", " ").title(),
        "body": json.dumps(payload) if payload else None,
        "meta": payload,
    }


def _message_to_item(row: dict[str, Any]) -> dict[str, Any]:
    ts = row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(
        row["created_at"]
    )
    role = row["role"]
    return {
        "id": f"msg-{row['id']}",
        "kind": "chat_user" if role == "user" else "chat_assistant",
        "ts": ts,
        "title": "You" if role == "user" else "Weave",
        "body": row["content"],
        "meta": {"role": role},
    }


async def persist_memory(pool: asyncpg.Pool, session_id: UUID, summary: str) -> UUID:
    row = await pool.fetchrow(
        """
        INSERT INTO session_memory (session_id, summary)
        VALUES ($1, $2)
        RETURNING id
        """,
        session_id,
        summary.strip(),
    )
    return row["id"]


async def fetch_activity_feed(
    pool: asyncpg.Pool,
    session_id: UUID,
    feed: str = "ai",
) -> list[dict[str, Any]]:
    events = await pool.fetch(
        """
        SELECT id, event_type, payload, ts
        FROM session_events WHERE session_id = $1 ORDER BY ts ASC
        """,
        session_id,
    )
    messages = await pool.fetch(
        """
        SELECT id, role, content, created_at
        FROM session_messages WHERE session_id = $1 ORDER BY created_at ASC
        """,
        session_id,
    )
    items: list[dict[str, Any]] = []
    items.extend(_event_to_item(dict(r)) for r in events)
    if feed in ("ai", "full"):
        try:
            memory_rows = await pool.fetch(
                """
                SELECT id, summary, created_at
                FROM session_memory WHERE session_id = $1 ORDER BY created_at ASC
                """,
                session_id,
            )
            for r in memory_rows:
                ts = (
                    r["created_at"].isoformat()
                    if hasattr(r["created_at"], "isoformat")
                    else str(r["created_at"])
                )
                items.append(
                    {
                        "id": f"memory-{r['id']}",
                        "kind": "memory",
                        "ts": ts,
                        "title": "Memory",
                        "body": r["summary"],
                        "meta": {},
                    }
                )
        except asyncpg.UndefinedTableError:
            pass
    if feed in ("full", "chat", "ai"):
        items.extend(_message_to_item(dict(r)) for r in messages)
    items.sort(key=lambda x: x["ts"])

    if feed == "ai":
        return [i for i in items if i["kind"] in AI_FEED_KINDS]
    if feed == "notes":
        return [i for i in items if i["kind"] in NOTE_FEED_KINDS]
    if feed == "pipeline":
        return [i for i in items if i["kind"] in PIPELINE_KINDS]
    if feed == "chat":
        return [i for i in items if i["kind"] in ("chat_user", "chat_assistant")]
    return items
