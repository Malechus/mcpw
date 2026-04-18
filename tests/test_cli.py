"""
Tests for cli.py — argument parsing behaviour.
"""

import sys

import pytest

from mcpw.cli import build_parser


class TestBuildParser:
    def setup_method(self):
        self.parser = build_parser()

    def test_defaults_with_no_args(self):
        args = self.parser.parse_args([])
        assert args.config is None
        assert args.log_dir is None
        assert args.model is None
        assert args.no_inject is False
        assert args.copilot_args == []

    def test_log_dir_flag(self):
        args = self.parser.parse_args(["--log-dir", "/tmp/logs"])
        assert str(args.log_dir) == "/tmp/logs"

    def test_model_flag(self):
        args = self.parser.parse_args(["--model", "gpt-4o"])
        assert args.model == "gpt-4o"

    def test_no_inject_flag(self):
        args = self.parser.parse_args(["--no-inject"])
        assert args.no_inject is True

    def test_config_flag(self, tmp_path):
        cfg_file = tmp_path / "my.toml"
        args = self.parser.parse_args(["--config", str(cfg_file)])
        assert args.config == cfg_file

    def test_copilot_passthrough_args(self):
        args = self.parser.parse_args(["--", "--verbose", "--foo", "bar"])
        assert "--verbose" in args.copilot_args
        assert "--foo" in args.copilot_args
        assert "bar" in args.copilot_args

    def test_no_tool_allowances_flag(self):
        args = self.parser.parse_args(["--no-tool-allowances"])
        assert args.no_tool_allowances is True

    def test_no_tool_allowances_defaults_to_false(self):
        args = self.parser.parse_args([])
        assert args.no_tool_allowances is False

    def test_combined_flags_and_passthrough(self):
        args = self.parser.parse_args(["--model", "gpt-4o", "--no-inject", "--", "extra"])
        assert args.model == "gpt-4o"
        assert args.no_inject is True
        assert "extra" in args.copilot_args
