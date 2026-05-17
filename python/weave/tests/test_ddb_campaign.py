from weave.ddb.campaign import parse_campaign_roster


def test_parse_active_characters_shape():
    payload = {
        "data": [
            {
                "characterId": 111,
                "characterName": "Aria",
                "level": 5,
                "className": "Wizard",
            },
            {
                "characterId": 222,
                "characterName": "Borin",
                "level": 5,
                "className": "Fighter",
            },
        ]
    }
    roster = parse_campaign_roster(payload)
    assert len(roster) == 2
    assert roster[0].ddb_character_id == 111
    assert roster[0].name == "Aria"
    assert roster[1].class_summary == "Fighter"
