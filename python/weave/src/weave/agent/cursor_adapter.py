"""Cursor ask-mode agent for live D&D session assistance."""

from __future__ import annotations

import logging
from typing import Any

from weave.agent.context import AgentContext, format_context_block
from weave.agent.prompts import (
    build_tick_user_message,
    normalize_tick_output,
    parse_tick_json,
    tick_system_prompt,
)
from weave.agent.recap import recap_tick_instructions
from weave.agent.suggestions import tick_instructions_extra
from weave.agent.cursor_client import run_cursor_ask
from weave.agent.cursor_sessions import get_cursor_session, set_cursor_session

logger = logging.getLogger(__name__)

CHAT_SYSTEM = """You are Weave, a D&D session assistant in read-only ask mode.
Answer using only the session context below (campaign brief, lore, party, recaps, session_story, transcript).
Be concise and flag uncertainty when the transcript is unclear.

Format every reply as **Markdown** for the chat UI: use ### headings, **bold**, bullet lists,
numbered steps. Do NOT wrap the answer in JSON or ``` code fences.

For map, battle map, scene, or character portrait requests: describe what to draw in vivid
table-ready detail (layout, lighting, key props). Note that automated image generation is not
wired yet — give the DM a strong text brief they can use in any art tool.
"""


def cursor_tick(session_id: str, ctx: AgentContext) -> dict[str, Any]:
    extra = tick_instructions_extra(ctx)
    recap_inst = recap_tick_instructions(ctx)
    user = build_tick_user_message(
        ctx,
        f"{recap_inst} Update memory_delta and suggestions from pending_transcript, notes, and chat. {extra}",
        compact=True,
    )
    system = tick_system_prompt(ctx)
    suggestions_note = ""
    if ctx.viewer_mode == "player" and ctx.viewer_character:
        suggestions_note = (
            " suggestions must be PLAYER tips (Ideas for your character), never DM advice."
        )
    json_only = (
        "\n\nIMPORTANT: Reply with a single raw JSON object only "
        "(keys: chronicle_entry, memory_delta, suggestions, lore_snippets). "
        f"No markdown code fences or explanation.{suggestions_note}"
    )
    return _run_and_parse(session_id, f"{system}{json_only}\n\n{user}", ctx)


def cursor_chat(session_id: str, ctx: AgentContext, question: str) -> str:
    from weave.agent.context import build_context_payload
    import json

    context = json.dumps(build_context_payload(ctx, compact=True), indent=2)
    prompt = f"{CHAT_SYSTEM}\n\n{context}\n\nPlayer question: {question}"
    result = _run_and_parse_raw(session_id, prompt)
    return result.text or "No response from Cursor agent."


def _run_and_parse(session_id: str, prompt: str, ctx: AgentContext) -> dict[str, Any]:
    result = _run_and_parse_raw(session_id, prompt)
    if result.is_error or not result.text:
        return normalize_tick_output(
            {
                "chronicle_entry": "",
                "memory_delta": "",
                "suggestions": [],
                "lore_snippets": [],
            }
        )
    return _parse_tick_json(result.text, ctx)


def _run_and_parse_raw(session_id: str, prompt: str):
    cursor_sid = get_cursor_session(session_id)
    result = run_cursor_ask(prompt, cursor_session_id=cursor_sid)
    if result.session_id:
        set_cursor_session(session_id, result.session_id)
    return result


def _parse_tick_json(text: str, ctx: AgentContext) -> dict[str, Any]:
    parsed = parse_tick_json(text)
    if parsed:
        return parsed
    logger.warning("Cursor returned non-JSON tick; using stub chronicle/suggestions fallback")
    from weave.agent.recap import stub_chronicle_entry
    from weave.agent.suggestions import stub_suggestions

    chronicle = stub_chronicle_entry(ctx) if (ctx.pending_transcript or "").strip() else ""
    return normalize_tick_output(
        {
            "chronicle_entry": chronicle,
            "memory_delta": chronicle,
            "suggestions": stub_suggestions(ctx, ctx.prior_suggestions),
            "lore_snippets": [],
        }
    )
