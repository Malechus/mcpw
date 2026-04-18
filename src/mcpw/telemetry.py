"""
telemetry.py — Parses the exit telemetry block printed by Copilot CLI.

When a Copilot session ends it prints a summary block, e.g.:

  ╭─╮╭─╮   Changes   +1815 -122
  ╰─╯╰─╯   Requests  7 Premium (1h 47m 26s)
  █ ▘▝ █   Tokens    ↑ 4.2m • ↓ 66.9k • 3.9m (cached) • 8.7k (reasoning)
   ▔▔▔▔    Resume    copilot --resume=cb939fc7-14d0-45db-bdca-905630c1d116

This module strips ANSI escape codes from the raw captured output and
extracts the structured fields for inclusion in the session logs.
"""

from __future__ import annotations

import re


# Matches ANSI/VT escape sequences (CSI, OSC, SS3, etc.)
_ANSI_ESCAPE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def _strip_ansi(text: str) -> str:
    return _ANSI_ESCAPE.sub("", text)


def _parse_count(s: str) -> float | None:
    """
    Parse a human-formatted number such as '4.2m', '66.9k', or '1815'.
    Returns None when the string cannot be parsed.
    """
    s = s.strip()
    if not s:
        return None
    m = re.match(r"^([0-9]+(?:\.[0-9]+)?)([kmb]?)$", s.lower())
    if not m:
        return None
    val = float(m.group(1))
    suffix = m.group(2)
    if suffix == "k":
        val *= 1_000
    elif suffix == "m":
        val *= 1_000_000
    elif suffix == "b":
        val *= 1_000_000_000
    return val


def parse_copilot_telemetry(text: str) -> dict:
    """
    Extract structured telemetry from Copilot's exit output.

    Returns a dict with zero or more of the following keys (keys are omitted,
    not set to None, when not found in the output):

        changes_added (int)         — lines / files added
        changes_removed (int)       — lines / files removed
        requests_count (int)        — total API requests made
        requests_tier (str)         — request tier, e.g. "Premium"
        requests_duration (str)     — wall-clock time, e.g. "1h 47m 26s"
        tokens_sent (float)         — tokens sent upstream (↑)
        tokens_received (float)     — tokens received from model (↓)
        tokens_cached (float)       — cached tokens
        tokens_reasoning (float)    — reasoning tokens
        resume_id (str)             — session resume UUID
    """
    if not text:
        return {}

    clean = _strip_ansi(text)
    result: dict = {}

    # Changes: +N -N
    m = re.search(r"Changes\s+\+(\d[\d,]*)\s+-(\d[\d,]*)", clean)
    if m:
        result["changes_added"] = int(m.group(1).replace(",", ""))
        result["changes_removed"] = int(m.group(2).replace(",", ""))

    # Requests: N Tier (duration)
    m = re.search(r"Requests\s+(\d+)\s+(\w+)(?:\s+\(([^)]+)\))?", clean)
    if m:
        result["requests_count"] = int(m.group(1))
        result["requests_tier"] = m.group(2)
        if m.group(3):
            result["requests_duration"] = m.group(3)

    # Tokens line: ↑ N • ↓ N • N (cached) • N (reasoning)
    m = re.search(r"Tokens\s+(.+?)(?:\r?\n|$)", clean)
    if m:
        token_line = m.group(1)
        sent = re.search(r"↑\s*([\d.]+[kmb]?)", token_line, re.IGNORECASE)
        if sent:
            result["tokens_sent"] = _parse_count(sent.group(1))
        recv = re.search(r"↓\s*([\d.]+[kmb]?)", token_line, re.IGNORECASE)
        if recv:
            result["tokens_received"] = _parse_count(recv.group(1))
        cached = re.search(r"([\d.]+[kmb]?)\s*\(cached\)", token_line, re.IGNORECASE)
        if cached:
            result["tokens_cached"] = _parse_count(cached.group(1))
        reasoning = re.search(r"([\d.]+[kmb]?)\s*\(reasoning\)", token_line, re.IGNORECASE)
        if reasoning:
            result["tokens_reasoning"] = _parse_count(reasoning.group(1))

    # Resume: copilot --resume=<uuid>
    m = re.search(r"Resume\s+copilot\s+--resume=([a-f0-9-]+)", clean)
    if m:
        result["resume_id"] = m.group(1)

    return result
