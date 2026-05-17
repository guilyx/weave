"""D&D Beyond campaign game log (rolls, etc.) — unofficial REST API."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from weave.ddb.client import DdbAuthRequired, DdbClient, DdbError

logger = logging.getLogger(__name__)

GAME_LOG_REST = "https://game-log-rest-live.dndbeyond.com/v1/getmessages"
USER_DATA_URL = "https://www.dndbeyond.com/mobile/api/v6/user-data"


def parse_game_log_ts(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw.astimezone(timezone.utc)
    s = str(raw).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except ValueError:
        return None


def format_game_log_message(msg: dict[str, Any]) -> str | None:
    """Human-readable line for agent context and UI."""
    event_type = str(msg.get("eventType") or msg.get("event_type") or "")
    data = msg.get("data") or {}
    if not isinstance(data, dict):
        data = {}

    if event_type == "dice/roll/fulfilled":
        ctx = data.get("context") or {}
        name = (ctx.get("name") or "").strip() or "Someone"
        action = (data.get("action") or "Roll").strip()
        rolls = data.get("rolls") or []
        parts: list[str] = []
        for roll in rolls:
            if not isinstance(roll, dict):
                continue
            notation = roll.get("diceNotation") or {}
            formula_bits: list[str] = []
            for s in notation.get("set") or []:
                if isinstance(s, dict):
                    formula_bits.append(f"{s.get('count', '')}{s.get('dieType', '')}")
            formula = "+".join(formula_bits)
            const = notation.get("constant")
            if const not in (None, 0):
                formula += f"{'' if const < 0 else '+'}{const}"
            result = roll.get("result") or {}
            total = result.get("total", "?")
            detail = result.get("text", "")
            rtype = roll.get("rollType") or "roll"
            line = f"{name}: {action} — {rtype}"
            if formula:
                line += f" ({formula})"
            line += f" → {total}"
            if detail and str(detail) != str(total):
                line += f" [{detail}]"
            parts.append(line)
        return "; ".join(parts) if parts else f"{name}: {action}"

    if event_type.endswith("/fulfilled") or event_type:
        label = event_type.split("/")[0].replace("-", " ").title()
        return f"{label}: {data.get('action') or data.get('message') or event_type}"

    return None


async def fetch_ddb_user_id(client: DdbClient) -> int:
    """Resolve D&D Beyond user id (required for game log API)."""
    if not client._cobalt:
        raise DdbAuthRequired("DDB_COBALT_SESSION required for game log")
    token = await client._fetch_bearer_token()
    resp = await client._http.post(
        USER_DATA_URL,
        content=f"token={client._cobalt}",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://www.dndbeyond.com",
            "Referer": "https://www.dndbeyond.com/",
            "Authorization": f"Bearer {token}",
            "Cookie": f"CobaltSession={client._cobalt}",
        },
    )
    if resp.status_code in (401, 403):
        raise DdbAuthRequired("invalid or expired DDB_COBALT_SESSION")
    if resp.status_code >= 400:
        raise DdbError(f"user-data API {resp.status_code}: {resp.text[:200]}")
    body = resp.json()
    if isinstance(body, dict) and body.get("status") == "error":
        raise DdbError(str(body.get("data") or "user-data error"))
    user_id = body.get("userId") if isinstance(body, dict) else None
    if user_id is None:
        raise DdbError("user-data response missing userId")
    return int(user_id)


async def fetch_game_log_messages(
    client: DdbClient,
    *,
    game_id: int,
    user_id: int,
) -> list[dict[str, Any]]:
    """Fetch campaign game log messages. game_id is the DDB campaign id."""
    token = await client._fetch_bearer_token()
    try:
        resp = await client._http.get(
            GAME_LOG_REST,
            params={"gameId": str(game_id), "userId": str(user_id)},
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Origin": "https://www.dndbeyond.com",
                "Referer": f"https://www.dndbeyond.com/campaigns/{game_id}",
            },
        )
    except httpx.HTTPError as exc:
        raise DdbError(f"game log request failed: {exc}") from exc

    if resp.status_code in (401, 403):
        raise DdbAuthRequired("game log access denied — check DDB_COBALT_SESSION and campaign role")
    if resp.status_code >= 400:
        raise DdbError(f"game log API {resp.status_code}: {resp.text[:200]}")

    payload = resp.json()
    if not isinstance(payload, dict):
        raise DdbError("game log response was not an object")
    data = payload.get("data")
    if not isinstance(data, list):
        return []
    return [m for m in data if isinstance(m, dict)]
