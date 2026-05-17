from weave.agent.context import AgentContext
from weave.agent.recap import looks_like_raw_transcript, stub_memory_beat, stub_chronicle_entry


def test_looks_like_raw_transcript():
    assert looks_like_raw_transcript("Table audio condensed: hello")
    assert looks_like_raw_transcript("short line no punctuation")
    assert not looks_like_raw_transcript(
        "The party entered the tavern. The barkeep eyed them warily."
    )


def test_stub_chronicle_entry_one_beat():
    ctx = AgentContext(
        campaign_name="Test",
        chronicle_entries=[
            {
                "id": "abc",
                "body": "They had reached the mountain pass.",
                "created_at": "2026-01-01T12:00:00Z",
            }
        ],
    )
    entry = stub_chronicle_entry(ctx, "uh yeah the dragon roars loudly")
    assert "uh yeah" not in entry
    assert "dragon" in entry.lower()
