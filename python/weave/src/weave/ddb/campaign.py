"""Parse D&D Beyond campaign roster API responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from weave.ddb.portraits import roster_avatar_url


class DdbRosterEntry(BaseModel):
    ddb_character_id: int
    name: str
    level: int | None = None
    class_summary: str | None = None
    avatar_url: str | None = None


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _entry_from_dict(raw: dict[str, Any]) -> DdbRosterEntry | None:
    cid = _as_int(raw.get("characterId") or raw.get("character_id"))
    if cid is None and (
        raw.get("characterName") or raw.get("character_name") or raw.get("name")
    ):
        cid = _as_int(raw.get("id") or raw.get("entityId"))
    if cid is None:
        return None
    name = (
        raw.get("characterName")
        or raw.get("name")
        or raw.get("character_name")
        or f"Character {cid}"
    )
    level = _as_int(raw.get("level") or raw.get("characterLevel"))
    class_summary = (
        raw.get("className")
        or raw.get("class_name")
        or raw.get("classSummary")
        or raw.get("class_summary")
    )
    if isinstance(class_summary, dict):
        class_summary = class_summary.get("name")
    return DdbRosterEntry(
        ddb_character_id=cid,
        name=str(name),
        level=level,
        class_summary=str(class_summary) if class_summary else None,
        avatar_url=roster_avatar_url(raw),
    )


def _collect_character_dicts(node: Any, out: list[dict[str, Any]]) -> None:
    if isinstance(node, list):
        for item in node:
            _collect_character_dicts(item, out)
        return
    if not isinstance(node, dict):
        return
    if _entry_from_dict(node) is not None:
        out.append(node)
    for value in node.values():
        if isinstance(value, (dict, list)):
            _collect_character_dicts(value, out)


def parse_campaign_roster(payload: Any) -> list[DdbRosterEntry]:
    """Normalize active-characters (or similar) JSON into roster entries."""
    raw_items: list[dict[str, Any]] = []
    _collect_character_dicts(payload, raw_items)

    seen: set[int] = set()
    entries: list[DdbRosterEntry] = []
    for raw in raw_items:
        entry = _entry_from_dict(raw)
        if entry and entry.ddb_character_id not in seen:
            seen.add(entry.ddb_character_id)
            entries.append(entry)

    entries.sort(key=lambda e: e.name.lower())
    return entries
