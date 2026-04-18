"""
config.py — User configuration loading and generation.

Two config file sources are supported (later values win):
  1. ~/.config/mcpw/mcpw.toml   — user-level config
  2. ./.github/mcpw.toml        — project-level config (takes precedence)

Both files are optional. Command-line flags always take final precedence
and are applied in cli.py after load() returns.
"""

from __future__ import annotations

import sys
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
    # The Copilot CLI binary to invoke.  Override in mcpw.toml if needed.
    "copilot_cmd": "copilot",
    # Directory where session logs are written.
    "log_dir": "logs",
    # Whether to prepend telemetry instructions before each session.
    "inject_instructions": True,
    # Model name passed to Copilot (None = let Copilot choose its default).
    "model": None,
}

# ── Known config file locations ───────────────────────────────────────────────

USER_CONFIG_PATH = Path.home() / ".config" / "mcpw" / "mcpw.toml"
PROJECT_CONFIG_PATH = Path(".github") / "mcpw.toml"


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

def _apply_file(cfg: Config, path: Path) -> None:
    """Overlay settings from a TOML file onto cfg. No-ops if the file is absent."""
    if not path.exists():
        return
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    if "copilot_cmd" in data:
        cfg.copilot_cmd = data["copilot_cmd"]
    if "log_dir" in data:
        cfg.log_dir = Path(data["log_dir"])
    if "inject_instructions" in data:
        cfg.inject_instructions = data["inject_instructions"]
    if "model" in data:
        cfg.model = data["model"]
    if "tool_allowances" in data:
        cfg.tool_allowances = list(data["tool_allowances"])


def load() -> Config:
    """
    Build a Config by layering both config sources in precedence order:
      1. Built-in defaults
      2. User config   (~/.config/mcpw/mcpw.toml)
      3. Project config (.github/mcpw.toml)   ← wins over user config
    """
    cfg = Config()
    _apply_file(cfg, USER_CONFIG_PATH)
    _apply_file(cfg, PROJECT_CONFIG_PATH)
    return cfg


# ── Config file template ──────────────────────────────────────────────────────

CONFIG_TEMPLATE = """\
# mcpw configuration file
#
# Project config (.github/mcpw.toml) takes precedence over user config
# (~/.config/mcpw/mcpw.toml). Uncomment any option below to override its default.

# The Copilot CLI binary to invoke.
# copilot_cmd = "copilot"

# Directory where session logs are written (relative to cwd, or absolute).
# log_dir = "logs"

# Set to false to skip injecting telemetry instructions each session.
# inject_instructions = true

# Force a specific model. Leave commented to use Copilot's default.
# model = "gpt-4o"

# Granular tool allowances passed to Copilot as --allow-tool= flags.
# Uncomment the entire block to restrict which tools Copilot may use.
# Set to [] to skip all allowances and let Copilot decide.
# tool_allowances = [
#   "shell(ls:*)",
#   "shell(cat:*)",
#   "shell(echo:*)",
#   "shell(git fetch)",
#   "shell(git checkout)",
#   "shell(grep:*)",
#   "shell(find:*)",
#   "shell(tail:*)",
#   "shell(head:*)",
#   "url(https://docs.github.com)",
# ]
"""


# ── Config generation ─────────────────────────────────────────────────────────

def generate(target: str) -> None:
    """
    Write a starter config file at the appropriate location.

    target "xdg" → ~/.config/mcpw/mcpw.toml
    target "prj" → ./.github/mcpw.toml  (errors if .github/ does not exist)

    Prints the created path on success. Prints an error and raises
    SystemExit(1) if the directory is missing or a file already exists.
    """
    if target == "xdg":
        dest_dir = USER_CONFIG_PATH.parent
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = USER_CONFIG_PATH
    elif target == "prj":
        github_dir = PROJECT_CONFIG_PATH.parent
        if not github_dir.is_dir():
            print(
                f"error: {github_dir}/ not found in the current directory.\n"
                "Run mcpw from the root of a repository that has a .github/ folder.",
                file=sys.stderr,
            )
            raise SystemExit(1)
        dest = PROJECT_CONFIG_PATH
    else:
        raise ValueError(f"Unknown config target: {target!r}")

    if dest.exists():
        print(f"error: config file already exists at {dest}", file=sys.stderr)
        raise SystemExit(1)

    dest.write_text(CONFIG_TEMPLATE, encoding="utf-8")
    print(f"Created {dest}")

