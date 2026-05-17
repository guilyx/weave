"""Context-aware suggestion helpers (stub backend and prompt hints)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from weave.agent.context import AgentContext


def _context_blob(ctx: AgentContext) -> str:
    parts = [
        ctx.session_recap or "",
        ctx.session_story or "",
        " ".join(ctx.transcript_window[-12:]),
        " ".join(ctx.manual_notes[-6:]),
        " ".join(ctx.session_memory_beats[-4:]),
    ]
    for msg in ctx.chat_history[-8:]:
        parts.append(msg.get("content") or "")
    return " ".join(parts).lower()


def tick_instructions_extra(ctx: AgentContext) -> str:
    prior = ctx.prior_suggestions
    if ctx.viewer_mode == "player" and ctx.viewer_character:
        name = ctx.viewer_character.get("name") or "your character"
        base = (
            f"The suggestions array is shown as “Ideas for your character” — written for the "
            f"PLAYER of {name}, NOT the Dungeon Master. Give 2–3 player tips: actions, "
            "resources from viewer.character (spells, items, features), reminders, objectives. "
            "Never: run the encounter, reveal hidden plots, adjudicate rules for the table, "
            "NPC motives the PC cannot know, or “get your players to…”."
        )
    else:
        base = (
            "Suggestions are for the Dungeon Master only — scene, NPCs, rules, pacing. "
            "No player-coaching or 'get your players to…' advice."
        )
    if not prior:
        return f"{base} Return 2-3 fresh tips grounded in recent_transcript and notes."
    joined = "; ".join(prior[-8:])
    return f"{base} Do NOT repeat: {joined}. Give 2-3 NEW tips."


def stub_suggestions(ctx: AgentContext, prior: list[str] | None = None) -> list[str]:
    """Heuristic tips from transcript/story/chat — not the fixed combat-only pair."""
    prior_set = {p.strip().lower() for p in (prior or []) if p}
    text = _context_blob(ctx)
    if len(text.strip()) < 12:
        return []

    candidates: list[str] = []

    player_mode = ctx.viewer_mode == "player" and ctx.viewer_character
    pc_name = (ctx.viewer_character or {}).get("name") or "your character"

    if player_mode:
        if re.search(r"\b(initiative|combat|attack|damage|hp|armor class|ac)\b", text):
            candidates.append(f"Track {pc_name}'s HP, conditions, and whose turn it is.")
        if re.search(r"\b(spell|cast|cantrip|concentrat)\b", text):
            candidates.append("Remember concentration and remaining spell slots for your character.")
        if re.search(r"\b(door|trap|stealth|sneak|perception|investigat)\b", text):
            candidates.append("Consider whether to scout or warn the party before moving in.")
        if re.search(r"\b(npc|talk|speak|persuad|deceiv|intimidat|merchant)\b", text):
            candidates.append("Note what was promised to you and names you learned.")
        if re.search(r"\b(quest|mission|objective|clue|letter|map)\b", text):
            candidates.append("Jot down clues your character cares about while they're fresh.")
        if re.search(r"\b(treasure|loot|gold|item|inventory)\b", text):
            candidates.append("Decide what your character wants to claim or share.")
    else:
        if re.search(r"\b(initiative|combat|attack|damage|hp|armor class|ac)\b", text):
            candidates.append("Track turn order and visible HP for creatures the table knows.")
        if re.search(r"\b(spell|cast|cantrip|concentrat)\b", text):
            candidates.append("Note active concentrations and environmental effects in the scene.")
        if re.search(r"\b(door|trap|stealth|sneak|perception|investigat)\b", text):
            candidates.append("Clarify DCs and consequences before the party commits.")
        if re.search(r"\b(npc|talk|speak|persuad|deceiv|intimidat|merchant)\b", text):
            candidates.append("Capture NPC names and what was promised or revealed.")
        if re.search(r"\b(quest|mission|objective|clue|letter|map)\b", text):
            candidates.append("Tie new clues to existing lore or fronts you're running.")
        if re.search(r"\b(rest|short rest|long rest|camp)\b", text):
            candidates.append("Confirm rest type and downtime complications if any.")
        if re.search(r"\b(treasure|loot|gold|item|inventory)\b", text):
            candidates.append("Log loot distribution and any cursed or plot items.")

    # Pull a topical line from the latest transcript chunk.
    latest = (ctx.transcript_window[-1] if ctx.transcript_window else "").strip()
    if latest and len(latest) > 20:
        snippet = latest[:90] + ("…" if len(latest) > 90 else "")
        candidates.append(f"Follow up on: “{snippet}”")

    if not candidates and text.strip():
        if player_mode:
            candidates.append("What does your character want to do next in this scene?")
        else:
            candidates.append("Capture names, places, and decisions from the latest exchange.")

    out: list[str] = []
    for tip in candidates:
        key = tip.strip().lower()
        if key and key not in prior_set and tip not in out:
            out.append(tip)
        if len(out) >= 3:
            break

    return out
