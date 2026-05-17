"""Session recap synthesis helpers (AI-facing prose, not raw STT)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from weave.agent.context import AgentContext


def looks_like_raw_transcript(text: str) -> bool:
    """Heuristic: pasted STT vs DM narrative."""
    t = text.strip()
    if not t:
        return False
    if t.lower().startswith("table audio condensed:"):
        return True
    if t.lower().startswith("recent play at the table:"):
        return True
    if len(t) < 60 and not re.search(r"[.!?]", t):
        return True
    # STT often lacks capitalization and has disfluencies
    if len(t) < 120 and t == t.lower() and not re.search(r"\.\s", t):
        return True
    return False


def recap_tick_instructions(ctx: AgentContext) -> str:
    base = (
        "pending_transcript is raw speech-to-text — never paste verbatim. "
        "Use session_memory_beats and session_story as fact sources only. "
        "Return chronicle_entry: ONE new journal passage since the last chronicle_entries item — "
        "do not rewrite the whole journal."
    )
    if ctx.viewer_mode == "player" and ctx.viewer_character:
        name = ctx.viewer_character.get("name") or "the character"
        return f"{base} Player POV for **{name}** only."
    return f"{base} DM table chronicle (third person, all PCs)."


def stub_memory_beat(ctx: AgentContext, pending_transcript: str) -> str:
    """Stub: one narrative line without copying STT (real AI required for quality)."""
    if not pending_transcript.strip():
        return ""
    low = pending_transcript.lower()
    themes: list[str] = []
    if re.search(r"\b(dragon|wyrm)\b", low):
        themes.append("a threatening dragon")
    if re.search(r"\b(combat|attack|initiative|damage)\b", low):
        themes.append("combat at the table")
    if re.search(r"\b(tavern|inn|town|city)\b", low):
        themes.append("events in town")
    if re.search(r"\b(door|trap|dungeon|corridor)\b", low):
        themes.append("exploration deeper in the delve")
    if re.search(r"\b(npc|merchant|guard|king|queen)\b", low):
        themes.append("a notable NPC exchange")
    if not themes:
        themes.append("the party's latest decisions and dialogue")
    roster = [
        c.get("name")
        for c in ctx.characters
        if isinstance(c, dict) and c.get("name")
    ]
    who = roster[0] if len(roster) == 1 else "The party"
    return (
        f"{who} pressed forward as {themes[0]} shaped the scene — "
        "(enable AGENT_BACKEND=langgraph + OPENAI_API_KEY for full AI chronicle)."
    )


def stub_chronicle_entry(ctx: AgentContext, pending_transcript: str) -> str:
    """Stub: one new journal line (not a full recap rewrite)."""
    if not pending_transcript.strip():
        return ""
    beat = stub_memory_beat(ctx, pending_transcript)
    pc_name = (ctx.viewer_character or {}).get("name") if ctx.viewer_character else None
    if ctx.viewer_mode == "player" and pc_name:
        return beat.replace("The party", pc_name)
    return beat
