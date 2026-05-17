from weave.agent.context import AgentContext
from weave.agent.session import run_agent_tick
from weave.config import settings


def test_stub_tick_without_api_key():
    settings.openai_api_key = None
    settings.agent_backend = "stub"
    ctx = AgentContext(
        campaign_name="Test",
        pending_transcript="The dragon roars.",
        transcript_window=["The dragon roars."],
    )
    out = run_agent_tick(session_id="s1", ctx=ctx)
    entry = (out.get("chronicle_entry") or out.get("memory_delta") or "").lower()
    assert "dragon" in entry
    assert out["suggestions"]
    mem = out.get("memory_delta") or ""
    assert "uh yeah" not in mem.lower()
    assert mem != "The dragon roars."
