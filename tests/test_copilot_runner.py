"""
Tests for copilot_runner.py — command construction and session result shape.
"""

import time
from unittest.mock import MagicMock, patch

from mcpw.config import DEFAULT_TOOL_ALLOWANCES
from mcpw.copilot_runner import SessionResult, build_command, run_session


class TestBuildCommand:
    def test_simple_command_no_allowances(self):
        assert build_command("copilot", [], []) == ["copilot"]

    def test_command_with_extra_args_no_allowances(self):
        result = build_command("copilot", ["--model", "gpt-4o"], [])
        assert result == ["copilot", "--model", "gpt-4o"]

    def test_multi_word_base_command(self):
        result = build_command("gh copilot", ["suggest"], [])
        assert result == ["gh", "copilot", "suggest"]

    def test_extra_args_are_appended_after_allowances(self):
        result = build_command("copilot", ["extra"], ["shell(ls:*)"])
        assert result == ["copilot", "--allow-tool=shell(ls:*)", "extra"]

    def test_tool_allowances_become_allow_tool_flags(self):
        allowances = ["shell(ls:*)", "shell(cat:*)"]
        result = build_command("copilot", [], allowances)
        assert "--allow-tool=shell(ls:*)" in result
        assert "--allow-tool=shell(cat:*)" in result

    def test_allowances_precede_extra_args(self):
        result = build_command("copilot", ["--model", "gpt-4o"], ["shell(ls:*)"])
        allow_idx = result.index("--allow-tool=shell(ls:*)")
        model_idx = result.index("--model")
        assert allow_idx < model_idx

    def test_none_allowances_produces_no_flags(self):
        result = build_command("copilot", ["arg"], None)
        assert not any(t.startswith("--allow-tool=") for t in result)

    def test_default_allowances_all_present(self):
        result = build_command("copilot", [], DEFAULT_TOOL_ALLOWANCES)
        for allowance in DEFAULT_TOOL_ALLOWANCES:
            assert f"--allow-tool={allowance}" in result

    def test_default_allowances_count(self):
        result = build_command("copilot", [], DEFAULT_TOOL_ALLOWANCES)
        allow_flags = [t for t in result if t.startswith("--allow-tool=")]
        assert len(allow_flags) == len(DEFAULT_TOOL_ALLOWANCES)


class TestRunSession:
    def test_returns_session_result(self):
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("mcpw.copilot_runner.subprocess.run", return_value=mock_result):
            session = run_session(["copilot"])

        assert isinstance(session, SessionResult)

    def test_exit_code_is_captured(self):
        mock_result = MagicMock()
        mock_result.returncode = 42

        with patch("mcpw.copilot_runner.subprocess.run", return_value=mock_result):
            session = run_session(["copilot"])

        assert session.exit_code == 42

    def test_command_is_stored(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        cmd = ["copilot", "--model", "gpt-4o"]

        with patch("mcpw.copilot_runner.subprocess.run", return_value=mock_result):
            session = run_session(cmd)

        assert session.command == cmd

    def test_timing_fields_are_populated(self):
        mock_result = MagicMock()
        mock_result.returncode = 0

        before = time.time()
        with patch("mcpw.copilot_runner.subprocess.run", return_value=mock_result):
            session = run_session(["copilot"])
        after = time.time()

        assert before <= session.start_time <= after
        assert before <= session.end_time <= after
        assert session.duration_seconds >= 0



class TestRunSession:
    def test_returns_session_result(self):
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("mcpw.copilot_runner.subprocess.run", return_value=mock_result):
            session = run_session(["copilot"])

        assert isinstance(session, SessionResult)

    def test_exit_code_is_captured(self):
        mock_result = MagicMock()
        mock_result.returncode = 42

        with patch("mcpw.copilot_runner.subprocess.run", return_value=mock_result):
            session = run_session(["copilot"])

        assert session.exit_code == 42

    def test_command_is_stored(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        cmd = ["copilot", "--model", "gpt-4o"]

        with patch("mcpw.copilot_runner.subprocess.run", return_value=mock_result):
            session = run_session(cmd)

        assert session.command == cmd

    def test_timing_fields_are_populated(self):
        mock_result = MagicMock()
        mock_result.returncode = 0

        before = time.time()
        with patch("mcpw.copilot_runner.subprocess.run", return_value=mock_result):
            session = run_session(["copilot"])
        after = time.time()

        assert before <= session.start_time <= after
        assert before <= session.end_time <= after
        assert session.duration_seconds >= 0
