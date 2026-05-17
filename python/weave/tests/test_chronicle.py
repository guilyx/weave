from uuid import uuid4

from weave.agent.prompts import extract_chronicle_entry, normalize_tick_output
from weave.agent.recap import stub_chronicle_entry
from weave.agent.context import AgentContext
from weave.chronicle import (
    chapter_stt_range,
    join_entries_text,
    legacy_chapter_from_tick_order,
    merge_chapter_body,
    stt_chapter_index,
    viewer_key_for_mode,
)


def test_extract_chronicle_entry_prefers_explicit_field():
    out = normalize_tick_output(
        {
            "chronicle_entry": "The party entered the crypt.",
            "session_recap": "FULL REWRITE SHOULD IGNORE",
            "memory_delta": "",
        }
    )
    assert extract_chronicle_entry(out) == "The party entered the crypt."


def test_extract_ignores_full_session_recap():
    out = {"session_recap": "Entire session rewritten", "chronicle_entry": ""}
    assert extract_chronicle_entry(out) == ""


def test_join_entries_text():
    entries = [
        {"id": "1", "body": "First beat."},
        {"id": "2", "body": "Second beat."},
    ]
    assert join_entries_text(entries) == "First beat.\n\nSecond beat."


def test_viewer_key_for_mode():
    cid = uuid4()
    assert viewer_key_for_mode("dm", None) == "dm"
    assert viewer_key_for_mode("player", cid) == f"player:{cid}"


def test_legacy_chapter_from_tick_order_collapses_ticks():
    # 101 agent ticks, 150 STT lines → ~5 chapters not 101
    assert legacy_chapter_from_tick_order(1, 101, 150) == 1
    assert legacy_chapter_from_tick_order(21, 101, 150) == 1
    assert legacy_chapter_from_tick_order(22, 101, 150) == 2
    assert legacy_chapter_from_tick_order(101, 101, 150) == 5


def test_stt_chapter_index_buckets():
    assert stt_chapter_index(1, size=30) == 1
    assert stt_chapter_index(30, size=30) == 1
    assert stt_chapter_index(31, size=30) == 2
    assert stt_chapter_index(60, size=30) == 2
    assert stt_chapter_index(61, size=30) == 3
    assert chapter_stt_range(2, size=30) == (31, 60)


def test_merge_chapter_body_dedupes():
    a = "The party entered."
    b = merge_chapter_body(a, "They lit a torch.")
    assert "torch" in b
    assert merge_chapter_body(b, "They lit a torch.") == b


def test_stub_chronicle_entry_not_empty_with_pending():
    ctx = AgentContext(campaign_name="T", pending_transcript="dragon roars")
    text = stub_chronicle_entry(ctx, "dragon roars")
    assert text
    assert "dragon" in text.lower()
