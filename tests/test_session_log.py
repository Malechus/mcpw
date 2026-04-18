"""
Tests for session_log.py — output file writing.
"""

import csv
import json
import time
from pathlib import Path

import pytest

from mcpw.copilot_runner import SessionResult
from mcpw.session_log import write_all, write_csv_row, write_json, write_markdown


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def session():
    now = time.time()
    return SessionResult(
        command=["copilot"],
        exit_code=0,
        start_time=now,
        end_time=now + 90.5,
        duration_seconds=90.5,
    )


@pytest.fixture()
def summary():
    return {
        "models_used": ["gpt-4o", "claude-3-5-sonnet"],
        "agents_used": ["search", "code-review"],
        "token_estimate": 12500,
        "subagent_interactions": [
            {"from": "user", "to": "search", "summary": "looked up API docs"},
        ],
    }


# ── Markdown ──────────────────────────────────────────────────────────────────

class TestWriteMarkdown:
    def test_file_is_created(self, tmp_path, session, summary):
        out = tmp_path / "session.md"
        write_markdown(out, session, summary, model="gpt-4o")
        assert out.exists()

    def test_contains_session_header(self, tmp_path, session, summary):
        out = tmp_path / "session.md"
        write_markdown(out, session, summary, model="gpt-4o")
        content = out.read_text()
        assert "# Session log" in content

    def test_contains_model_name(self, tmp_path, session, summary):
        out = tmp_path / "session.md"
        write_markdown(out, session, summary, model="gpt-4o")
        assert "gpt-4o" in out.read_text()

    def test_contains_subagent_interaction(self, tmp_path, session, summary):
        out = tmp_path / "session.md"
        write_markdown(out, session, summary, model=None)
        assert "looked up API docs" in out.read_text()

    def test_no_summary_shows_placeholder(self, tmp_path, session):
        out = tmp_path / "session.md"
        write_markdown(out, session, {}, model=None)
        assert "No subagent interaction data" in out.read_text()


# ── JSON ──────────────────────────────────────────────────────────────────────

class TestWriteJson:
    def test_file_is_valid_json(self, tmp_path, session, summary):
        out = tmp_path / "session.json"
        write_json(out, session, summary, model="gpt-4o")
        data = json.loads(out.read_text())
        assert isinstance(data, dict)

    def test_exit_code_in_json(self, tmp_path, session, summary):
        out = tmp_path / "session.json"
        write_json(out, session, summary, model=None)
        data = json.loads(out.read_text())
        assert data["exit_code"] == 0

    def test_model_in_json(self, tmp_path, session, summary):
        out = tmp_path / "session.json"
        write_json(out, session, summary, model="gpt-4o")
        data = json.loads(out.read_text())
        assert data["model"] == "gpt-4o"

    def test_token_estimate_in_json(self, tmp_path, session, summary):
        out = tmp_path / "session.json"
        write_json(out, session, summary, model=None)
        data = json.loads(out.read_text())
        assert data["token_estimate"] == 12500


# ── CSV ───────────────────────────────────────────────────────────────────────

class TestWriteCsvRow:
    def test_creates_file_with_header(self, tmp_path, session, summary):
        csv_path = tmp_path / "sessions.csv"
        write_csv_row(csv_path, session, summary, model=None)
        rows = list(csv.DictReader(csv_path.open()))
        assert len(rows) == 1

    def test_appends_on_second_call(self, tmp_path, session, summary):
        csv_path = tmp_path / "sessions.csv"
        write_csv_row(csv_path, session, summary, model=None)
        write_csv_row(csv_path, session, summary, model=None)
        rows = list(csv.DictReader(csv_path.open()))
        assert len(rows) == 2

    def test_duration_in_csv(self, tmp_path, session, summary):
        csv_path = tmp_path / "sessions.csv"
        write_csv_row(csv_path, session, summary, model=None)
        rows = list(csv.DictReader(csv_path.open()))
        assert float(rows[0]["duration_seconds"]) == pytest.approx(90.5)

    def test_agents_pipe_separated(self, tmp_path, session, summary):
        csv_path = tmp_path / "sessions.csv"
        write_csv_row(csv_path, session, summary, model=None)
        rows = list(csv.DictReader(csv_path.open()))
        assert rows[0]["agents_used"] == "search|code-review"


# ── write_all integration ─────────────────────────────────────────────────────

class TestWriteAll:
    def test_all_three_files_are_created(self, tmp_path, session, summary):
        write_all(session=session, summary=summary, log_dir=tmp_path, model="gpt-4o")
        files = list(tmp_path.iterdir())
        extensions = {f.suffix for f in files}
        assert ".md" in extensions
        assert ".json" in extensions
        assert ".csv" in extensions
