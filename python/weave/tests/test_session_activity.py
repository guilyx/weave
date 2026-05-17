import pytest

from weave.session_activity import _event_to_item


def test_recap_event_with_entry_maps_to_chronicle():
    item = _event_to_item(
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "event_type": "recap",
            "ts": "2026-05-17T12:00:00+00:00",
            "payload": {
                "_activity_id": "chronicle-abc",
                "entry": {"id": "abc", "body": "The party entered the crypt."},
                "text": "joined",
            },
        }
    )
    assert item["id"] == "chronicle-abc"
    assert item["kind"] == "chronicle"
    assert item["body"] == "The party entered the crypt."
