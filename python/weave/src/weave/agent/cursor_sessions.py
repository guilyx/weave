"""Persist Cursor CLI session_id per Weave session for multi-turn context."""

from __future__ import annotations

import logging

from weave.config import settings

logger = logging.getLogger(__name__)

_redis = None


def _redis_client():
    global _redis
    if _redis is None:
        try:
            import redis

            _redis = redis.from_url(settings.redis_url, decode_responses=True)
        except Exception as exc:
            logger.warning("Redis unavailable for Cursor sessions: %s", exc)
            _redis = False
    return _redis if _redis is not False else None


def get_cursor_session(weave_session_id: str) -> str | None:
    client = _redis_client()
    if not client:
        return None
    return client.get(f"session:{weave_session_id}:cursor_chat")


def set_cursor_session(weave_session_id: str, cursor_session_id: str) -> None:
    client = _redis_client()
    if not client:
        return
    client.set(f"session:{weave_session_id}:cursor_chat", cursor_session_id, ex=86400 * 7)
