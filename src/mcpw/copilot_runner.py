"""
copilot_runner.py — Launches Copilot CLI as a subprocess.

The Copilot process inherits the current terminal (stdin/stdout/stderr),
so the interactive session feels completely normal to the user.
We only measure timing and capture the exit code — we do not intercept
any of Copilot's output.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass


# ── Session result ────────────────────────────────────────────────────────────

@dataclass
class SessionResult:
    """Everything the wrapper knows about a completed Copilot session."""

    command: list[str]       # The exact command that was run
    exit_code: int           # Copilot's exit code (0 = success)
    start_time: float        # Unix timestamp when the session started
    end_time: float          # Unix timestamp when the session ended
    duration_seconds: float  # Total wall-clock time


# ── Command building ──────────────────────────────────────────────────────────

def build_command(
    copilot_cmd: str,
    extra_args: list[str],
    tool_allowances: list[str] | None = None,
) -> list[str]:
    """
    Combine the base Copilot command with tool allowance flags and extra args.

    --allow-tool= flags are prepended before extra_args so Copilot sees them
    before any user-supplied passthrough arguments.

    Example:
        build_command("copilot", ["--model", "gpt-4o"], ["shell(ls:*)"])
        # → ["copilot", "--allow-tool=shell(ls:*)", "--model", "gpt-4o"]
    """
    allow_flags = [f"--allow-tool={t}" for t in (tool_allowances or [])]
    return [*copilot_cmd.split(), *allow_flags, *extra_args]


# ── Session runner ────────────────────────────────────────────────────────────

def run_session(command: list[str]) -> SessionResult:
    """
    Run the Copilot CLI command and wait for it to finish.

    The user interacts with Copilot normally in their terminal.
    Returns a SessionResult once the process exits.
    """
    start = time.time()

    # subprocess.run with no stdout/stderr redirection lets Copilot own the
    # terminal completely, which is necessary for an interactive session.
    result = subprocess.run(command)

    end = time.time()

    return SessionResult(
        command=command,
        exit_code=result.returncode,
        start_time=start,
        end_time=end,
        duration_seconds=end - start,
    )
