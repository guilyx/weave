from unittest.mock import patch

from weave.agent.cursor_client import _MAX_ARGV_PROMPT_BYTES, _parse_json_result, run_cursor_ask


def test_large_prompt_uses_stdin_not_argv():
    huge = "x" * (_MAX_ARGV_PROMPT_BYTES + 1000)
    with patch("weave.agent.cursor_client.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"type":"result","result":"{}","is_error":false}\n'
        mock_run.return_value.stderr = ""
        run_cursor_ask(huge)
        _cmd, kwargs = mock_run.call_args
        cmd = _cmd[0]
        assert huge not in cmd
        assert kwargs.get("input") == huge


def test_parse_json_result_line():
    stdout = '{"type":"result","result":"Hello","session_id":"abc","is_error":false}\n'
    r = _parse_json_result(stdout)
    assert r.text == "Hello"
    assert r.session_id == "abc"
    assert not r.is_error
