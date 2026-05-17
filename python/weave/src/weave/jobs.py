import json
import uuid
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

JOB_QUEUE_KEY = "weave:jobs"


class JobKind(str, Enum):
    TRANSCRIBE_AUDIO = "transcribe_audio"
    AGENT_TICK = "agent_tick"
    REFRESH_CHARACTER = "refresh_character"
    SYNC_GAME_LOG = "sync_game_log"


class TranscribeAudioJob(BaseModel):
    kind: str = "transcribe_audio"
    session_id: UUID
    chunk_id: UUID
    audio_path: str


class AgentTickJob(BaseModel):
    kind: str = "agent_tick"
    session_id: UUID
    force: bool = False


class RefreshCharacterJob(BaseModel):
    kind: str = "refresh_character"
    character_id: UUID


class JobEnvelope(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    kind: str
    session_id: UUID | None = None
    chunk_id: UUID | None = None
    audio_path: str | None = None
    force: bool = False
    character_id: UUID | None = None
    campaign_id: UUID | None = None

    @classmethod
    def transcribe(cls, session_id: UUID, chunk_id: UUID, audio_path: str) -> "JobEnvelope":
        return cls(
            kind=JobKind.TRANSCRIBE_AUDIO.value,
            session_id=session_id,
            chunk_id=chunk_id,
            audio_path=audio_path,
        )

    @classmethod
    def agent_tick(cls, session_id: UUID, force: bool = False) -> "JobEnvelope":
        return cls(kind=JobKind.AGENT_TICK.value, session_id=session_id, force=force)

    @classmethod
    def refresh_character(cls, character_id: UUID) -> "JobEnvelope":
        return cls(kind=JobKind.REFRESH_CHARACTER.value, character_id=character_id)

    @classmethod
    def sync_game_log(cls, campaign_id: UUID, session_id: UUID | None = None) -> "JobEnvelope":
        return cls(
            kind=JobKind.SYNC_GAME_LOG.value,
            session_id=session_id,
            campaign_id=campaign_id,
        )


async def enqueue(redis: Any, job: JobEnvelope | str) -> None:
    payload = job if isinstance(job, str) else job.model_dump_json()
    await redis.lpush(JOB_QUEUE_KEY, payload)
