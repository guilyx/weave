from weave.agent.context import AgentContext, build_context_payload, party_roster_summaries


def test_build_context_payload_includes_campaign_brief_and_party():
    ctx = AgentContext(
        campaign_name="Curse of Strahd",
        campaign_description="Gothic horror",
        ai_brief="Party is level 5, just entered Vallaki.",
        characters=[{"name": "Aria", "race": "Elf", "class_summary": "Wizard 5"}],
        lore=["## Vallaki\nWalled town."],
        past_session_recaps=["### Session 1\nMet the burgomaster."],
        session_recap="Exploring the tavern.",
        transcript_window=["Player: We ask about the vampire."],
        manual_notes=["Remember the holy symbol."],
    )
    payload = build_context_payload(ctx)
    assert payload["campaign"]["ai_brief"] == "Party is level 5, just entered Vallaki."
    assert payload["party_roster"][0]["name"] == "Aria"
    assert payload["party_sheets"][0]["name"] == "Aria"
    assert "Vallaki" in payload["campaign_lore"][0]
    assert payload["past_session_recaps"][0].startswith("### Session 1")
    assert payload["current_session_recap"] == "Exploring the tavern."


def test_party_roster_summaries_handles_dict_snapshots():
    rows = party_roster_summaries(
        [{"name": "Borin", "race": "Dwarf", "class_summary": "Fighter 3", "hit_points": 28}]
    )
    assert rows[0]["name"] == "Borin"
    assert rows[0]["hit_points"] == 28
