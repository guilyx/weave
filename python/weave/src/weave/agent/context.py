"""Shared context payload for all agent backends (tick, chat, export)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import asyncpg

from weave.agent.viewpoint import parse_recaps_by_viewer, recap_for_viewer
from weave.chronicle import (
    ensure_legacy_recap_migrated,
    join_entries_text,
    list_chronicle_entries,
    viewer_key_for_mode,
)
from weave.game_log.sync import list_game_log_for_campaign


@dataclass
class AgentContext:
    """Everything Weave injects into agent prompts for a live session."""

    campaign_name: str
    campaign_description: str | None = None
    ai_brief: str | None = None
    characters: list[Any] = field(default_factory=list)
    lore: list[str] = field(default_factory=list)
    past_session_recaps: list[str] = field(default_factory=list)
    session_recap: str = ""
    session_story: str = ""
    session_memory_beats: list[str] = field(default_factory=list)
    transcript_window: list[str] = field(default_factory=list)
    pending_transcript: str = ""
    manual_notes: list[str] = field(default_factory=list)
    chat_history: list[dict[str, str]] = field(default_factory=list)
    prior_suggestions: list[str] = field(default_factory=list)
    viewer_mode: str = "dm"
    viewer_character_id: UUID | None = None
    viewer_character: dict[str, Any] | None = None
    chronicle_entries: list[dict[str, Any]] = field(default_factory=list)
    ddb_game_log_recent: list[str] = field(default_factory=list)


def party_roster_summaries(characters: list[Any]) -> list[dict[str, Any]]:
    """Compact party lines for the model (full sheets kept under party_sheets)."""
    summaries: list[dict[str, Any]] = []
    for raw in characters:
        snap = raw if isinstance(raw, dict) else {}
        summaries.append(
            {
                "name": snap.get("name"),
                "race": snap.get("race"),
                "class_summary": snap.get("class_summary"),
                "hit_points": snap.get("hit_points"),
                "armor_class": snap.get("armor_class"),
            }
        )
    return summaries


def build_context_payload(ctx: AgentContext, *, compact: bool = False) -> dict[str, Any]:
    """JSON-serializable block included in every agent user prompt."""
    story = ctx.session_story or ""
    if compact and len(story) > 12_000:
        story = "…\n" + story[-12_000:]

    payload: dict[str, Any] = {
        "campaign": {
            "name": ctx.campaign_name,
            "description": ctx.campaign_description,
            "ai_brief": ctx.ai_brief,
        },
        "party_roster": party_roster_summaries(ctx.characters),
        "campaign_lore": ctx.lore[-8:] if compact else ctx.lore,
        "past_session_recaps": ctx.past_session_recaps[-4:] if compact else ctx.past_session_recaps,
        "current_session_recap": ctx.session_recap,
        "chronicle_entries": ctx.chronicle_entries[-24 if compact else 48 :],
        "session_story": story,
        "session_memory_beats": ctx.session_memory_beats[-8 if compact else 16 :],
        "recent_transcript": ctx.transcript_window[-40 if compact else 80 :],
        "pending_transcript": ctx.pending_transcript,
        "manual_notes": ctx.manual_notes[-8 if compact else 24 :],
        "chat_history": ctx.chat_history[-8 if compact else 16 :],
        "prior_suggestions": ctx.prior_suggestions[-12:],
        "viewer": {
            "mode": ctx.viewer_mode,
            "character_id": str(ctx.viewer_character_id) if ctx.viewer_character_id else None,
            "character": ctx.viewer_character,
        },
        "ddb_game_log_recent": ctx.ddb_game_log_recent[-25 if compact else 40 :],
    }
    if not compact:
        payload["party_sheets"] = ctx.characters
    elif ctx.viewer_character:
        payload["viewer_character_sheet"] = ctx.viewer_character
    return payload


def format_context_block(ctx: AgentContext) -> str:
    return json.dumps(build_context_payload(ctx), indent=2)


async def load_agent_context(pool: asyncpg.Pool, session_id: UUID) -> AgentContext:
    try:
        session = await pool.fetchrow(
            """
            SELECT campaign_id, recap, COALESCE(story, '') AS story,
                   COALESCE(viewer_mode, 'dm') AS viewer_mode,
                   viewer_character_id,
                   COALESCE(recaps_by_viewer, '{}'::jsonb) AS recaps_by_viewer
            FROM sessions WHERE id = $1
            """,
            session_id,
        )
    except asyncpg.UndefinedColumnError:
        session = await pool.fetchrow(
            """
            SELECT campaign_id, recap, COALESCE(story, '') AS story
            FROM sessions WHERE id = $1
            """,
            session_id,
        )
    if not session:
        raise ValueError(f"session not found: {session_id}")

    campaign_id = session["campaign_id"]
    campaign = await pool.fetchrow(
        "SELECT name, description, ai_brief FROM campaigns WHERE id = $1",
        campaign_id,
    )
    if not campaign:
        raise ValueError(f"campaign not found: {campaign_id}")

    transcript_rows = await pool.fetch(
        """
        SELECT payload->>'text' AS text FROM session_events
        WHERE session_id = $1 AND event_type = 'transcript'
        ORDER BY ts DESC LIMIT 120
        """,
        session_id,
    )
    transcript = [r["text"] for r in reversed(transcript_rows) if r["text"]]

    char_rows = await pool.fetch(
        "SELECT snapshot FROM characters WHERE campaign_id = $1 ORDER BY is_primary DESC, created_at",
        campaign_id,
    )
    characters = [r["snapshot"] for r in char_rows]

    note_rows = await pool.fetch(
        """
        SELECT payload->>'text' AS text FROM session_events
        WHERE session_id = $1 AND event_type = 'note' ORDER BY ts
        """,
        session_id,
    )
    notes = [r["text"] for r in note_rows if r["text"]]

    lore_rows = await pool.fetch(
        "SELECT title, content FROM campaign_lore WHERE campaign_id = $1 ORDER BY created_at",
        campaign_id,
    )
    lore = [f"## {r['title']}\n{r['content']}" for r in lore_rows]

    past_rows = await pool.fetch(
        """
        SELECT COALESCE(title, 'Session') AS title, recap
        FROM sessions
        WHERE campaign_id = $1 AND id != $2
          AND recap IS NOT NULL AND TRIM(recap) != ''
        ORDER BY COALESCE(ended_at, started_at, created_at) DESC
        LIMIT 8
        """,
        campaign_id,
        session_id,
    )
    past_recaps = [
        f"### {r['title']}\n{r['recap'].strip()}" for r in past_rows if r["recap"]
    ]

    memory_beats: list[str] = []
    try:
        mem_rows = await pool.fetch(
            """
            SELECT summary FROM session_memory
            WHERE session_id = $1
            ORDER BY created_at DESC
            LIMIT 16
            """,
            session_id,
        )
        memory_beats = [r["summary"] for r in reversed(mem_rows)]
    except asyncpg.UndefinedTableError:
        pass

    msg_rows = await pool.fetch(
        """
        SELECT role, content FROM session_messages
        WHERE session_id = $1
        ORDER BY created_at DESC
        LIMIT 24
        """,
        session_id,
    )
    chat_history = [
        {"role": str(r["role"]), "content": str(r["content"])}
        for r in reversed(msg_rows)
    ]

    prior_suggestions: list[str] = []
    sugg_rows = await pool.fetch(
        """
        SELECT payload FROM session_events
        WHERE session_id = $1 AND event_type = 'suggestion'
        ORDER BY ts DESC
        LIMIT 8
        """,
        session_id,
    )
    for row in sugg_rows:
        payload = row["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        if not isinstance(payload, dict):
            continue
        items = payload.get("items") or []
        if isinstance(items, list):
            for item in items:
                if isinstance(item, str) and item.strip():
                    prior_suggestions.append(item.strip())
    # newest last for prompt "do not repeat"
    prior_suggestions = list(dict.fromkeys(reversed(prior_suggestions)))[-12:]

    viewer_mode = str(session.get("viewer_mode") or "dm").lower()
    viewer_character_id = session.get("viewer_character_id")
    recaps_map = parse_recaps_by_viewer(session.get("recaps_by_viewer"))
    viewer_character: dict[str, Any] | None = None
    if viewer_mode == "player" and viewer_character_id:
        row = await pool.fetchrow(
            "SELECT snapshot FROM characters WHERE id = $1 AND campaign_id = $2",
            viewer_character_id,
            campaign_id,
        )
        if row and isinstance(row["snapshot"], dict):
            viewer_character = row["snapshot"]

    vkey = viewer_key_for_mode(viewer_mode, viewer_character_id)
    legacy_recap = recap_for_viewer(
        recaps_map,
        viewer_mode,
        viewer_character_id,
        legacy_recap=session["recap"] or "",
    )
    chronicle_entries = await list_chronicle_entries(pool, session_id, vkey)
    if not chronicle_entries and legacy_recap:
        chronicle_entries = await ensure_legacy_recap_migrated(
            pool, session_id, vkey, legacy_recap
        )
    current_recap = join_entries_text(chronicle_entries) or legacy_recap

    game_log_lines: list[str] = []
    try:
        for entry in await list_game_log_for_campaign(pool, campaign_id, limit=40):
            line = entry.get("summary")
            if line:
                game_log_lines.append(str(line))
    except Exception:
        game_log_lines = []

    return AgentContext(
        campaign_name=campaign["name"],
        campaign_description=campaign["description"],
        ai_brief=campaign["ai_brief"],
        characters=characters,
        lore=lore,
        past_session_recaps=past_recaps,
        session_recap=current_recap,
        session_story=(session["story"] or "").strip(),
        session_memory_beats=memory_beats,
        transcript_window=transcript,
        manual_notes=notes,
        chat_history=chat_history,
        prior_suggestions=prior_suggestions,
        viewer_mode=viewer_mode,
        viewer_character_id=viewer_character_id,
        viewer_character=viewer_character,
        chronicle_entries=chronicle_entries,
        ddb_game_log_recent=game_log_lines,
    )
