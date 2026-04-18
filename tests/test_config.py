"""
Tests for config.py — loading precedence, file application, and generation.
"""

import pytest

from mcpw import config as cfg_module
from mcpw.config import (
    CONFIG_TEMPLATE,
    DEFAULT_TOOL_ALLOWANCES,
    Config,
    _apply_file,
    generate,
    load,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _write_toml(path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


# ── _apply_file ───────────────────────────────────────────────────────────────

class TestApplyFile:
    def test_no_op_when_file_missing(self, tmp_path):
        cfg = Config()
        _apply_file(cfg, tmp_path / "nonexistent.toml")
        assert cfg.copilot_cmd == "copilot"  # unchanged default

    def test_applies_copilot_cmd(self, tmp_path):
        p = tmp_path / "mcpw.toml"
        _write_toml(p, 'copilot_cmd = "my-copilot"\n')
        cfg = Config()
        _apply_file(cfg, p)
        assert cfg.copilot_cmd == "my-copilot"

    def test_applies_log_dir(self, tmp_path):
        p = tmp_path / "mcpw.toml"
        _write_toml(p, 'log_dir = "/var/log/mcpw"\n')
        cfg = Config()
        _apply_file(cfg, p)
        assert str(cfg.log_dir) == "/var/log/mcpw"

    def test_applies_inject_instructions(self, tmp_path):
        p = tmp_path / "mcpw.toml"
        _write_toml(p, "inject_instructions = false\n")
        cfg = Config()
        _apply_file(cfg, p)
        assert cfg.inject_instructions is False

    def test_applies_model(self, tmp_path):
        p = tmp_path / "mcpw.toml"
        _write_toml(p, 'model = "gpt-4o"\n')
        cfg = Config()
        _apply_file(cfg, p)
        assert cfg.model == "gpt-4o"

    def test_applies_tool_allowances(self, tmp_path):
        p = tmp_path / "mcpw.toml"
        _write_toml(p, 'tool_allowances = ["shell(ls:*)"]\n')
        cfg = Config()
        _apply_file(cfg, p)
        assert cfg.tool_allowances == ["shell(ls:*)"]

    def test_does_not_touch_absent_keys(self, tmp_path):
        p = tmp_path / "mcpw.toml"
        _write_toml(p, 'model = "gpt-4o"\n')
        cfg = Config()
        original_cmd = cfg.copilot_cmd
        _apply_file(cfg, p)
        assert cfg.copilot_cmd == original_cmd  # untouched


# ── load() — defaults and precedence ─────────────────────────────────────────

class TestLoad:
    def test_returns_defaults_when_no_files_exist(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cfg_module, "USER_CONFIG_PATH", tmp_path / "user.toml")
        monkeypatch.setattr(cfg_module, "PROJECT_CONFIG_PATH", tmp_path / "prj.toml")
        cfg = load()
        assert cfg.copilot_cmd == "copilot"
        assert cfg.inject_instructions is True
        assert cfg.tool_allowances == DEFAULT_TOOL_ALLOWANCES

    def test_user_config_applied(self, tmp_path, monkeypatch):
        user = tmp_path / "user.toml"
        _write_toml(user, 'model = "claude-3"\n')
        monkeypatch.setattr(cfg_module, "USER_CONFIG_PATH", user)
        monkeypatch.setattr(cfg_module, "PROJECT_CONFIG_PATH", tmp_path / "prj.toml")
        cfg = load()
        assert cfg.model == "claude-3"

    def test_project_config_overrides_user(self, tmp_path, monkeypatch):
        user = tmp_path / "user.toml"
        prj = tmp_path / "prj.toml"
        _write_toml(user, 'model = "claude-3"\n')
        _write_toml(prj, 'model = "gpt-4o"\n')
        monkeypatch.setattr(cfg_module, "USER_CONFIG_PATH", user)
        monkeypatch.setattr(cfg_module, "PROJECT_CONFIG_PATH", prj)
        cfg = load()
        assert cfg.model == "gpt-4o"

    def test_user_only_settings_survive_project_override(self, tmp_path, monkeypatch):
        user = tmp_path / "user.toml"
        prj = tmp_path / "prj.toml"
        _write_toml(user, 'log_dir = "/user/logs"\n')
        _write_toml(prj, 'model = "gpt-4o"\n')  # does not set log_dir
        monkeypatch.setattr(cfg_module, "USER_CONFIG_PATH", user)
        monkeypatch.setattr(cfg_module, "PROJECT_CONFIG_PATH", prj)
        cfg = load()
        assert str(cfg.log_dir) == "/user/logs"
        assert cfg.model == "gpt-4o"

    def test_both_configs_absent_gives_defaults(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cfg_module, "USER_CONFIG_PATH", tmp_path / "u.toml")
        monkeypatch.setattr(cfg_module, "PROJECT_CONFIG_PATH", tmp_path / "p.toml")
        cfg = load()
        assert cfg.model is None


# ── generate() ───────────────────────────────────────────────────────────────

class TestGenerate:
    def test_xdg_creates_file(self, tmp_path, monkeypatch):
        dest = tmp_path / "mcpw.toml"
        monkeypatch.setattr(cfg_module, "USER_CONFIG_PATH", dest)
        generate("xdg")
        assert dest.exists()

    def test_xdg_file_contains_template(self, tmp_path, monkeypatch):
        dest = tmp_path / "mcpw.toml"
        monkeypatch.setattr(cfg_module, "USER_CONFIG_PATH", dest)
        generate("xdg")
        assert dest.read_text() == CONFIG_TEMPLATE

    def test_xdg_creates_parent_directories(self, tmp_path, monkeypatch):
        dest = tmp_path / "deep" / "nested" / "mcpw.toml"
        monkeypatch.setattr(cfg_module, "USER_CONFIG_PATH", dest)
        generate("xdg")
        assert dest.exists()

    def test_xdg_errors_if_file_already_exists(self, tmp_path, monkeypatch):
        dest = tmp_path / "mcpw.toml"
        dest.write_text("existing", encoding="utf-8")
        monkeypatch.setattr(cfg_module, "USER_CONFIG_PATH", dest)
        with pytest.raises(SystemExit) as exc:
            generate("xdg")
        assert exc.value.code == 1

    def test_prj_creates_file_when_github_dir_exists(self, tmp_path, monkeypatch):
        github = tmp_path / ".github"
        github.mkdir()
        dest = github / "mcpw.toml"
        monkeypatch.setattr(cfg_module, "PROJECT_CONFIG_PATH", dest)
        generate("prj")
        assert dest.exists()

    def test_prj_file_contains_template(self, tmp_path, monkeypatch):
        github = tmp_path / ".github"
        github.mkdir()
        dest = github / "mcpw.toml"
        monkeypatch.setattr(cfg_module, "PROJECT_CONFIG_PATH", dest)
        generate("prj")
        assert dest.read_text() == CONFIG_TEMPLATE

    def test_prj_errors_if_github_dir_missing(self, tmp_path, monkeypatch):
        dest = tmp_path / ".github" / "mcpw.toml"  # parent does not exist
        monkeypatch.setattr(cfg_module, "PROJECT_CONFIG_PATH", dest)
        with pytest.raises(SystemExit) as exc:
            generate("prj")
        assert exc.value.code == 1

    def test_prj_errors_if_file_already_exists(self, tmp_path, monkeypatch):
        github = tmp_path / ".github"
        github.mkdir()
        dest = github / "mcpw.toml"
        dest.write_text("existing", encoding="utf-8")
        monkeypatch.setattr(cfg_module, "PROJECT_CONFIG_PATH", dest)
        with pytest.raises(SystemExit) as exc:
            generate("prj")
        assert exc.value.code == 1

    def test_template_has_all_options_commented(self):
        for key in ("copilot_cmd", "log_dir", "inject_instructions", "model", "tool_allowances"):
            assert f"# {key}" in CONFIG_TEMPLATE
