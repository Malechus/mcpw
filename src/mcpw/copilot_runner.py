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

def build_command(copilot_cmd: str, extra_args: list[str]) -> list[str]:
    """
    Combine the base Copilot command with any extra arguments.

    Example:
        build_command("gh copilot", ["--model", "gpt-4o"])
        # → ["gh", "copilot", "--model", "gpt-4o"]
    """
    return [*copilot_cmd.split(), *extra_args]


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
