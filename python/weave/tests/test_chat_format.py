from weave.agent.chat_format import normalize_chat_reply


def test_strips_markdown_fence():
    raw = "```markdown\n## Scene\n\n- Torchlight\n```"
    assert "## Scene" in normalize_chat_reply(raw)


def test_extracts_json_reply_field():
    raw = '{"reply": "**The dragon** roars."}'
    assert normalize_chat_reply(raw) == "**The dragon** roars."


def test_plain_markdown_unchanged():
    text = "### Map brief\n\n1. North gate\n2. Courtyard"
    assert normalize_chat_reply(text) == text
