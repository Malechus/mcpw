"""
config.py — User configuration loading.

Settings are resolved in this order (later values win):
  1. Built-in defaults
  2. Config file  (~/.config/mcpw/config.toml  or  ./mcpw.toml)
  3. Command-line arguments (applied in cli.py)
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


# ── Defaults ─────────────────────────────────────────────────────────────────

# Granular tool allowances forwarded to Copilot CLI via --allow-tool= flags.
# Each entry becomes one --allow-tool=<value> argument on the command line.
# Override the full list in mcpw.toml under the key `tool_allowances`.
DEFAULT_TOOL_ALLOWANCES: list[str] = [
    "shell(ls:*)",
    "shell(cat:*)",
    "shell(echo:*)",
    "shell(git fetch)",
    "shell(git checkout)",
    "shell(grep:*)",
    "shell(find:*)",
    "shell(tail:*)",
    "shell(head:*)",
    "url(https://docs.github.com)",
]

DEFAULTS: dict = {
    # The Copilot CLI binary to invoke.  If Copilot is accessible via a
    # different path or command on your system, override this in mcpw.toml.
    "copilot_cmd": "copilot",
    # Directory where session logs are written.
    "log_dir": "logs",
    # Whether to prepend telemetry instructions before each session.
    "inject_instructions": True,
    # Model name passed to Copilot (None = let Copilot choose its default).
    "model": None,
}


# ── Config dataclass ──────────────────────────────────────────────────────────

@dataclass
class Config:
    copilot_cmd: str = DEFAULTS["copilot_cmd"]
    log_dir: Path = field(default_factory=lambda: Path(DEFAULTS["log_dir"]))
    inject_instructions: bool = DEFAULTS["inject_instructions"]
    model: str | None = DEFAULTS["model"]
    # List of tool allowance strings passed to Copilot as --allow-tool= flags.
    # Set to an empty list (or use --no-tool-allowances) to disable all limits.
    tool_allowances: list[str] = field(
        default_factory=lambda: list(DEFAULT_TOOL_ALLOWANCES)
    )


# ── Loading logic ─────────────────────────────────────────────────────────────

def _candidate_paths(explicit: Path | None) -> list[Path]:
    """Return config file paths to try, in order of preference."""
    if explicit:
        return [explicit]
    return [
        Path("mcpw.toml"),
        Path.home() / ".config" / "mcpw" / "config.toml",
    ]


def load(config_file: Path | None = None) -> Config:
    """
    Load configuration from the first config file found.
    Returns a Config with defaults if no file is found.
    """
    cfg = Config()

    for path in _candidate_paths(config_file):
        if path.exists():
            with path.open("rb") as fh:
                data = tomllib.load(fh)
            cfg.copilot_cmd = data.get("copilot_cmd", cfg.copilot_cmd)
            cfg.log_dir = Path(data.get("log_dir", cfg.log_dir))
            cfg.inject_instructions = data.get(
                "inject_instructions", cfg.inject_instructions
            )
            cfg.model = data.get("model", cfg.model)
            if "tool_allowances" in data:
                cfg.tool_allowances = list(data["tool_allowances"])
            break  # stop at first file found

    return cfg
