import json
from pathlib import Path
from typing import Literal
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from weave.agent import run_agent_chat
from weave.agent.context import load_agent_context
from weave.agent.viewpoint import parse_recaps_by_viewer, recap_for_viewer
from weave.chronicle import (
    join_entries_text,
    list_chronicle_entries,
    viewer_key_for_mode,
)
from weave.config import settings
from weave.ddb.client import DdbAuthRequired, DdbClient, DdbError, DdbNotFound
from weave.ddb.models import CharacterSheet
from weave.deps import get_ddb, get_pool, get_redis, require_api_key
from weave.jobs import JobEnvelope, enqueue
from weave.live import LiveEvent, publish
from weave.session_activity import activity_item_id, fetch_activity_feed, insert_event, log_activity
from weave.tts import synthesize_speech

router = APIRouter(dependencies=[Depends(require_api_key)])


def _row(row: asyncpg.Record | None) -> dict | None:
    return dict(row) if row else None


def _rows(rows: list[asyncpg.Record]) -> list[dict]:
    return [dict(r) for r in rows]


async def _require_session(pool: asyncpg.Pool, session_id: UUID) -> asyncpg.Record:
    row = await pool.fetchrow("SELECT * FROM sessions WHERE id = $1", session_id)
    if not row:
        raise HTTPException(404, "session not found")
    return row


# --- schemas ---


class CreateCampaign(BaseModel):
    name: str
    description: str | None = None


class UpdateCampaign(BaseModel):
    name: str | None = None
    description: str | None = None
    ai_brief: str | None = None


class LinkCharacter(BaseModel):
    ddb_character_id: int


class ImportDdbParty(BaseModel):
    ddb_campaign_id: int
    ddb_character_ids: list[int] = Field(min_length=1)
    primary_ddb_character_id: int | None = None


class CreateLore(BaseModel):
    title: str
    content: str


class CreateSession(BaseModel):
    title: str | None = None


class AddNote(BaseModel):
    text: str


class PostMessage(BaseModel):
    content: str


class SessionViewpoint(BaseModel):
    mode: Literal["dm", "player"] = "dm"
    character_id: UUID | None = None


class TtsRequest(BaseModel):
    text: str


# --- campaigns ---


@router.get("/api/v1/campaigns")
async def list_campaigns(pool: asyncpg.Pool = Depends(get_pool)) -> list[dict]:
    return _rows(await pool.fetch("SELECT * FROM campaigns ORDER BY created_at DESC"))


