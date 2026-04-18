"""
instructions.py — Telemetry instruction injection for Copilot sessions.

Copilot reads session instructions from .github/copilot-instructions.md
in the current repository.  This module prepends a telemetry block to that
file before the session starts and restores the original content when done.

The injected instructions ask Copilot to write a YAML summary of the session
(models used, agents used, token estimate, subagent interactions) to a
temporary file.  session_log.py reads that file after Copilot exits.
"""

from __future__ import annotations

import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path


# ── Constants ─────────────────────────────────────────────────────────────────

INSTRUCTIONS_FILE = Path(".github") / "copilot-instructions.md"

# The telemetry instruction block that is prepended to the instructions file.
# {summary_path} is replaced with the actual temp-file path at runtime.
TELEMETRY_TEMPLATE = """\
<!-- mcpw:telemetry-start -->
## Session telemetry (added automatically by mcpw — do not edit)

At the very end of this session, write a YAML block to the file at:
  {summary_path}

Use exactly this format (indentation matters):

```yaml
models_used:
  - <model name>
agents_used:
  - <agent or tool name>
token_estimate: <integer or null>
subagent_interactions:
  - from: <source>
    to: <target>
    summary: <one-line description>
```

Leave the file empty if there is nothing to report.
<!-- mcpw:telemetry-end -->

"""


# ── Context manager ───────────────────────────────────────────────────────────

@contextmanager
def injected(enabled: bool = True):
    """
    Context manager that prepends telemetry instructions before the session
    and restores the original file content afterwards.

    Usage:
        with instructions.injected(enabled=cfg.inject_instructions) as summary_path:
            runner.run_session(command)
        data = read_summary(summary_path)

    If *enabled* is False the context manager is a no-op and yields None.
    """
    if not enabled:
        yield None
        return

    # Create a temp file for Copilot to write its session summary into.
    summary_fd, summary_path = tempfile.mkstemp(suffix="_mcpw_summary.yaml")
    summary_path = Path(summary_path)

    instructions_file = INSTRUCTIONS_FILE
    original_content: str | None = None
    backup_path: Path | None = None

    try:
        if instructions_file.exists():
            original_content = instructions_file.read_text(encoding="utf-8")
            # Keep a backup in case something goes wrong.
            backup_path = instructions_file.with_suffix(".md.mcpw_backup")
            shutil.copy2(instructions_file, backup_path)

        # Prepend the telemetry block.
        instructions_file.parent.mkdir(parents=True, exist_ok=True)
        telemetry_block = TELEMETRY_TEMPLATE.format(summary_path=summary_path)
        new_content = telemetry_block + (original_content or "")
        instructions_file.write_text(new_content, encoding="utf-8")

        yield summary_path

    finally:
        # Always restore the original file, even if Copilot crashes.
        if original_content is not None:
            instructions_file.write_text(original_content, encoding="utf-8")
        elif instructions_file.exists():
            # We created the file from scratch; remove it.
            instructions_file.unlink()

        if backup_path and backup_path.exists():
            backup_path.unlink()


# ── Summary reader ────────────────────────────────────────────────────────────

def read_summary(summary_path: Path | None) -> dict:
    """
    Read the YAML summary file that Copilot wrote during the session.
    Returns an empty dict if the file is missing, empty, or unparseable.
    """
    if summary_path is None or not summary_path.exists():
        return {}

    content = summary_path.read_text(encoding="utf-8").strip()
    if not content:
        return {}

    # Use the stdlib to parse simple YAML-like content without adding a
    # third-party dependency.  For the structured summary format above this
    # is sufficient; swap in PyYAML later if the format grows more complex.
    try:
        import yaml  # type: ignore[import]
        return yaml.safe_load(content) or {}
    except Exception:
        # Return the raw text under a fallback key so it's not silently lost.
        return {"raw_summary": content}
