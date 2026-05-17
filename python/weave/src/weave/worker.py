import asyncio
import base64
import json
import logging
import time
from pathlib import Path
from uuid import UUID

import asyncpg
import redis.asyncio as redis

from weave.agent import run_agent_tick
from weave.agent.context import load_agent_context
from weave.agent.recap import looks_like_raw_transcript
from weave.agent.prompts import extract_chronicle_entry
from weave.chronicle import (
    append_or_extend_chronicle,
    count_session_transcripts,
    list_chronicle_entries,
    sync_session_recap_field,
    viewer_key_for_mode,
)
from weave.config import settings
from weave.ddb.client import DdbClient
from weave.jobs import JOB_QUEUE_KEY, JobEnvelope, JobKind, enqueue
from weave.live import LiveEvent, publish
from weave.session_activity import (
    append_session_story,
    insert_event,
    log_activity,
    persist_memory,
)
from weave.stt import transcribe_audio

logger = logging.getLogger(__name__)

AGENT_LOCK_TTL_SEC = 600


def _agent_debounce_sec() -> int:
    return max(10, settings.agent_debounce_sec)


async def worker_loop(
    pool: asyncpg.Pool,
    redis_client: redis.Redis,
    ddb: DdbClient,
) -> None:
    concurrency = max(1, settings.worker_concurrency)
    sem = asyncio.Semaphore(concurrency)
    in_flight: set[asyncio.Task[None]] = set()
    logger.info("background worker started (concurrency=%s)", concurrency)

    async def run_job(payload: str) -> None:
        async with sem:
            try:
                job = JobEnvelope.model_validate_json(payload)
                await _process_job(pool, redis_client, ddb, job)
            except Exception:
                logger.exception("worker job error")

    while True:
        done = {t for t in in_flight if t.done()}
        for task in done:
            in_flight.discard(task)
            try:
                task.result()
            except Exception:
                pass

        if len(in_flight) >= concurrency:
            await asyncio.wait(in_flight, return_when=asyncio.FIRST_COMPLETED)
            continue

        try:
            result = await redis_client.brpop(JOB_QUEUE_KEY, timeout=1)
        except asyncio.CancelledError:
            if in_flight:
                await asyncio.gather(*in_flight, return_exceptions=True)
            raise

        if result is None:
            await asyncio.sleep(0.1)
            continue

        _, payload = result
        task = asyncio.create_task(run_job(payload))
        in_flight.add(task)


async def _process_job(
    pool: asyncpg.Pool,
    redis_client: redis.Redis,
    ddb: DdbClient,
    job: JobEnvelope,
) -> None:
    if job.kind == JobKind.TRANSCRIBE_AUDIO.value:
        if job.session_id and job.audio_path:
            await _transcribe(pool, redis_client, job.session_id, job.audio_path)
            await _maybe_enqueue_agent(pool, redis_client, job.session_id)
    elif job.kind == JobKind.AGENT_TICK.value:
        if job.session_id:
            await _run_agent_tick_guarded(pool, redis_client, job.session_id, force=job.force)
    elif job.kind == JobKind.REFRESH_CHARACTER.value:
        if job.character_id:
            await _refresh_character(pool, ddb, job.character_id)
    elif job.kind == JobKind.SYNC_GAME_LOG.value:
        if job.campaign_id:
            from weave.game_log.sync import sync_campaign_game_log

            await sync_campaign_game_log(
                pool,
                ddb,
                job.campaign_id,
                session_id=job.session_id,
                redis_client=redis_client,
            )


async def _transcribe(
    pool: asyncpg.Pool,
    redis_client: redis.Redis,
    session_id: UUID,
    audio_path: str,
) -> None:
    data = Path(audio_path).read_bytes()
    audio_b64 = base64.b64encode(data).decode("ascii")
    result = await asyncio.to_thread(transcribe_audio, audio_b64, "audio/webm")
    text = (result.text or "").strip()
    if not text:
        return

    await insert_event(pool, session_id, "transcript", {"text": text})
    await append_session_story(pool, session_id, text)

    buffer_key = f"session:{session_id}:buffer"
    await redis_client.append(buffer_key, text + "\n")
    await publish(redis_client, session_id, LiveEvent.transcript_delta(text))


