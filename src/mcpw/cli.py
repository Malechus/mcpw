"""
cli.py — Command-line entrypoint for mcpw.

Usage:
    mcpw [options] [-- copilot_args...]

Options are wrapper-specific.  Anything after -- is forwarded directly
to the Copilot CLI binary.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mcpw import __version__
from mcpw import config as cfg_module
from mcpw import copilot_runner as runner
from mcpw import instructions
from mcpw import session_log


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcpw",
        description=(
            "A wrapper for Copilot CLI that logs session metadata, "
            "model usage, token estimates, and subagent interactions."
        ),
        epilog=(
            "Any arguments after -- are forwarded directly to the Copilot CLI.\n"
            "Example: mcpw --log-dir ./my-logs -- --model gpt-4o"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "--gen-conf",
        choices=["xdg", "prj"],
        metavar="{xdg|prj}",
        default=None,
        help=(
            "Generate a starter config file and exit. "
            "'xdg' writes to ~/.config/mcpw/mcpw.toml; "
            "'prj' writes to .github/mcpw.toml in the current repository."
        ),
    )

    parser.add_argument(
        "--log-dir",
        metavar="DIR",
        type=Path,
        default=None,
        help="Directory to write session logs (overrides config file).",
    )

    parser.add_argument(
        "--model",
        metavar="MODEL",
        default=None,
        help="Model name to forward to Copilot CLI (overrides config file).",
    )

    parser.add_argument(
        "--no-inject",
        action="store_true",
        default=False,
        help="Skip injecting telemetry instructions into the Copilot session.",
    )

    parser.add_argument(
        "--no-tool-allowances",
        action="store_true",
        default=False,
        help=(
            "Disable granular tool allowances. By default mcpw passes a "
            "curated --allow-tool= list to Copilot CLI. Use this flag to "
            "let Copilot decide which tools are available."
        ),
    )

    # Everything after -- lands here as a plain list of strings.
    parser.add_argument(
        "copilot_args",
        nargs=argparse.REMAINDER,
        help="Extra arguments forwarded to Copilot CLI.",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # ── Config generation (early exit, no session started) ────────────────────
    if args.gen_conf:
        cfg_module.generate(args.gen_conf)
        sys.exit(0)

    # Strip a leading '--' separator if the user typed it explicitly.
    copilot_args: list[str] = args.copilot_args
    if copilot_args and copilot_args[0] == "--":
        copilot_args = copilot_args[1:]

    # ── Load config, then apply CLI overrides ─────────────────────────────────
    cfg = cfg_module.load()

    if args.log_dir is not None:
        cfg.log_dir = args.log_dir
    if args.model is not None:
        cfg.model = args.model
    if args.no_inject:
        cfg.inject_instructions = False
    if args.no_tool_allowances:
        cfg.tool_allowances = []

    # If a model was specified, append it to the Copilot args.
    if cfg.model:
        copilot_args = ["--model", cfg.model, *copilot_args]

    # ── Build the Copilot command ─────────────────────────────────────────────
    command = runner.build_command(cfg.copilot_cmd, copilot_args, cfg.tool_allowances)

    # ── Run the session with optional instruction injection ───────────────────
    cfg.log_dir.mkdir(parents=True, exist_ok=True)

    with instructions.injected(enabled=cfg.inject_instructions) as summary_path:
        session = runner.run_session(command)

    # ── Read any telemetry Copilot wrote during the session ───────────────────
    summary = instructions.read_summary(summary_path)

    # ── Write the three log outputs ───────────────────────────────────────────
    session_log.write_all(
        session=session,
        summary=summary,
        log_dir=cfg.log_dir,
        model=cfg.model,
    )

    # Exit with the same code Copilot used so shell scripts behave correctly.
    sys.exit(session.exit_code)


if __name__ == "__main__":
    main()
