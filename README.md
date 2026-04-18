# Malechus' CoPilot Wrapper - mcpw
### Copilot CLI Wrapper

`mcpw` wraps the Copilot CLI to add structured session logging.  After each
session it writes three output files:

| File | Contents |
|---|---|
| `logs/<timestamp>_session.md` | Human-readable log: subagent interactions, models used, agents used |
| `logs/<timestamp>_session.json` | Structured JSON metadata for the full session |
| `logs/sessions.csv` | Appended row: token spend, duration, models, agents, exit code |

---

## Local setup

### 1. Prerequisites

- Python 3.11 or newer (`python3 --version` to check)
- Copilot CLI installed and accessible as `copilot` on your `PATH`

### 2. Clone and create a virtual environment

```bash
git clone <repo-url>
cd mcpw

# Create an isolated Python environment in .venv/
python3 -m venv .venv

# Activate it (you must do this in every new terminal session)
source .venv/bin/activate
```

> **What is a virtual environment?**  It's a self-contained folder where
> Python packages are installed without affecting the rest of your system.
> The `source` command "activates" it so that `python` and `pip` commands
> use the packages inside `.venv/` instead of the system ones.

### 3. Install the package in editable mode

```bash
pip install -e ".[dev]"
```

> `-e` means *editable*: changes you make to the source files in `src/`
> take effect immediately without reinstalling.  `[dev]` installs the
> extra packages needed for tests (currently just `pytest`).

### 4. Verify the installation

```bash
mcpw --version
```

---

## Running mcpw

```bash
# Start a Copilot CLI session with default settings
mcpw

# Specify a model
mcpw --model gpt-4o

# Save logs to a custom directory
mcpw --log-dir ~/copilot-logs

# Skip injecting telemetry instructions into the session
mcpw --no-inject

# Disable the granular tool allowances passed to Copilot
mcpw --no-tool-allowances

# Pass extra arguments directly to the Copilot CLI binary
mcpw -- --some-copilot-flag value
```

Everything after `--` is forwarded unchanged to the underlying `copilot`
command.

---

## Tool allowances

By default `mcpw` passes a curated set of `--allow-tool=` flags to the
Copilot CLI binary.  These map to the same tool set used by the `cpilot`
helper script and grant granular, least-privilege access (e.g.
`shell(ls:*)`, `shell(cat:*)`, `github.com`).

Use `--no-tool-allowances` to skip all `--allow-tool=` flags and let Copilot
apply its own defaults instead.

---

## Configuration

`mcpw` reads configuration from **two fixed locations**, layered in order:

| Priority | Path | Description |
|---|---|---|
| 1 (lowest) | `~/.config/mcpw/mcpw.toml` | Your personal user-wide config |
| 2 (highest) | `.github/mcpw.toml` | Per-project config (wins on conflict) |

Both files are optional — any absent file is silently skipped.

### Generating a config file

```bash
# Generate (or scaffold) the user-wide config
mcpw --gen-conf xdg

# Generate a project-level config in .github/
mcpw --gen-conf prj
```

`--gen-conf` writes a pre-commented template to the target path and exits.
It will not overwrite an existing file.  `--gen-conf prj` returns an error
if `.github/` does not exist in the current directory.

### Config keys

```toml
# The Copilot CLI binary to invoke.
copilot_cmd = "copilot"

# Where to write session logs.
log_dir = "logs"

# Set to false to skip telemetry instruction injection.
inject_instructions = true

# Force a specific model (comment out to let Copilot choose).
# model = "gpt-4o"

# Override the tool allowances list (TOML array of strings).
# tool_allowances = ["shell(ls:*)", "shell(cat:*)"]
```

CLI flags always override values from either config file.

---

## How telemetry capture works

When `inject_instructions` is enabled, `mcpw` temporarily prepends a block
to `.github/copilot-instructions.md` that asks Copilot to write a YAML
session summary (models used, agents used, token estimate, subagent
interactions) to a temp file.  The original instructions file is restored
the moment the session ends.

`mcpw` reads the temp file after Copilot exits and incorporates the data
into the markdown log, JSON file, and CSV row.

If Copilot does not write a summary (for example, because `--no-inject` was
used), the log files are still written but the telemetry fields are empty.

---

## Running tests

```bash
# Run all tests
pytest

# Run a single test file
pytest tests/test_cli.py

# Run a single test by name
pytest tests/test_cli.py::TestBuildParser::test_model_flag -v
```

---

## Project structure

```
src/
  mcpw/
    __init__.py         version string
    cli.py              argparse entrypoint — run as `mcpw`
    config.py           config file loading, generation, and precedence rules
    copilot_runner.py   subprocess launcher for the Copilot CLI
    instructions.py     telemetry instruction injection / cleanup
    session_log.py      writes the .md, .json, and .csv outputs
tests/
  test_cli.py           argument parsing tests
  test_config.py        config loading, precedence, and --gen-conf tests
  test_copilot_runner.py  command building and session result tests
  test_session_log.py  log file writing tests
logs/                   session log output (git-ignored)
pyproject.toml          project metadata, dependencies, entrypoint
```