async def _maybe_enqueue_game_log_sync(
    pool: asyncpg.Pool, redis_client: redis.Redis, session_id: UUID
) -> None:
    """Pull D&D Beyond rolls into campaign log (debounced per campaign)."""
    if not settings.ddb_cobalt_session:
        return
    row = await pool.fetchrow(
        "SELECT campaign_id FROM sessions WHERE id = $1",
        session_id,
    )
    if not row:
        return
    campaign_id = row["campaign_id"]
    has_ddb = await pool.fetchval(
        "SELECT ddb_campaign_id IS NOT NULL FROM campaigns WHERE id = $1",
        campaign_id,
    )
    if not has_ddb:
        return
    key = f"campaign:{campaign_id}:last_gamelog_sync"
    now = int(time.time())
    last = await redis_client.get(key)
    if last and now - int(last) < 45:
        return
    await redis_client.set(key, str(now), ex=120)
    await enqueue(
        redis_client,
        JobEnvelope.sync_game_log(campaign_id, session_id=session_id),
    )


async def _maybe_enqueue_agent(
    pool: asyncpg.Pool, redis_client: redis.Redis, session_id: UUID
) -> None:
    await _maybe_enqueue_game_log_sync(pool, redis_client, session_id)
    key = f"session:{session_id}:last_agent"
    last = await redis_client.get(key)
    now = int(time.time())
    if last and now - int(last) < _agent_debounce_sec():
        return
    await redis_client.set(key, str(now))
    await enqueue(redis_client, JobEnvelope.agent_tick(session_id))


def _agent_lock_key(session_id: UUID) -> str:
    return f"weave:lock:agent:{session_id}"


def _agent_pending_key(session_id: UUID) -> str:
    return f"weave:pending:agent:{session_id}"


async def _run_agent_tick_guarded(
    pool: asyncpg.Pool,
    redis_client: redis.Redis,
    session_id: UUID,
    *,
    force: bool = False,
) -> None:
    """One agent run per session at a time; coalesce overlapping requests."""
    lock_key = _agent_lock_key(session_id)
    pending_key = _agent_pending_key(session_id)

    acquired = await redis_client.set(lock_key, "1", nx=True, ex=AGENT_LOCK_TTL_SEC)
    if not acquired:
        await redis_client.set(pending_key, "1", ex=AGENT_LOCK_TTL_SEC)
        logger.debug("agent tick for %s waiting (run in progress)", session_id)
        return

    try:
        await _agent_tick(pool, redis_client, session_id)
    finally:
        await redis_client.delete(lock_key)
        if await redis_client.getdel(pending_key):
            logger.debug("agent tick for %s re-queued after pending work", session_id)
            await enqueue(redis_client, JobEnvelope.agent_tick(session_id, force=force))


