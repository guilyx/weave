from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class LiveEvent(BaseModel):
    type: str
    text: str | None = None
    recap: str | None = None
    items: list[str] | None = None
    message: str | None = None
    ts: str | None = None
    kind: str | None = None
    activity_id: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def transcript_delta(cls, text: str) -> "LiveEvent":
        return cls(
            type="transcript_delta",
            text=text,
            ts=datetime.now(timezone.utc).isoformat(),
        )

    @classmethod
    def recap_update(cls, recap: str) -> "LiveEvent":
        return cls(type="recap_update", recap=recap)

    @classmethod
    def chronicle_append(cls, entry: dict[str, Any], recap: str) -> "LiveEvent":
        return cls(
            type="chronicle_append",
            recap=recap,
            meta={"entry": entry},
            activity_id=f"chronicle-{entry.get('id', '')}",
            ts=entry.get("created_at"),
        )

    @classmethod
    def suggestions(cls, items: list[str]) -> "LiveEvent":
        return cls(type="suggestions", items=items)

    @classmethod
    def lore_snippets(cls, items: list[str]) -> "LiveEvent":
        return cls(type="lore_snippets", items=items)

    @classmethod
    def status(cls, message: str) -> "LiveEvent":
        return cls(type="status", message=message)

    @classmethod
    def activity(
        cls,
        *,
        kind: str,
        title: str,
        body: str | None = None,
        meta: dict[str, Any] | None = None,
        activity_id: str | None = None,
    ) -> "LiveEvent":
        return cls(
            type="activity",
            kind=kind,
            message=title,
            text=body,
            meta=meta or {},
            activity_id=activity_id,
            ts=datetime.now(timezone.utc).isoformat(),
        )


async def publish(redis: Any, session_id: UUID, event: LiveEvent) -> None:
    channel = f"session:{session_id}:live"
    await redis.publish(channel, event.model_dump_json())
