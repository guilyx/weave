"""Additive session chronicle (journal chapters grouped by STT count)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import asyncpg

from weave.agent.viewpoint import viewer_recap_key
from weave.config import settings

DEFAULT_CHAPTER_STT_SIZE = 30


def chapter_stt_size() -> int:
    return max(1, getattr(settings, "chronicle_stt_per_chapter", DEFAULT_CHAPTER_STT_SIZE))


def legacy_chapter_from_tick_order(
    rn: int, entry_cnt: int, stt_total: int, *, size: int = DEFAULT_CHAPTER_STT_SIZE
) -> int:
    """Bucket pre-merge tick rows into ~size-STT chapters (migration / repair)."""
    num_chapters = max(1, (stt_total + size - 1) // size)
    ticks_per = max(1, (entry_cnt + num_chapters - 1) // num_chapters)
    return (rn - 1) // ticks_per + 1


def stt_chapter_index(stt_count: int, *, size: int | None = None) -> int:
    """Map total session transcript count to chapter number (1-based)."""
    size = size or chapter_stt_size()
    if stt_count <= 0:
        return 1
    return (stt_count - 1) // size + 1


def chapter_stt_range(chapter_index: int, *, size: int | None = None) -> tuple[int, int]:
    size = size or chapter_stt_size()
    stt_from = (chapter_index - 1) * size + 1
    stt_to = chapter_index * size
    return stt_from, stt_to


def merge_chapter_body(existing: str, passage: str) -> str:
    """Append agent passage to chapter without duplicating identical paragraphs."""
    passage = passage.strip()
    if not passage:
        return existing.strip()
    existing = existing.strip()
    if not existing:
        return passage
    if passage in existing:
        return existing
    if existing in passage:
        return passage
    return f"{existing}\n\n{passage}"


def entry_to_dict(row: asyncpg.Record) -> dict[str, Any]:
    created = row["created_at"]
    if isinstance(created, datetime):
        ts = created.astimezone(timezone.utc).isoformat()
    else:
        ts = str(created)
    out: dict[str, Any] = {
        "id": str(row["id"]),
        "session_id": str(row["session_id"]),
        "viewer_key": row["viewer_key"],
        "body": row["body"],
        "source": row["source"],
        "created_at": ts,
    }
    if "chapter_index" in row.keys():
        out["chapter_index"] = int(row["chapter_index"])
    if row.get("stt_from") is not None:
        out["stt_from"] = int(row["stt_from"])
    if row.get("stt_to") is not None:
        out["stt_to"] = int(row["stt_to"])
    return out


async def count_session_transcripts(pool: asyncpg.Pool, session_id: UUID) -> int:
    n = await pool.fetchval(
        """
        SELECT COUNT(*)::int FROM session_events
        WHERE session_id = $1 AND event_type = 'transcript'
        """,
        session_id,
    )
    return int(n or 0)


async def list_chronicle_entries(
    pool: asyncpg.Pool,
    session_id: UUID,
    viewer_key: str,
    *,
    limit: int = 200,
) -> list[dict[str, Any]]:
    try:
        rows = await pool.fetch(
            """
            SELECT id, session_id, viewer_key, body, source, created_at,
                   chapter_index, stt_from, stt_to
            FROM session_chronicle_entries
            WHERE session_id = $1 AND viewer_key = $2
            ORDER BY chapter_index ASC, created_at ASC
            LIMIT $3
            """,
            session_id,
            viewer_key,
            limit,
        )
    except asyncpg.UndefinedTableError:
        return []
    except asyncpg.UndefinedColumnError:
        rows = await pool.fetch(
            """
            SELECT id, session_id, viewer_key, body, source, created_at
            FROM session_chronicle_entries
            WHERE session_id = $1 AND viewer_key = $2
            ORDER BY created_at ASC
            LIMIT $3
            """,
            session_id,
            viewer_key,
            limit,
        )
    return [entry_to_dict(r) for r in rows]


async def append_or_extend_chronicle(
    pool: asyncpg.Pool,
    session_id: UUID,
    viewer_key: str,
    passage: str,
    stt_count: int,
    *,
    source: str = "agent",
) -> tuple[dict[str, Any], bool]:
    """
    Upsert chronicle for the chapter covering ``stt_count`` transcripts.
    Returns (entry, created_new_chapter).
    """
    passage = passage.strip()
    if not passage:
        raise ValueError("empty chronicle passage")

    size = chapter_stt_size()
    chapter_index = stt_chapter_index(stt_count, size=size)
    stt_from, stt_cap = chapter_stt_range(chapter_index, size=size)
    stt_to = min(stt_count, stt_cap) if stt_count > 0 else None

    try:
        existing = await pool.fetchrow(
            """
            SELECT id, body FROM session_chronicle_entries
            WHERE session_id = $1 AND viewer_key = $2 AND chapter_index = $3
            """,
            session_id,
            viewer_key,
            chapter_index,
        )
    except asyncpg.UndefinedColumnError:
        row = await pool.fetchrow(
            """
            INSERT INTO session_chronicle_entries (session_id, viewer_key, body, source)
            VALUES ($1, $2, $3, $4)
            RETURNING id, session_id, viewer_key, body, source, created_at
            """,
            session_id,
            viewer_key,
            passage,
            source,
        )
        if not row:
            raise RuntimeError("failed to insert chronicle entry")
        return entry_to_dict(row), True

    if existing:
        merged = merge_chapter_body(str(existing["body"]), passage)
        row = await pool.fetchrow(
            """
            UPDATE session_chronicle_entries
            SET body = $2, stt_to = $3, source = $4
            WHERE id = $1
            RETURNING id, session_id, viewer_key, body, source, created_at,
                      chapter_index, stt_from, stt_to
            """,
            existing["id"],
            merged,
            stt_to,
            source,
        )
        if not row:
            raise RuntimeError("failed to update chronicle chapter")
        return entry_to_dict(row), False

    row = await pool.fetchrow(
        """
        INSERT INTO session_chronicle_entries
            (session_id, viewer_key, chapter_index, stt_from, stt_to, body, source)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id, session_id, viewer_key, body, source, created_at,
                  chapter_index, stt_from, stt_to
        """,
        session_id,
        viewer_key,
        chapter_index,
        stt_from,
        stt_to,
        passage,
        source,
    )
    if not row:
        raise RuntimeError("failed to insert chronicle chapter")
    return entry_to_dict(row), True


async def append_chronicle_entry(
    pool: asyncpg.Pool,
    session_id: UUID,
    viewer_key: str,
    body: str,
    *,
    source: str = "agent",
) -> dict[str, Any]:
    """Legacy: append using current transcript count for chapter assignment."""
    stt_count = await count_session_transcripts(pool, session_id)
    entry, _ = await append_or_extend_chronicle(
        pool, session_id, viewer_key, body, stt_count, source=source
    )
    return entry


def join_entries_text(entries: list[dict[str, Any]]) -> str:
    """Legacy flat recap string for export / compatibility."""
    return "\n\n".join(e["body"].strip() for e in entries if e.get("body"))


async def sync_session_recap_field(
    pool: asyncpg.Pool,
    session_id: UUID,
    viewer_key: str,
    entries: list[dict[str, Any]],
) -> None:
    """Keep sessions.recap as joined journal for current viewer."""
    text = join_entries_text(entries)
    row = await pool.fetchrow(
        """
        SELECT COALESCE(recaps_by_viewer, '{}'::jsonb) AS recaps_by_viewer,
               COALESCE(viewer_mode, 'dm') AS viewer_mode,
               viewer_character_id
        FROM sessions WHERE id = $1
        """,
        session_id,
    )
    recaps_map: dict[str, str] = {}
    if row and row["recaps_by_viewer"]:
        raw = row["recaps_by_viewer"]
        if isinstance(raw, str):
            recaps_map = json.loads(raw)
        elif isinstance(raw, dict):
            recaps_map = {str(k): str(v) for k, v in raw.items()}
    recaps_map[viewer_key] = text
    await pool.execute(
        """
        UPDATE sessions SET recap = $2, recaps_by_viewer = $3::jsonb WHERE id = $1
        """,
        session_id,
        text,
        json.dumps(recaps_map),
    )


async def ensure_legacy_recap_migrated(
    pool: asyncpg.Pool,
    session_id: UUID,
    viewer_key: str,
    legacy_recap: str,
) -> list[dict[str, Any]]:
    """If journal empty but old flat recap exists, seed one opening entry."""
    entries = await list_chronicle_entries(pool, session_id, viewer_key)
    if entries or not (legacy_recap or "").strip():
        return entries
    legacy = legacy_recap.strip()
    if not legacy:
        return entries
    try:
        entry = await append_chronicle_entry(
            pool, session_id, viewer_key, legacy, source="import"
        )
        return [entry]
    except asyncpg.UndefinedTableError:
        return []


def viewer_key_for_mode(mode: str, character_id: UUID | None) -> str:
    return viewer_recap_key(mode, character_id)
