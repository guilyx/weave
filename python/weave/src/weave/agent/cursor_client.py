"""Cursor Agent CLI integration (ask mode by default).

Uses the `agent` binary: `agent --print --mode ask --output-format json`
See: https://cursor.com/docs/cli/using
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from dataclasses import dataclass

from weave.config import settings

logger = logging.getLogger(__name__)

# Linux ARG_MAX is often ~2MB; huge JSON prompts must not be argv (E2BIG).
_MAX_ARGV_PROMPT_BYTES = 32_000


@dataclass
class CursorRunResult:
    text: str
    session_id: str | None
    is_error: bool


def run_cursor_ask(
    prompt: str,
    *,
    cursor_session_id: str | None = None,
) -> CursorRunResult:
    """Run Cursor agent in ask (read-only) mode and return the final text."""
    bin_path = settings.cursor_agent_bin
    mode = settings.cursor_agent_mode
    workspace = settings.cursor_workspace

    cmd = [
        bin_path,
        "--print",
        "--mode",
        mode,
        "--trust",
        "--output-format",
        "json",
        "--workspace",
        workspace,
    ]
    if cursor_session_id:
        cmd.extend(["--resume", cursor_session_id])
    if settings.cursor_model:
        cmd.extend(["--model", settings.cursor_model])

    use_stdin = len(prompt.encode("utf-8")) > _MAX_ARGV_PROMPT_BYTES
    if not use_stdin:
        cmd.append(prompt)

    env = os.environ.copy()
    if settings.cursor_api_key:
        env["CURSOR_API_KEY"] = settings.cursor_api_key

    logger.debug(
        "cursor agent: %s (prompt_bytes=%d stdin=%s)",
        " ".join(cmd),
        len(prompt.encode("utf-8")),
        use_stdin,
    )
    try:
        proc = subprocess.run(
            cmd,
            input=prompt if use_stdin else None,
            capture_output=True,
            text=True,
            timeout=settings.cursor_timeout_seconds,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Cursor agent timed out after {settings.cursor_timeout_seconds}s") from exc

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        raise RuntimeError(
            f"Cursor agent failed (exit {proc.returncode}): {stderr or stdout or 'unknown error'}"
        )

    parsed = _parse_json_result(proc.stdout or "")
    return parsed


def _parse_json_result(stdout: str) -> CursorRunResult:
    """Parse the final JSON line from --output-format json."""
    lines = [ln.strip() for ln in stdout.splitlines() if ln.strip()]
    for line in reversed(lines):
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if data.get("type") == "result":
            return CursorRunResult(
                text=str(data.get("result") or ""),
                session_id=data.get("session_id"),
                is_error=bool(data.get("is_error")),
            )
    # Fallback: plain text stdout
    return CursorRunResult(text=stdout.strip(), session_id=None, is_error=False)
