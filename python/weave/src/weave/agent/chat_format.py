"""Normalize agent chat replies for display (Markdown prose, not JSON blobs)."""

from __future__ import annotations

import json
import re
from typing import Any


def normalize_chat_reply(text: str) -> str:
    """Strip JSON wrappers and code fences; return user-facing Markdown."""
    cleaned = text.strip()
    if not cleaned:
        return ""

    if "```" in cleaned:
        match = re.search(r"```(?:markdown|md)?\s*([\s\S]*?)```", cleaned, re.IGNORECASE)
        if match:
            cleaned = match.group(1).strip()
        else:
            cleaned = re.sub(r"^```\w*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()

    if cleaned.startswith("{") and cleaned.endswith("}"):
        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                for key in ("reply", "answer", "response", "content", "message", "text"):
                    val = data.get(key)
                    if isinstance(val, str) and val.strip():
                        return normalize_chat_reply(val)
        except json.JSONDecodeError:
            pass

    return cleaned
