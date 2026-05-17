"""Extract character portrait URLs from D&D Beyond JSON."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class CharacterPortraits(BaseModel):
    avatar_url: str | None = None
    frame_avatar_url: str | None = None
    small_backdrop_avatar_url: str | None = None
    large_backdrop_avatar_url: str | None = None


def _str_url(value: Any) -> str | None:
    if isinstance(value, str) and value.strip().startswith("http"):
        return value.strip()
    return None


def extract_portraits(root: dict[str, Any]) -> CharacterPortraits:
    decorations = root.get("decorations") or root.get("characterDecorations")
    if isinstance(decorations, dict):
        return CharacterPortraits(
            avatar_url=_str_url(decorations.get("avatarUrl") or decorations.get("avatar_url")),
            frame_avatar_url=_str_url(
                decorations.get("frameAvatarUrl") or decorations.get("frame_avatar_url")
            ),
            small_backdrop_avatar_url=_str_url(
                decorations.get("smallBackdropAvatarUrl")
                or decorations.get("small_backdrop_avatar_url")
            ),
            large_backdrop_avatar_url=_str_url(
                decorations.get("largeBackdropAvatarUrl")
                or decorations.get("large_backdrop_avatar_url")
            ),
        )

    return CharacterPortraits(
        avatar_url=_str_url(root.get("avatarUrl") or root.get("avatar_url")),
        frame_avatar_url=_str_url(root.get("frameAvatarUrl") or root.get("frame_avatar_url")),
        small_backdrop_avatar_url=_str_url(
            root.get("smallBackdropAvatarUrl") or root.get("small_backdrop_avatar_url")
        ),
        large_backdrop_avatar_url=_str_url(
            root.get("largeBackdropAvatarUrl") or root.get("large_backdrop_avatar_url")
        ),
    )


def roster_avatar_url(raw: dict[str, Any]) -> str | None:
    """Best-effort avatar from campaign roster payload."""
    portraits = extract_portraits(raw)
    if portraits.avatar_url:
        return portraits.avatar_url
    for key in ("avatarUrl", "avatar_url", "characterAvatarUrl", "thumbnailUrl"):
        url = _str_url(raw.get(key))
        if url:
            return url
    return None
