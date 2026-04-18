"""
Tests for telemetry.py — Copilot exit output parsing.
"""

import pytest

from mcpw.telemetry import _parse_count, _strip_ansi, parse_copilot_telemetry


# ── Sample output ─────────────────────────────────────────────────────────────

# Approximate reproduction of what Copilot CLI prints at exit (ANSI stripped
# for the multiline constant; ANSI variant tested separately).
SAMPLE_OUTPUT = """\
  \u256d\u2500\u256e\u256d\u2500\u256e   Changes   +1815 -122
  \u2570\u2500\u256f\u2570\u2500\u256f   Requests  7 Premium (1h 47m 26s)
  \u2588 \u2598\u259d \u2588   Tokens    \u2191 4.2m \u2022 \u2193 66.9k \u2022 3.9m (cached) \u2022 8.7k (reasoning)
   \u2594\u2594\u2594\u2594    Resume    copilot --resume=cb939fc7-14d0-45db-bdca-905630c1d116
"""


# ── _strip_ansi ───────────────────────────────────────────────────────────────

class TestStripAnsi:
    def test_removes_csi_sequence(self):
        assert _strip_ansi("\x1b[31mred\x1b[0m") == "red"

    def test_removes_bold_sequence(self):
        assert _strip_ansi("\x1b[1mbold\x1b[0m") == "bold"

    def test_passthrough_plain_text(self):
        assert _strip_ansi("hello world") == "hello world"

    def test_empty_string(self):
        assert _strip_ansi("") == ""

    def test_multiple_sequences(self):
        result = _strip_ansi("\x1b[32m+1815\x1b[0m \x1b[31m-122\x1b[0m")
        assert result == "+1815 -122"


# ── _parse_count ──────────────────────────────────────────────────────────────

class TestParseCount:
    def test_plain_integer(self):
        assert _parse_count("1815") == pytest.approx(1815)

    def test_kilo_suffix(self):
        assert _parse_count("66.9k") == pytest.approx(66_900)

    def test_mega_suffix(self):
        assert _parse_count("4.2m") == pytest.approx(4_200_000)

    def test_billion_suffix(self):
        assert _parse_count("1b") == pytest.approx(1_000_000_000)

    def test_no_suffix(self):
        assert _parse_count("8700") == pytest.approx(8700)

    def test_empty_string_returns_none(self):
        assert _parse_count("") is None

    def test_non_numeric_returns_none(self):
        assert _parse_count("abc") is None

    def test_whitespace_stripped(self):
        assert _parse_count("  3.9m  ") == pytest.approx(3_900_000)


# ── parse_copilot_telemetry ───────────────────────────────────────────────────

class TestParseCopilotTelemetry:
    def test_parses_changes_added(self):
        result = parse_copilot_telemetry(SAMPLE_OUTPUT)
        assert result["changes_added"] == 1815

    def test_parses_changes_removed(self):
        result = parse_copilot_telemetry(SAMPLE_OUTPUT)
        assert result["changes_removed"] == 122

    def test_parses_requests_count(self):
        result = parse_copilot_telemetry(SAMPLE_OUTPUT)
        assert result["requests_count"] == 7

    def test_parses_requests_tier(self):
        result = parse_copilot_telemetry(SAMPLE_OUTPUT)
        assert result["requests_tier"] == "Premium"

    def test_parses_requests_duration(self):
        result = parse_copilot_telemetry(SAMPLE_OUTPUT)
        assert result["requests_duration"] == "1h 47m 26s"

    def test_parses_tokens_sent(self):
        result = parse_copilot_telemetry(SAMPLE_OUTPUT)
        assert result["tokens_sent"] == pytest.approx(4_200_000)

    def test_parses_tokens_received(self):
        result = parse_copilot_telemetry(SAMPLE_OUTPUT)
        assert result["tokens_received"] == pytest.approx(66_900)

    def test_parses_tokens_cached(self):
        result = parse_copilot_telemetry(SAMPLE_OUTPUT)
        assert result["tokens_cached"] == pytest.approx(3_900_000)

    def test_parses_tokens_reasoning(self):
        result = parse_copilot_telemetry(SAMPLE_OUTPUT)
        assert result["tokens_reasoning"] == pytest.approx(8_700)

    def test_parses_resume_id(self):
        result = parse_copilot_telemetry(SAMPLE_OUTPUT)
        assert result["resume_id"] == "cb939fc7-14d0-45db-bdca-905630c1d116"

    def test_empty_string_returns_empty_dict(self):
        assert parse_copilot_telemetry("") == {}

    def test_unrelated_output_returns_empty_dict(self):
        assert parse_copilot_telemetry("Starting session...\nDone.\n") == {}

    def test_ansi_codes_are_stripped_before_parsing(self):
        ansi_output = (
            "\x1b[1mChanges\x1b[0m   +500 -10\n"
            "Requests  3 Standard\n"
        )
        result = parse_copilot_telemetry(ansi_output)
        assert result["changes_added"] == 500
        assert result["requests_count"] == 3

    def test_partial_output_returns_available_fields(self):
        partial = "  Requests  2 Standard\n"
        result = parse_copilot_telemetry(partial)
        assert result["requests_count"] == 2
        assert "changes_added" not in result
        assert "tokens_sent" not in result

    def test_no_duration_when_absent(self):
        no_dur = "  Requests  5 Premium\n"
        result = parse_copilot_telemetry(no_dur)
        assert "requests_duration" not in result
