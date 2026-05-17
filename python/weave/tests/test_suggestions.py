from weave.agent.context import AgentContext
from weave.agent.suggestions import stub_suggestions


def test_stub_suggestions_uses_transcript_not_generic_combat_only():
    ctx = AgentContext(
        campaign_name="Test",
        transcript_window=["The party negotiates with the innkeeper about a hidden map."],
        prior_suggestions=[
            "Confirm initiative order if combat just started.",
            "Note any HP changes or conditions mentioned.",
        ],
    )
    tips = stub_suggestions(ctx, ctx.prior_suggestions)
    assert tips
    assert not any("initiative order" in t.lower() for t in tips)
    assert any("npc" in t.lower() or "clue" in t.lower() or "follow up" in t.lower() for t in tips)


def test_stub_suggestions_avoids_repeats():
    prior = ["Track initiative and HP changes on the table."]
    ctx = AgentContext(
        campaign_name="Test",
        transcript_window=["Roll initiative! The goblin attacks."],
        prior_suggestions=prior,
    )
    tips = stub_suggestions(ctx, prior)
    assert all(t not in prior for t in tips)