async def _agent_tick(pool: asyncpg.Pool, redis_client: redis.Redis, session_id: UUID) -> None:
    buffer_key = f"session:{session_id}:buffer"
    raw = await redis_client.get(buffer_key)
    buffer_lines = (raw or "").strip().splitlines() if raw else []

    try:
        ctx = await load_agent_context(pool, session_id)
    except ValueError:
        return
    pending = "\n".join(buffer_lines).strip() if buffer_lines else ""
    if pending:
        ctx.pending_transcript = pending
        ctx.transcript_window = buffer_lines

    out = await asyncio.to_thread(run_agent_tick, str(session_id), ctx)
    backend_used = out.pop("_backend", None) or out.pop("_stub_reason", "unknown")
    logger.info("agent tick completed session=%s backend=%s", session_id, backend_used)
    chronicle_text = extract_chronicle_entry(out)
    memory_delta = (out.get("memory_delta") or "").strip()
    if memory_delta and looks_like_raw_transcript(memory_delta) and chronicle_text:
        memory_delta = chronicle_text
    suggestions = out.get("suggestions", [])
    lore_snippets = out.get("lore_snippets", [])

    vkey = viewer_key_for_mode(ctx.viewer_mode, ctx.viewer_character_id)
    new_entry_row: dict | None = None
    new_chapter = False
    if chronicle_text and not looks_like_raw_transcript(chronicle_text):
        try:
            stt_count = await count_session_transcripts(pool, session_id)
            new_entry_row, new_chapter = await append_or_extend_chronicle(
                pool,
                session_id,
                vkey,
                chronicle_text,
                stt_count,
                source="agent",
            )
        except asyncpg.UndefinedTableError:
            logger.warning("session_chronicle_entries table missing; run migrations")
        except ValueError:
            pass

    if new_entry_row:
        entries = await list_chronicle_entries(pool, session_id, vkey)
        joined = "\n\n".join(e["body"] for e in entries)
        try:
            await sync_session_recap_field(pool, session_id, vkey, entries)
        except asyncpg.UndefinedTableError:
            pass
        excerpt = new_entry_row["body"]
        if len(excerpt) > 600:
            excerpt = excerpt[:600] + "…"
        ch = new_entry_row.get("chapter_index", "?")
        stt_lo = new_entry_row.get("stt_from")
        stt_hi = new_entry_row.get("stt_to")
        stt_label = (
            f" (STT {stt_lo}–{stt_hi})" if stt_lo is not None and stt_hi is not None else ""
        )
        await log_activity(
            pool,
            redis_client,
            session_id,
            event_type="recap",
            kind="chronicle",
            title=f"Chapter {ch}" if new_chapter else f"Chapter {ch} updated",
            body=excerpt,
            payload={
                "entry": new_entry_row,
                "text": joined,
                "chapter_index": ch,
                "new_chapter": new_chapter,
            },
            activity_id=f"chronicle-{new_entry_row['id']}",
        )
        await publish(
            redis_client,
            session_id,
            LiveEvent.chronicle_append(new_entry_row, joined),
        )

    if memory_delta and not looks_like_raw_transcript(memory_delta):
        try:
            mem_id = await persist_memory(pool, session_id, memory_delta)
            await publish(
                redis_client,
                session_id,
                LiveEvent.activity(
                    kind="memory",
                    title="Memory",
                    body=memory_delta,
                    activity_id=f"memory-{mem_id}",
                ),
            )
        except asyncpg.UndefinedTableError:
            await log_activity(
                pool,
                redis_client,
                session_id,
                event_type="memory",
                kind="memory",
                title="Memory",
                body=memory_delta,
                payload={"text": memory_delta},
            )

    if suggestions:
        await log_activity(
            pool,
            redis_client,
            session_id,
            event_type="suggestion",
            kind="suggestion",
            title="Suggestions",
            body="\n".join(f"• {s}" for s in suggestions),
            payload={"items": suggestions},
        )
        await publish(redis_client, session_id, LiveEvent.suggestions(suggestions))

    if lore_snippets:
        await publish(redis_client, session_id, LiveEvent.lore_snippets(lore_snippets))

    if buffer_lines:
        await redis_client.delete(buffer_key)

    await pool.execute(
        """
        INSERT INTO agent_runs (session_id, input_hash, output_summary)
        VALUES ($1, $2, $3::jsonb)
        """,
        session_id,
        f"{session_id}-{len(ctx.transcript_window)}",
        json.dumps(out),
    )


async def _refresh_character(pool: asyncpg.Pool, ddb: DdbClient, character_id: UUID) -> None:
    row = await pool.fetchrow(
        "SELECT ddb_character_id FROM characters WHERE id = $1", character_id
    )
    if not row:
        return
    sheet = await ddb.fetch_character(int(row["ddb_character_id"]))
    await pool.execute(
        """
        UPDATE characters SET snapshot = $2::jsonb, last_synced_at = NOW() WHERE id = $1
        """,
        character_id,
        sheet.model_dump_json(),
    )
