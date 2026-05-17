"""Agent system prompts and tick response schema."""

from __future__ import annotations

import json
import logging
from typing import Any

from weave.agent.context import AgentContext, build_context_payload

logger = logging.getLogger(__name__)

TICK_JSON_KEYS = (
    "chronicle_entry",
    "memory_delta",
    "suggestions",
    "lore_snippets",
)

TICK_SYSTEM_DM = """You are Weave, an expert Dungeons & Dragons session chronicler for the **Dungeon Master**.

Audience: the DM running the table — not the players.

`chronicle_entries` are **chapters** (~30 table transcript lines each). Never rewrite finished chapters.

On each tick, read `pending_transcript` (speech since last agent pass) plus memory, story, party, lore, notes, chat,
and `ddb_game_log_recent`.

**chronicle_entry** (required when there is new `pending_transcript`): ONE passage (2–6 sentences) to **append to the
current chapter** covering recent speech — past tense, third person, name PCs/NPCs. Do not repeat text already in
`chronicle_entries`. Never paste raw speech-to-text.

**memory_delta**: optional; same beat as chronicle_entry or "" if you only return chronicle_entry.

**suggestions** (“Scene & DM notes” in the UI): 2–3 short tips for the **Dungeon Master only**
(pacing, NPC motives, rules, scene framing) — never player-coaching or “your character should…”.

**lore_snippets**: optional citations from campaign_lore.

Do NOT return session_recap or recap_delta (journal is append-only).

Your entire reply must be ONE JSON object — no markdown fences, no commentary before or after.

Respond with JSON only: chronicle_entry, memory_delta, suggestions, lore_snippets.
"""

TICK_SYSTEM_PLAYER = """You are Weave, a personal session chronicler for **one player character** at the table.

Audience: the player controlling `viewer.character` — NOT the DM.

`chronicle_entries` are **chapters** (~30 transcript lines each) for this character. Never rewrite finished chapters.

On each tick, integrate `pending_transcript` and `ddb_game_log_recent` but only what this character could know.

**chronicle_entry** (required when there is new `pending_transcript`): ONE passage (2–6 sentences) to **append to the
current chapter** in their voice. Past tense; center on their name. Do not repeat prior chapter text.

**memory_delta**: optional duplicate of the beat or "".

**suggestions** (“Ideas for your character” in the UI): 2–3 short tips aimed at the **PLAYER**
controlling `viewer.character` — what they might do, remember, or use (spells, gear, objectives).
Write in second person (“you”) when natural. This block is **NOT** for the Dungeon Master:
never give DM facilitation, encounter design, “run the scene”, NPC motives the PC wouldn’t know,
rules adjudication for the table, or “tell your players to…”.

**lore_snippets**: lore this character knows.

Do NOT return session_recap or recap_delta.

Your entire reply must be ONE JSON object — no markdown fences, no commentary before or after.

Respond with JSON only: chronicle_entry, memory_delta, suggestions, lore_snippets.
"""


def _suggestions_audience_hint(ctx: AgentContext) -> str:
    if ctx.viewer_mode == "player" and ctx.viewer_character:
        name = (ctx.viewer_character or {}).get("name") or "your character"
        return (
            f"PLAYER-facing tips for the person playing **{name}** — not the DM. "
            "Use viewer.character (sheet) plus recent_transcript. "
            "Forbidden: DM-only advice, secret GM info, or coaching the table."
        )
    return (
        "DM-facing tips for the person running the game — not individual players. "
        "Forbidden: 'your character should…' or player action coaching."
    )


def tick_system_prompt(ctx: AgentContext) -> str:
    if ctx.viewer_mode == "player" and ctx.viewer_character:
        return TICK_SYSTEM_PLAYER
    return TICK_SYSTEM_DM


def build_tick_user_message(
    ctx: AgentContext, extra_instructions: str, *, compact: bool = False
) -> str:
    mode = ctx.viewer_mode
    char_name = (ctx.viewer_character or {}).get("name") if ctx.viewer_character else None
    n = len(ctx.chronicle_entries)
    task = (
        f"Append ONE chronicle_entry passage to the current chapter ({n} chapter(s) so far). "
        "pending_transcript is speech since the last agent tick (not a full chapter by itself)."
    )
    if mode == "player" and char_name:
        task += f" Write for the player of **{char_name}** only."
    else:
        task += " Write for the Dungeon Master."

    payload = {
        **build_context_payload(ctx, compact=compact),
        "task": task,
        "extra_instructions": extra_instructions,
        "suggestions_audience": _suggestions_audience_hint(ctx),
    }
    return json.dumps(payload, indent=2)


def extract_chronicle_entry(out: dict[str, Any]) -> str:
    """Prefer explicit chronicle_entry; never append full session_recap rewrites."""
    ce = str(out.get("chronicle_entry") or "").strip()
    if ce:
        return ce
    md = str(out.get("memory_delta") or "").strip()
    if md:
        return md
    rd = str(out.get("recap_delta") or "").strip()
    if rd:
        return rd
    return ""


def normalize_tick_output(data: dict[str, Any]) -> dict[str, Any]:
    suggestions = data.get("suggestions") or []
    if not isinstance(suggestions, list):
        suggestions = []
    lore = data.get("lore_snippets") or []
    if not isinstance(lore, list):
        lore = []
    chronicle_entry = extract_chronicle_entry(data)
    memory_delta = str(data.get("memory_delta") or "").strip() or chronicle_entry
    return {
        "chronicle_entry": chronicle_entry,
        "session_recap": "",
        "memory_delta": memory_delta,
        "recap_delta": "",
        "suggestions": [str(s).strip() for s in suggestions if str(s).strip()],
        "lore_snippets": [str(s).strip() for s in lore if str(s).strip()],
    }


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Best-effort parse when models wrap JSON in prose or markdown."""
    import re

    cleaned = text.strip()
    if not cleaned:
        return None

    if "```" in cleaned:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
        if match:
            cleaned = match.group(1).strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    if start >= 0:
        depth = 0
        for i in range(start, len(cleaned)):
            ch = cleaned[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        data = json.loads(cleaned[start : i + 1])
                        if isinstance(data, dict):
                            return data
                    except json.JSONDecodeError:
                        break
    return None


def parse_tick_json(text: str) -> dict[str, Any] | None:
    data = _extract_json_object(text)
    if data:
        return normalize_tick_output(data)
    preview = text.strip().replace("\n", " ")[:160]
    logger.warning("tick response was not valid JSON (preview: %s)", preview)
    return None
