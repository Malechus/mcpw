"""
copilot_runner.py — Launches Copilot CLI as a subprocess.

When a real TTY is available the session is run through a pseudo-terminal
(PTY) so the interactive session feels completely normal to the user AND
we can capture the output (including Copilot's exit telemetry block) for
later parsing.  In non-TTY environments (CI, pipes) we fall back to a
plain subprocess.run call with no capture.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass, field


# ── PTY availability ──────────────────────────────────────────────────────────

try:
    import pty as _pty
    _HAS_PTY = True
except ImportError:  # Windows / unusual environments
    _HAS_PTY = False


# ── Session result ────────────────────────────────────────────────────────────

@dataclass
class SessionResult:
    """Everything the wrapper knows about a completed Copilot session."""

    command: list[str]                    # The exact command that was run
    exit_code: int                        # Copilot's exit code (0 = success)
    start_time: float                     # Unix timestamp when the session started
    end_time: float                       # Unix timestamp when the session ended
    duration_seconds: float              # Total wall-clock time
    captured_output: str = field(default="")  # Raw stdout captured via PTY


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

    When stdin is a real TTY, the session is run through a pseudo-terminal so
    the user gets a fully interactive experience AND stdout is captured (for
    parsing Copilot's exit telemetry).  In non-TTY environments (CI, pipes)
    we fall back to subprocess.run with no capture.
    """
    start = time.time()
    exit_code = 0
    captured_output = ""

    if _HAS_PTY and sys.stdin.isatty():
        buf = bytearray()

        def _master_read(fd: int) -> bytes:
            data = os.read(fd, 65536)
            buf.extend(data)
            return data

        try:
            pid_status = _pty.spawn(command, master_read=_master_read)
            # pty.spawn returns the raw waitpid status word.
            if os.WIFEXITED(pid_status):
                exit_code = os.WEXITSTATUS(pid_status)
            elif os.WIFSIGNALED(pid_status):
                exit_code = 128 + os.WTERMSIG(pid_status)
            else:
                exit_code = pid_status
            captured_output = buf.decode("utf-8", errors="replace")
        except Exception:
            # If PTY setup fails for any reason, fall back to plain subprocess.
            result = subprocess.run(command)
            exit_code = result.returncode
    else:
        result = subprocess.run(command)
        exit_code = result.returncode

    end = time.time()

    return SessionResult(
        command=command,
        exit_code=exit_code,
        start_time=start,
        end_time=end,
        duration_seconds=end - start,
        captured_output=captured_output,
    )
