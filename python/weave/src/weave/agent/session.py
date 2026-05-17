import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from weave.agent.context import AgentContext, build_context_payload
from weave.agent.prompts import (
    build_tick_user_message,
    normalize_tick_output,
    parse_tick_json,
    tick_system_prompt,
)
from weave.agent.chat_format import normalize_chat_reply
from weave.agent.recap import recap_tick_instructions, stub_chronicle_entry, stub_memory_beat
from weave.agent.suggestions import stub_suggestions, tick_instructions_extra
from weave.config import settings

logger = logging.getLogger(__name__)


def _effective_tick_backend() -> str:
    b = (settings.agent_backend or "stub").lower().strip()
    if b == "auto":
        return "langgraph" if settings.openai_api_key else "stub"
    return b


def run_agent_tick(session_id: str, ctx: AgentContext) -> dict[str, Any]:
    backend = _effective_tick_backend()
    logger.info(
        "agent tick session=%s configured=%s effective=%s pending_chars=%d",
        session_id,
        settings.agent_backend,
        backend,
        len(ctx.pending_transcript or ""),
    )

    if backend == "cursor":
        try:
            from weave.agent.cursor_adapter import cursor_tick

            out = cursor_tick(session_id=session_id, ctx=ctx)
            out["_backend"] = "cursor"
            return out
        except (FileNotFoundError, RuntimeError, OSError) as exc:
            logger.warning("cursor agent unavailable: %s", exc)
            if settings.openai_api_key:
                backend = "langgraph"
            else:
                return _stub_tick(ctx, reason="cursor_unavailable")

    if backend == "langgraph":
        if not settings.openai_api_key:
            logger.warning("langgraph backend but OPENAI_API_KEY missing — using stub")
            return _stub_tick(ctx, reason="no_api_key")
        out = _langgraph_tick(ctx)
        out["_backend"] = "langgraph"
        return out

    if backend != "stub":
        logger.warning("unknown agent_backend=%s — using stub", backend)
    out = _stub_tick(ctx, reason="stub")
    out["_backend"] = "stub"
    return out


def run_agent_chat(session_id: str, ctx: AgentContext, question: str) -> str:
    backend = settings.agent_backend.lower()
    raw = ""
    if backend == "cursor":
        try:
            from weave.agent.cursor_adapter import cursor_chat

            raw = cursor_chat(session_id=session_id, ctx=ctx, question=question)
        except (FileNotFoundError, RuntimeError) as exc:
            logger.warning("cursor agent unavailable, using stub: %s", exc)
    if not raw:
        if backend == "stub" or not settings.openai_api_key:
            raw = (
                f"(stub) Based on the recap and {len(ctx.transcript_window)} transcript lines: "
                f"I cannot answer '{question}' without a configured agent backend."
            )
        else:
            raw = _langgraph_chat(ctx, question)
    return normalize_chat_reply(raw)


def _stub_tick(ctx: AgentContext, *, reason: str = "stub") -> dict[str, Any]:
    pending = (ctx.pending_transcript or " ".join(ctx.transcript_window[-8:])).strip()
    chronicle_entry = stub_chronicle_entry(ctx, pending)
    memory_delta = chronicle_entry or (stub_memory_beat(ctx, pending) if pending else "")
    suggestions = stub_suggestions(ctx, ctx.prior_suggestions)
    return {
        "chronicle_entry": chronicle_entry,
        "memory_delta": memory_delta,
        "session_recap": "",
        "recap_delta": "",
        "suggestions": suggestions,
        "lore_snippets": [],
        "_stub_reason": reason,
    }


def _langgraph_tick(ctx: AgentContext) -> dict[str, Any]:
    from langchain_openai import ChatOpenAI

    extra = tick_instructions_extra(ctx)
    recap_inst = recap_tick_instructions(ctx)
    user_content = build_tick_user_message(ctx, f"{recap_inst} {extra}")

    llm = ChatOpenAI(
        model=settings.agent_model,
        api_key=settings.openai_api_key,
        temperature=0.4,
        model_kwargs={"response_format": {"type": "json_object"}},
    )
    response = llm.invoke(
        [
            SystemMessage(content=tick_system_prompt(ctx)),
            HumanMessage(content=user_content),
        ]
    )
    text = str(response.content)
    parsed = parse_tick_json(text)
    if parsed:
        return parsed

    logger.warning("langgraph tick JSON parse failed, attempting recovery")
    try:
        data = json.loads(text.strip())
        if isinstance(data, dict):
            return normalize_tick_output(data)
    except json.JSONDecodeError:
        pass

    return {
        "chronicle_entry": text[:1200] if text and not text.startswith("{") else "",
        "memory_delta": "",
        "session_recap": "",
        "recap_delta": "",
        "suggestions": stub_suggestions(ctx, ctx.prior_suggestions),
        "lore_snippets": [],
    }


def _langgraph_chat(ctx: AgentContext, question: str) -> str:
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model=settings.agent_model, api_key=settings.openai_api_key)
    if ctx.viewer_mode == "player" and ctx.viewer_character:
        name = ctx.viewer_character.get("name") or "your character"
        sys = (
            f"You are Weave, assisting the player of **{name}**. Answer from their knowledge only. "
            "No secret DM info. For maps/portraits, describe what their character would perceive. "
            "Reply in **Markdown** (headings, lists, bold) — plain prose only, never JSON."
        )
    else:
        sys = (
            "You are Weave, assisting the Dungeon Master. Answer using table context only. "
            "For maps/scenes, give DM-ready descriptions. Flag unclear transcript. "
            "Reply in **Markdown** (headings, lists, bold) — plain prose only, never JSON."
        )
    system = SystemMessage(content=sys)
    context = {**build_context_payload(ctx), "question": question}
    human = HumanMessage(content=json.dumps(context, indent=2))
    response = llm.invoke([system, human])
    return str(response.content)
