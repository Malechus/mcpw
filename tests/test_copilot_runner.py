"""
Tests for copilot_runner.py — command construction and session result shape.
"""

import time
from unittest.mock import MagicMock, patch

from mcpw.copilot_runner import SessionResult, build_command, run_session


class TestBuildCommand:
    def test_simple_command(self):
        assert build_command("copilot", []) == ["copilot"]

    def test_command_with_extra_args(self):
        result = build_command("copilot", ["--model", "gpt-4o"])
        assert result == ["copilot", "--model", "gpt-4o"]

    def test_multi_word_base_command(self):
        result = build_command("gh copilot", ["suggest"])
        assert result == ["gh", "copilot", "suggest"]

    def test_extra_args_are_appended_after_base(self):
        result = build_command("copilot", ["a", "b", "c"])
        assert result[:1] == ["copilot"]
        assert result[1:] == ["a", "b", "c"]


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
