from weave.agent.context import AgentContext
from weave.agent.prompts import TICK_SYSTEM_PLAYER, _suggestions_audience_hint, build_tick_user_message
from weave.agent.suggestions import tick_instructions_extra


def test_player_suggestions_prompts_are_not_dm_facing():
    ctx = AgentContext(
        campaign_name="Test",
        viewer_mode="player",
        viewer_character={"name": "Aelindra", "class_summary": "Wizard 5"},
    )
    extra = tick_instructions_extra(ctx)
    assert "PLAYER" in extra or "player" in extra
    assert "NOT the Dungeon Master" in extra or "not the Dungeon Master" in extra.lower()
    assert "Ideas for your character" in extra

    hint = _suggestions_audience_hint(ctx)
    assert "PLAYER" in hint
    assert "Aelindra" in hint

    user_msg = build_tick_user_message(ctx, extra)
    assert "suggestions_audience" in user_msg
    assert "PLAYER" in user_msg

    assert "Ideas for your character" in TICK_SYSTEM_PLAYER
    assert "NOT" in TICK_SYSTEM_PLAYER and "Dungeon Master" in TICK_SYSTEM_PLAYER
