from weave.agent.prompts import normalize_tick_output, parse_tick_json


def test_parse_tick_json():
    raw = """```json
    {"chronicle_entry": "The party fled.", "memory_delta": "They ran.",
     "suggestions": ["Track HP"], "lore_snippets": []}
    ```"""
    out = parse_tick_json(raw)
    assert out is not None
    assert out["chronicle_entry"] == "The party fled."
    assert out["suggestions"] == ["Track HP"]


def test_parse_tick_json_from_prose_wrapped_object():
    raw = """Here is the update:

    {"chronicle_entry": "They opened the door.", "memory_delta": "",
     "suggestions": ["Check traps"], "lore_snippets": []}

    Hope that helps."""
    out = parse_tick_json(raw)
    assert out is not None
    assert out["chronicle_entry"] == "They opened the door."


def test_normalize_tick_output():
    out = normalize_tick_output(
        {
            "chronicle_entry": "  x ",
            "suggestions": "not a list",
            "memory_delta": 1,
        }
    )
    assert out["chronicle_entry"] == "x"
    assert out["suggestions"] == []
