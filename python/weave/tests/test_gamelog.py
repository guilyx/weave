from weave.ddb.gamelog import format_game_log_message


def test_format_dice_roll():
    msg = {
        "id": "abc",
        "eventType": "dice/roll/fulfilled",
        "data": {
            "action": "Longbow",
            "context": {"name": "Aelindra"},
            "rolls": [
                {
                    "rollType": "attack",
                    "diceNotation": {
                        "set": [{"count": 1, "dieType": "d20"}],
                        "constant": 5,
                    },
                    "result": {"total": 18, "text": "13+5"},
                }
            ],
        },
    }
    line = format_game_log_message(msg)
    assert line is not None
    assert "Aelindra" in line
    assert "Longbow" in line
    assert "18" in line


def test_format_skips_unknown():
    assert format_game_log_message({"eventType": "other/thing", "data": {}}) is not None
