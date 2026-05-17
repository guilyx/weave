"""Session viewer mode: DM table chronicle vs player-character POV."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID


def viewer_recap_key(mode: str, character_id: UUID | None) -> str:
    if mode == "player" and character_id is not None:
        return f"player:{character_id}"
    return "dm"


def parse_recaps_by_viewer(raw: Any) -> dict[str, str]:
    if raw is None:
        return {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items() if v}


def recap_for_viewer(
    recaps_by_viewer: dict[str, str],
    mode: str,
    character_id: UUID | None,
    *,
    legacy_recap: str = "",
) -> str:
    key = viewer_recap_key(mode, character_id)
    text = (recaps_by_viewer.get(key) or "").strip()
    if text:
        return text
    if mode == "dm" and legacy_recap.strip():
        return legacy_recap.strip()
    return ""


def merge_recap(
    recaps_by_viewer: dict[str, str],
    mode: str,
    character_id: UUID | None,
    new_recap: str,
) -> dict[str, str]:
    out = dict(recaps_by_viewer)
    out[viewer_recap_key(mode, character_id)] = new_recap
    return out
