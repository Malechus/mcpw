"""
session_log.py — Writes the three post-session output files.

After each Copilot session the wrapper produces:

  1. <log_dir>/<session_id>_session.md   — Human-readable markdown log
     focusing on subagent interactions and session narrative.

  2. <log_dir>/<session_id>_session.json — Structured JSON metadata
     (timing, exit code, model, raw summary data).

  3. <log_dir>/sessions.csv              — Appended CSV row for aggregate
     analysis (token spend, duration, models, agents used, etc.).
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from mcpw.copilot_runner import SessionResult


# ── Session ID ────────────────────────────────────────────────────────────────

def _session_id(start_time: float) -> str:
    """Return a filesystem-safe timestamp string like 2024-05-01_14-30-00."""
    dt = datetime.fromtimestamp(start_time, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d_%H-%M-%S")


# ── 1. Human-readable markdown log ───────────────────────────────────────────

def write_markdown(
    path: Path,
    session: SessionResult,
    summary: dict,
    model: str | None,
    copilot_telemetry: dict | None = None,
) -> None:
    """Write a human-readable markdown session log."""
    sid = _session_id(session.start_time)
    start_dt = datetime.fromtimestamp(session.start_time, tz=timezone.utc)
    end_dt = datetime.fromtimestamp(session.end_time, tz=timezone.utc)

    lines: list[str] = [
        f"# Session log — {sid}",
        "",
        "## Session info",
        "",
        f"- **Start:**    {start_dt.isoformat()}",
        f"- **End:**      {end_dt.isoformat()}",
        f"- **Duration:** {session.duration_seconds:.1f}s",
        f"- **Exit code:** {session.exit_code}",
        f"- **Model:**    {model or '(Copilot default)'}",
        f"- **Command:**  `{' '.join(session.command)}`",
        "",
    ]

    # Subagent interactions section — populated from Copilot's summary.
    interactions = summary.get("subagent_interactions") or []
    lines += [
        "## Subagent interactions",
        "",
    ]
    if interactions:
        for item in interactions:
            src = item.get("from", "?")
            dst = item.get("to", "?")
            note = item.get("summary", "")
            lines.append(f"- **{src}** → **{dst}**: {note}")
        lines.append("")
    else:
        lines += ["_No subagent interaction data was captured for this session._", ""]

    # Models and agents used.
    models_used: list[str] = summary.get("models_used") or []
    agents_used: list[str] = summary.get("agents_used") or []
    token_estimate = summary.get("token_estimate")

    lines += ["## Resource usage", ""]
    if models_used:
        lines.append(f"- **Models used:** {', '.join(models_used)}")
    if agents_used:
        lines.append(f"- **Agents used:** {', '.join(agents_used)}")
    if token_estimate is not None:
        lines.append(f"- **Token estimate:** {token_estimate:,}")
    if not models_used and not agents_used and token_estimate is None:
        lines.append("_No resource usage data was captured for this session._")
    lines.append("")

    # Copilot exit telemetry (parsed from stdout).
    tel = copilot_telemetry or {}
    if tel:
        lines += ["## Copilot exit telemetry", ""]
        if "changes_added" in tel or "changes_removed" in tel:
            lines.append(
                f"- **Changes:** +{tel.get('changes_added', '?')} -{tel.get('changes_removed', '?')}"
            )
        if "requests_count" in tel:
            req = f"- **Requests:** {tel['requests_count']}"
            if "requests_tier" in tel:
                req += f" {tel['requests_tier']}"
            if "requests_duration" in tel:
                req += f" ({tel['requests_duration']})"
            lines.append(req)
        if any(k in tel for k in ("tokens_sent", "tokens_received", "tokens_cached", "tokens_reasoning")):
            parts = []
            if "tokens_sent" in tel:
                parts.append(f"↑ {tel['tokens_sent']:,.0f}")
            if "tokens_received" in tel:
                parts.append(f"↓ {tel['tokens_received']:,.0f}")
            if "tokens_cached" in tel:
                parts.append(f"{tel['tokens_cached']:,.0f} (cached)")
            if "tokens_reasoning" in tel:
                parts.append(f"{tel['tokens_reasoning']:,.0f} (reasoning)")
            lines.append(f"- **Tokens:** {' • '.join(parts)}")
        if "resume_id" in tel:
            lines.append(f"- **Resume ID:** `{tel['resume_id']}`")
        lines.append("")

    # Raw fallback — if Copilot wrote something we couldn't parse.
    raw = summary.get("raw_summary")
    if raw:
        lines += ["## Raw session summary (unparsed)", "", "```", raw, "```", ""]

    path.write_text("\n".join(lines), encoding="utf-8")


# ── 2. Structured JSON metadata ───────────────────────────────────────────────

def write_json(
    path: Path,
    session: SessionResult,
    summary: dict,
    model: str | None,
    copilot_telemetry: dict | None = None,
) -> None:
    """Write structured JSON metadata for the session."""
    payload = {
        "session_id": _session_id(session.start_time),
        "start_time": session.start_time,
        "end_time": session.end_time,
        "duration_seconds": session.duration_seconds,
        "exit_code": session.exit_code,
        "model": model,
        "command": session.command,
        "models_used": summary.get("models_used"),
        "agents_used": summary.get("agents_used"),
        "token_estimate": summary.get("token_estimate"),
        "subagent_interactions": summary.get("subagent_interactions"),
        "copilot_telemetry": copilot_telemetry or {},
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


# ── 3. Aggregate CSV ──────────────────────────────────────────────────────────

CSV_FIELDNAMES = [
    "session_id",
    "date",
    "start_time",
    "end_time",
    "duration_seconds",
    "exit_code",
    "model",
    "copilot_cmd",
    "models_used",
    "agents_used",
    "token_estimate",
    # Copilot exit telemetry (parsed from stdout)
    "changes_added",
    "changes_removed",
    "requests_count",
    "requests_tier",
    "requests_duration",
    "tokens_sent",
    "tokens_received",
    "tokens_cached",
    "tokens_reasoning",
    "resume_id",
]


def write_csv_row(
    path: Path,
    session: SessionResult,
    summary: dict,
    model: str | None,
    copilot_telemetry: dict | None = None,
) -> None:
    """Append one row to the aggregate CSV (creates file + header if needed)."""
    sid = _session_id(session.start_time)
    start_dt = datetime.fromtimestamp(session.start_time, tz=timezone.utc)
    tel = copilot_telemetry or {}

    row = {
        "session_id": sid,
        "date": start_dt.date().isoformat(),
        "start_time": session.start_time,
        "end_time": session.end_time,
        "duration_seconds": round(session.duration_seconds, 3),
        "exit_code": session.exit_code,
        "model": model or "",
        "copilot_cmd": session.command[0] if session.command else "",
        # Lists are serialised as pipe-separated strings for readability.
        "models_used": "|".join(summary.get("models_used") or []),
        "agents_used": "|".join(summary.get("agents_used") or []),
        "token_estimate": summary.get("token_estimate") or "",
        # Copilot exit telemetry
        "changes_added": tel.get("changes_added", ""),
        "changes_removed": tel.get("changes_removed", ""),
        "requests_count": tel.get("requests_count", ""),
        "requests_tier": tel.get("requests_tier", ""),
        "requests_duration": tel.get("requests_duration", ""),
        "tokens_sent": tel.get("tokens_sent", ""),
        "tokens_received": tel.get("tokens_received", ""),
        "tokens_cached": tel.get("tokens_cached", ""),
        "tokens_reasoning": tel.get("tokens_reasoning", ""),
        "resume_id": tel.get("resume_id", ""),
    }

    write_header = not path.exists() or path.stat().st_size == 0

    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


# ── Combined writer ───────────────────────────────────────────────────────────

def write_all(
    session: SessionResult,
    summary: dict,
    log_dir: Path,
    model: str | None,
    copilot_telemetry: dict | None = None,
) -> None:
    """Write all three output files for a completed session."""
    sid = _session_id(session.start_time)

    write_markdown(
        path=log_dir / f"{sid}_session.md",
        session=session,
        summary=summary,
        model=model,
        copilot_telemetry=copilot_telemetry,
    )
    write_json(
        path=log_dir / f"{sid}_session.json",
        session=session,
        summary=summary,
        model=model,
        copilot_telemetry=copilot_telemetry,
    )
    write_csv_row(
        path=log_dir / "sessions.csv",
        session=session,
        summary=summary,
        model=model,
        copilot_telemetry=copilot_telemetry,
    )