@router.post("/api/v1/campaigns")
async def create_campaign(
    body: CreateCampaign,
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict:
    row = await pool.fetchrow(
        "INSERT INTO campaigns (name, description) VALUES ($1, $2) RETURNING *",
        body.name,
        body.description,
    )
    return _row(row)  # type: ignore[return-value]


@router.get("/api/v1/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: UUID,
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict:
    row = await pool.fetchrow("SELECT * FROM campaigns WHERE id = $1", campaign_id)
    if not row:
        raise HTTPException(404, "campaign not found")
    return dict(row)


@router.patch("/api/v1/campaigns/{campaign_id}")
async def update_campaign(
    campaign_id: UUID,
    body: UpdateCampaign,
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict:
    row = await pool.fetchrow(
        """
        UPDATE campaigns SET
            name = COALESCE($2, name),
            description = COALESCE($3, description),
            ai_brief = COALESCE($4, ai_brief),
            updated_at = NOW()
        WHERE id = $1 RETURNING *
        """,
        campaign_id,
        body.name,
        body.description,
        body.ai_brief,
    )
    if not row:
        raise HTTPException(404, "campaign not found")
    return dict(row)


@router.get("/api/v1/campaigns/{campaign_id}/game-log")
async def get_campaign_game_log(
    campaign_id: UUID,
    pool: asyncpg.Pool = Depends(get_pool),
    limit: int = 100,
) -> dict:
    exists = await pool.fetchval(
        "SELECT EXISTS(SELECT 1 FROM campaigns WHERE id = $1)", campaign_id
    )
    if not exists:
        raise HTTPException(404, "campaign not found")
    from weave.game_log.sync import list_game_log_for_campaign

    entries = await list_game_log_for_campaign(pool, campaign_id, limit=min(limit, 200))
    synced = await pool.fetchval(
        "SELECT game_log_synced_at FROM campaigns WHERE id = $1", campaign_id
    )
    ddb_id = await pool.fetchval(
        "SELECT ddb_campaign_id FROM campaigns WHERE id = $1", campaign_id
    )
    return {
        "campaign_id": str(campaign_id),
        "ddb_campaign_id": int(ddb_id) if ddb_id else None,
        "game_log_synced_at": synced.isoformat() if synced and hasattr(synced, "isoformat") else None,
        "entries": entries,
    }


@router.post("/api/v1/campaigns/{campaign_id}/sync-game-log")
async def sync_campaign_game_log_endpoint(
    campaign_id: UUID,
    pool: asyncpg.Pool = Depends(get_pool),
    ddb: DdbClient = Depends(get_ddb),
    redis_client=Depends(get_redis),
) -> dict:
    from weave.game_log.sync import sync_campaign_game_log

    try:
        return await sync_campaign_game_log(pool, ddb, campaign_id, redis_client=redis_client)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except DdbAuthRequired as exc:
        raise HTTPException(401, str(exc)) from exc
    except DdbError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.get("/api/v1/campaigns/{campaign_id}/lore")
async def list_lore(
    campaign_id: UUID,
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[dict]:
    return _rows(
        await pool.fetch(
            "SELECT * FROM campaign_lore WHERE campaign_id = $1 ORDER BY created_at", campaign_id
        )
    )


@router.post("/api/v1/campaigns/{campaign_id}/lore")
async def create_lore(
    campaign_id: UUID,
    body: CreateLore,
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict:
    exists = await pool.fetchval("SELECT EXISTS(SELECT 1 FROM campaigns WHERE id = $1)", campaign_id)
    if not exists:
        raise HTTPException(404, "campaign not found")
    row = await pool.fetchrow(
        """
        INSERT INTO campaign_lore (campaign_id, title, content)
        VALUES ($1, $2, $3) RETURNING *
        """,
        campaign_id,
        body.title,
        body.content,
    )
    return dict(row)  # type: ignore[arg-type]


# --- D&D Beyond campaign roster ---


@router.get("/api/v1/ddb/campaigns/{ddb_campaign_id}/roster")
async def ddb_campaign_roster(
    ddb_campaign_id: int,
    ddb: DdbClient = Depends(get_ddb),
) -> list[dict]:
    try:
        roster = await ddb.fetch_campaign_roster(ddb_campaign_id)
    except DdbNotFound:
        raise HTTPException(404, "D&D Beyond campaign not found") from None
    except DdbAuthRequired as exc:
        raise HTTPException(401, detail=str(exc)) from None
    except DdbError as exc:
        raise HTTPException(502, detail=str(exc)) from None
    except Exception as exc:
        raise HTTPException(502, detail=f"D&D Beyond roster failed: {exc}") from exc
    return [entry.model_dump() for entry in roster]


class DdbSheetBatchRequest(BaseModel):
    ddb_character_ids: list[int] = Field(min_length=1, max_length=24)


@router.get("/api/v1/ddb/characters/{ddb_character_id}/sheet")
async def ddb_character_sheet(
    ddb_character_id: int,
    ddb: DdbClient = Depends(get_ddb),
) -> dict:
    try:
        sheet = await ddb.fetch_character(ddb_character_id)
    except DdbNotFound:
        raise HTTPException(404, "character not found on D&D Beyond") from None
    except DdbAuthRequired as exc:
        raise HTTPException(401, detail=str(exc)) from None
    except DdbError as exc:
        raise HTTPException(502, detail=str(exc)) from None
    return sheet.model_dump()


@router.get("/api/v1/ddb/characters/{ddb_character_id}/avatar")
async def ddb_character_avatar(
    ddb_character_id: int,
    kind: str = "avatar",
    ddb: DdbClient = Depends(get_ddb),
) -> Response:
    """Proxy D&D Beyond portrait (avatar / frame / backdrop) with your Cobalt session."""
    try:
        content, media_type = await ddb.fetch_portrait_bytes(ddb_character_id, kind=kind)
    except DdbNotFound:
        raise HTTPException(404, "portrait not found") from None
    except DdbAuthRequired as exc:
        raise HTTPException(401, detail=str(exc)) from None
    except DdbError as exc:
        raise HTTPException(502, detail=str(exc)) from None
    return Response(content=content, media_type=media_type)


@router.post("/api/v1/ddb/characters/sheets")
async def ddb_character_sheets_batch(
    body: DdbSheetBatchRequest,
    ddb: DdbClient = Depends(get_ddb),
) -> list[dict]:
    sheets: list[dict] = []
    errors: list[str] = []
    for ddb_id in body.ddb_character_ids:
        try:
            sheet = await ddb.fetch_character(ddb_id)
            sheets.append(sheet.model_dump())
        except DdbNotFound:
            errors.append(f"{ddb_id}: not found")
        except DdbAuthRequired as exc:
            raise HTTPException(401, detail=str(exc)) from None
        except DdbError as exc:
            errors.append(f"{ddb_id}: {exc}")
    if not sheets and errors:
        raise HTTPException(502, detail="; ".join(errors))
    return sheets


# --- characters ---


async def _upsert_character(
    pool: asyncpg.Pool,
    campaign_id: UUID,
    sheet: CharacterSheet,
    *,
    is_primary: bool = False,
) -> dict:
    row = await pool.fetchrow(
        """
        INSERT INTO characters (campaign_id, ddb_character_id, snapshot, last_synced_at, is_primary)
        VALUES ($1, $2, $3::jsonb, NOW(), $4)
        ON CONFLICT (campaign_id, ddb_character_id)
        DO UPDATE SET
            snapshot = EXCLUDED.snapshot,
            last_synced_at = NOW(),
            is_primary = EXCLUDED.is_primary
        RETURNING *
        """,
        campaign_id,
        sheet.ddb_character_id,
        sheet.model_dump_json(),
        is_primary,
    )
    return dict(row)  # type: ignore[arg-type]


@router.post("/api/v1/campaigns/{campaign_id}/import-ddb-party")
async def import_ddb_party(
    campaign_id: UUID,
    body: ImportDdbParty,
    pool: asyncpg.Pool = Depends(get_pool),
    ddb: DdbClient = Depends(get_ddb),
) -> dict:
    exists = await pool.fetchval("SELECT EXISTS(SELECT 1 FROM campaigns WHERE id = $1)", campaign_id)
    if not exists:
        raise HTTPException(404, "campaign not found")

    if body.primary_ddb_character_id is not None and body.primary_ddb_character_id not in body.ddb_character_ids:
        raise HTTPException(400, "primary character must be included in ddb_character_ids")

    try:
        await ddb.fetch_campaign_roster(body.ddb_campaign_id)
    except DdbNotFound:
        raise HTTPException(404, "D&D Beyond campaign not found") from None
    except DdbAuthRequired as exc:
        raise HTTPException(401, str(exc)) from None
    except DdbError as exc:
        raise HTTPException(502, str(exc)) from None

    await pool.execute(
        "UPDATE campaigns SET ddb_campaign_id = $2, updated_at = NOW() WHERE id = $1",
        campaign_id,
        body.ddb_campaign_id,
    )
    await pool.execute(
        "UPDATE characters SET is_primary = FALSE WHERE campaign_id = $1",
        campaign_id,
    )

    linked: list[dict] = []
    failed: list[dict] = []
    for ddb_id in body.ddb_character_ids:
        try:
            sheet = await ddb.fetch_character(ddb_id)
        except DdbNotFound:
            failed.append(
                {"ddb_character_id": ddb_id, "error": "not found on D&D Beyond"}
            )
            continue
        except DdbAuthRequired as exc:
            raise HTTPException(401, detail=str(exc)) from None
        except DdbError as exc:
            failed.append({"ddb_character_id": ddb_id, "error": str(exc)})
            continue
        except Exception as exc:
            failed.append({"ddb_character_id": ddb_id, "error": str(exc)})
            continue
        is_primary = body.primary_ddb_character_id == ddb_id
        linked.append(await _upsert_character(pool, campaign_id, sheet, is_primary=is_primary))

    if not linked and failed:
        detail = "; ".join(f"{f['ddb_character_id']}: {f['error']}" for f in failed)
        raise HTTPException(502, detail=detail)
    return {"linked": linked, "count": len(linked), "failed": failed}


@router.get("/api/v1/campaigns/{campaign_id}/characters")
async def list_characters(
    campaign_id: UUID,
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[dict]:
    return _rows(
        await pool.fetch(
            "SELECT * FROM characters WHERE campaign_id = $1 ORDER BY created_at", campaign_id
        )
    )


@router.post("/api/v1/campaigns/{campaign_id}/characters")
async def link_character(
    campaign_id: UUID,
    body: LinkCharacter,
    pool: asyncpg.Pool = Depends(get_pool),
    ddb: DdbClient = Depends(get_ddb),
) -> dict:
    try:
        sheet = await ddb.fetch_character(body.ddb_character_id)
    except DdbNotFound:
        raise HTTPException(404, "character not found on D&D Beyond") from None
    except DdbAuthRequired:
        raise HTTPException(401, "DDB auth required: set DDB_COBALT_SESSION") from None
    except Exception as exc:
        raise HTTPException(502, str(exc)) from exc

    return await _upsert_character(pool, campaign_id, sheet, is_primary=False)


@router.post("/api/v1/campaigns/{campaign_id}/characters/{character_id}/set-primary")
async def set_primary_character(
    campaign_id: UUID,
    character_id: UUID,
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict:
    row = await pool.fetchrow(
        "SELECT id FROM characters WHERE id = $1 AND campaign_id = $2",
        character_id,
        campaign_id,
    )
    if not row:
        raise HTTPException(404, "character not found")
    await pool.execute(
        "UPDATE characters SET is_primary = FALSE WHERE campaign_id = $1",
        campaign_id,
    )
    updated = await pool.fetchrow(
        "UPDATE characters SET is_primary = TRUE WHERE id = $1 RETURNING *",
        character_id,
    )
    return dict(updated)  # type: ignore[arg-type]


@router.get("/api/v1/campaigns/{campaign_id}/characters/{character_id}")
async def get_character(
    campaign_id: UUID,
    character_id: UUID,
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict:
    row = await pool.fetchrow(
        "SELECT * FROM characters WHERE id = $1 AND campaign_id = $2",
        character_id,
        campaign_id,
    )
    if not row:
        raise HTTPException(404, "character not found")
    return dict(row)


@router.post("/api/v1/campaigns/{campaign_id}/characters/{character_id}")
async def refresh_character(
    campaign_id: UUID,
    character_id: UUID,
    pool: asyncpg.Pool = Depends(get_pool),
    ddb: DdbClient = Depends(get_ddb),
) -> dict:
    row = await pool.fetchrow(
        "SELECT * FROM characters WHERE id = $1 AND campaign_id = $2",
        character_id,
        campaign_id,
    )
    if not row:
        raise HTTPException(404, "character not found")
    try:
        sheet = await ddb.fetch_character(int(row["ddb_character_id"]))
    except DdbNotFound:
        raise HTTPException(404, "character not found on D&D Beyond") from None
    except DdbAuthRequired:
        raise HTTPException(401, "DDB auth required") from None
    updated = await pool.fetchrow(
        """
        UPDATE characters SET snapshot = $2::jsonb, last_synced_at = NOW()
        WHERE id = $1 RETURNING *
        """,
        character_id,
        sheet.model_dump_json(),
    )
    return dict(updated)  # type: ignore[arg-type]


# --- sessions ---


@router.get("/api/v1/campaigns/{campaign_id}/sessions")
async def list_sessions(
    campaign_id: UUID,
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[dict]:
    return _rows(
        await pool.fetch(
            "SELECT * FROM sessions WHERE campaign_id = $1 ORDER BY created_at DESC", campaign_id
        )
    )


@router.post("/api/v1/campaigns/{campaign_id}/sessions")
async def create_session(
    campaign_id: UUID,
    body: CreateSession,
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict:
    row = await pool.fetchrow(
        """
        INSERT INTO sessions (campaign_id, title, status)
        VALUES ($1, $2, 'planned') RETURNING *
        """,
        campaign_id,
        body.title,
    )
    return dict(row)  # type: ignore[arg-type]


@router.get("/api/v1/sessions/{session_id}")
async def get_session(
    session_id: UUID,
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict:
    row = await pool.fetchrow("SELECT * FROM sessions WHERE id = $1", session_id)
    if not row:
        raise HTTPException(404, "session not found")
    return dict(row)


@router.post("/api/v1/sessions/{session_id}/start")
async def start_session(
    session_id: UUID,
    pool: asyncpg.Pool = Depends(get_pool),
    redis_client=Depends(get_redis),
) -> dict:
    row = await pool.fetchrow(
        """
        UPDATE sessions SET status = 'active', started_at = COALESCE(started_at, NOW())
        WHERE id = $1 RETURNING *
        """,
        session_id,
    )
    if not row:
        raise HTTPException(404, "session not found")
    await log_activity(
        pool,
        redis_client,
        session_id,
        event_type="system",
        kind="system",
        title="Session started",
        body="Mic and notes are ready.",
        payload={"title": "Session started", "body": "Recording may begin."},
    )
    campaign_id = row["campaign_id"]
    has_ddb = await pool.fetchval(
        "SELECT ddb_campaign_id IS NOT NULL FROM campaigns WHERE id = $1",
        campaign_id,
    )
    if has_ddb:
        await enqueue(
            redis_client,
            JobEnvelope.sync_game_log(campaign_id, session_id=session_id),
        )
    return dict(row)


@router.post("/api/v1/sessions/{session_id}/end")
async def end_session(
    session_id: UUID,
    pool: asyncpg.Pool = Depends(get_pool),
    redis_client=Depends(get_redis),
) -> dict:
    row = await pool.fetchrow(
        "UPDATE sessions SET status = 'ended', ended_at = NOW() WHERE id = $1 RETURNING *",
        session_id,
    )
    if not row:
        raise HTTPException(404, "session not found")
    await log_activity(
        pool,
        redis_client,
        session_id,
        event_type="system",
        kind="system",
        title="Session ended",
        body="Final recap queued.",
        payload={"title": "Session ended", "body": "Final agent recap queued."},
    )
    await enqueue(redis_client, JobEnvelope.agent_tick(session_id, force=True))
    return dict(row)


@router.post("/api/v1/sessions/{session_id}/notes")
async def add_note(
    session_id: UUID,
    body: AddNote,
    pool: asyncpg.Pool = Depends(get_pool),
    redis_client=Depends(get_redis),
) -> dict:
    event_id = await insert_event(pool, session_id, "note", {"text": body.text})
    await publish(
        redis_client,
        session_id,
        LiveEvent.activity(
            kind="note",
            title="Note",
            body=body.text,
            activity_id=activity_item_id(event_id),
        ),
    )
    await enqueue(redis_client, JobEnvelope.agent_tick(session_id))
    row = await pool.fetchrow(
        "SELECT * FROM session_events WHERE id = $1", event_id
    )
    return dict(row)  # type: ignore[arg-type]


@router.post("/api/v1/sessions/{session_id}/audio-chunks")
async def upload_audio(
    session_id: UUID,
    pool: asyncpg.Pool = Depends(get_pool),
    redis_client=Depends(get_redis),
    audio: UploadFile = File(...),
) -> dict:
    import uuid

    await _require_session(pool, session_id)

    data_dir = Path(settings.data_dir) / "audio"
    data_dir.mkdir(parents=True, exist_ok=True)
    chunk_id = uuid.uuid4()
    path = data_dir / f"{session_id}_{chunk_id}.webm"
    content = await audio.read()
    path.write_bytes(content)

    await pool.execute(
        """
        INSERT INTO audio_chunks (id, session_id, storage_path, content_type)
        VALUES ($1, $2, $3, $4)
        """,
        chunk_id,
        session_id,
        str(path),
        audio.content_type,
    )
    # Pipeline only — not shown in default AI activity feed.
    await insert_event(
        pool,
        session_id,
        "audio_chunk",
        {
            "chunk_id": str(chunk_id),
            "bytes": len(content),
            "content_type": audio.content_type,
        },
    )
    await enqueue(redis_client, JobEnvelope.transcribe(session_id, chunk_id, str(path)))
    return {"chunk_id": str(chunk_id), "queued": True}


async def _chronicle_payload_for_session(pool: asyncpg.Pool, row: asyncpg.Record) -> dict:
    session_id = row["id"]
    mode = str(row.get("viewer_mode") or "dm")
    char_id = row.get("viewer_character_id")
    vkey = viewer_key_for_mode(mode, char_id)
    entries = await list_chronicle_entries(pool, session_id, vkey)
    recaps_map = parse_recaps_by_viewer(row.get("recaps_by_viewer"))
    legacy = recap_for_viewer(recaps_map, mode, char_id, legacy_recap=row.get("recap") or "")
    if not entries and legacy:
        from weave.chronicle import ensure_legacy_recap_migrated

        entries = await ensure_legacy_recap_migrated(pool, session_id, vkey, legacy)
    text = join_entries_text(entries) or legacy
    return {
        "recap": text,
        "entries": entries,
        "viewer_mode": mode,
        "viewer_character_id": str(char_id) if char_id else None,
        "viewer_key": vkey,
    }


@router.get("/api/v1/sessions/{session_id}/recap")
async def get_recap(session_id: UUID, pool: asyncpg.Pool = Depends(get_pool)) -> dict:
    row = await pool.fetchrow(
        """
        SELECT id, recap, COALESCE(viewer_mode, 'dm') AS viewer_mode, viewer_character_id,
               COALESCE(recaps_by_viewer, '{}'::jsonb) AS recaps_by_viewer
        FROM sessions WHERE id = $1
        """,
        session_id,
    )
    if not row:
        raise HTTPException(404, "session not found")
    return await _chronicle_payload_for_session(pool, row)


@router.patch("/api/v1/sessions/{session_id}/viewpoint")
async def set_viewpoint(
    session_id: UUID,
    body: SessionViewpoint,
    pool: asyncpg.Pool = Depends(get_pool),
    redis_client=Depends(get_redis),
) -> dict:
    session = await _require_session(pool, session_id)
    mode = body.mode
    char_id = body.character_id

    if mode == "player":
        if not char_id:
            raise HTTPException(400, "character_id required for player viewpoint")
        char_row = await pool.fetchrow(
            "SELECT id FROM characters WHERE id = $1 AND campaign_id = $2",
            char_id,
            session["campaign_id"],
        )
        if not char_row:
            raise HTTPException(404, "character not found in this campaign")
    else:
        char_id = None

    row = await pool.fetchrow(
        """
        UPDATE sessions
        SET viewer_mode = $2, viewer_character_id = $3
        WHERE id = $1
        RETURNING id, recap, COALESCE(recaps_by_viewer, '{}'::jsonb) AS recaps_by_viewer,
                  COALESCE(viewer_mode, 'dm') AS viewer_mode, viewer_character_id
        """,
        session_id,
        mode,
        char_id,
    )
    if not row:
        raise HTTPException(404, "session not found")

    payload = await _chronicle_payload_for_session(pool, row)
    await pool.execute(
        "UPDATE sessions SET recap = $2 WHERE id = $1",
        session_id,
        payload["recap"],
    )
    await enqueue(redis_client, JobEnvelope.agent_tick(session_id, force=True))
    return {
        "viewer_mode": mode,
        "viewer_character_id": str(char_id) if char_id else None,
        "recap": payload["recap"],
        "entries": payload["entries"],
        "agent_queued": True,
    }


@router.get("/api/v1/sessions/{session_id}/timeline")
async def get_timeline(
    session_id: UUID,
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[dict]:
    return _rows(
        await pool.fetch(
            "SELECT * FROM session_events WHERE session_id = $1 ORDER BY ts ASC", session_id
        )
    )


@router.get("/api/v1/sessions/{session_id}/activity")
async def get_activity(
    session_id: UUID,
    feed: str = "ai",
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[dict]:
    exists = await pool.fetchval("SELECT EXISTS(SELECT 1 FROM sessions WHERE id = $1)", session_id)
    if not exists:
        raise HTTPException(404, "session not found")
    if feed not in ("ai", "notes", "pipeline", "chat", "full"):
        feed = "ai"
    return await fetch_activity_feed(pool, session_id, feed=feed)


@router.get("/api/v1/sessions/{session_id}/messages")
async def list_messages(
    session_id: UUID,
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[dict]:
    return _rows(
        await pool.fetch(
            "SELECT * FROM session_messages WHERE session_id = $1 ORDER BY created_at", session_id
        )
    )


@router.post("/api/v1/sessions/{session_id}/messages")
async def post_message(
    session_id: UUID,
    body: PostMessage,
    pool: asyncpg.Pool = Depends(get_pool),
    redis_client=Depends(get_redis),
) -> dict:
    user_row = await pool.fetchrow(
        """
        INSERT INTO session_messages (session_id, role, content)
        VALUES ($1, 'user', $2)
        RETURNING id
        """,
        session_id,
        body.content,
    )
    await publish(
        redis_client,
        session_id,
        LiveEvent.activity(
            kind="chat_user",
            title="You",
            body=body.content,
            activity_id=f"msg-{user_row['id']}",
        ),
    )
    try:
        ctx = await load_agent_context(pool, session_id)
    except ValueError:
        raise HTTPException(404, "session not found") from None
    reply = run_agent_chat(
        session_id=str(session_id),
        ctx=ctx,
        question=body.content,
    )
    asst_row = await pool.fetchrow(
        """
        INSERT INTO session_messages (session_id, role, content)
        VALUES ($1, 'assistant', $2)
        RETURNING id
        """,
        session_id,
        reply,
    )
    await publish(
        redis_client,
        session_id,
        LiveEvent.activity(
            kind="chat_assistant",
            title="Weave",
            body=reply,
            activity_id=f"msg-{asst_row['id']}",
        ),
    )
    return {"reply": reply}


@router.post("/api/v1/sessions/{session_id}/agent-tick")
async def trigger_agent(
    session_id: UUID,
    pool: asyncpg.Pool = Depends(get_pool),
    redis_client=Depends(get_redis),
) -> dict:
    await enqueue(redis_client, JobEnvelope.agent_tick(session_id, force=True))
    return {"queued": True}


@router.get("/api/v1/sessions/{session_id}/export")
async def export_markdown(
    session_id: UUID,
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict:
    session = await get_session(session_id, pool)
    timeline = await get_timeline(session_id, pool)
    md = f"# Session: {session['title'] or 'Untitled'}\n\n**Recap:** {session['recap']}\n\n## Timeline\n\n"
    for ev in timeline:
        md += f"- **{ev['event_type']}** @ {ev['ts']}\n  ```json\n{json.dumps(ev['payload'], default=str)}\n  ```\n"
    return {"markdown": md}


@router.post("/api/v1/tts/speak")
async def tts_speak(body: TtsRequest) -> dict:
    import base64

    audio, mime = synthesize_speech(body.text)
    return {
        "audio_base64": base64.b64encode(audio).decode("ascii"),
        "content_type": mime,
    }
