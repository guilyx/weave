import json
from pathlib import Path

from weave.ddb.normalize import normalize_legacy, normalize_v5

FIXTURES = Path(__file__).parent / "fixtures"


def test_legacy_sample_normalizes():
    raw = (FIXTURES / "legacy_sample.json").read_text()
    data = json.loads(raw)
    sheet = normalize_legacy(12345, data)
    assert sheet.name == "Bhaal"
    assert sheet.race == "Half-Orc"
    assert len(sheet.classes) == 1
    assert sheet.classes[0].name == "Warlock"
    assert sheet.abilities["str"].score == 6
    assert sheet.abilities["str"].modifier == -2
    assert sheet.abilities["cha"].modifier == 3
    assert sheet.raw_source == "legacy"


def test_v5_wrapper_normalizes():
    data = {
        "data": {
            "name": "Ezra",
            "race": {"fullName": "Lightfoot Halfling"},
            "classes": [{"level": 3, "definition": {"name": "Rogue"}}],
            "stats": [
                {"id": 1, "value": 10},
                {"id": 2, "value": 16},
                {"id": 3, "value": 10},
                {"id": 4, "value": 12},
                {"id": 5, "value": 10},
                {"id": 6, "value": 14},
            ],
        }
    }
    sheet = normalize_v5(99, data)
    assert sheet.name == "Ezra"
    assert "Rogue" in sheet.class_summary


def test_legacy_with_gear_extracts_items_features_spells():
    raw = (FIXTURES / "legacy_with_gear.json").read_text()
    data = json.loads(raw)
    sheet = normalize_legacy(42, data)
    assert sheet.speed == 30
    assert sheet.alignment == "Chaotic Good"
    assert sheet.proficiency_bonus == 2
    assert len(sheet.items) == 2
    equipped = [i for i in sheet.items if i.equipped]
    assert any(i.name == "Staff of Power" for i in equipped)
    assert any(i.name == "Healing Potion" for i in sheet.items if not i.equipped)
    assert any(f.name == "War Caster" for f in sheet.features)
    assert any(s.name == "Shield" for s in sheet.spells)


def test_legacy_race_as_string():
    sheet = normalize_legacy(1, {"name": "Test", "race": "Human", "classes": []})
    assert sheet.race == "Human"
