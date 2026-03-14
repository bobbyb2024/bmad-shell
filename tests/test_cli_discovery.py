import yaml
from typer.testing import CliRunner

from bmad_orch.cli import app

runner = CliRunner()


def test_cli_validate_no_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 2
    assert "No config found" in result.stdout


def test_cli_validate_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "bmad-orch.yaml"
    valid_data = {
        "providers": {1: {"name": "p1", "cli": "c1", "model": "m1"}},
        "cycles": {"c1": {"steps": [{"skill": "s1", "provider": 1, "type": "generative", "prompt": "p1"}]}},
        "git": {"commit_at": "cycle", "push_at": "end"},
        "pauses": {"between_steps": 1, "between_cycles": 1, "between_workflows": 1},
        "error_handling": {"retry_transient": True, "max_retries": 3, "retry_delay": 10},
    }
    config_file.write_text(yaml.dump(valid_data))
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0
    assert "Configuration is valid" in result.stdout
    assert "p1" in result.stdout
    assert "m1" in result.stdout


def test_cli_validate_explicit(tmp_path):
    config_file = tmp_path / "my-config.yaml"
    valid_data = {
        "providers": {1: {"name": "p1", "cli": "c1", "model": "m1"}},
        "cycles": {"c1": {"steps": [{"skill": "s1", "provider": 1, "type": "generative", "prompt": "p1"}]}},
        "git": {"commit_at": "cycle", "push_at": "end"},
        "pauses": {"between_steps": 1, "between_cycles": 1, "between_workflows": 1},
        "error_handling": {"retry_transient": True, "max_retries": 3, "retry_delay": 10},
    }
    config_file.write_text(yaml.dump(valid_data))
    result = runner.invoke(app, ["validate", "--config", str(config_file)])
    assert result.exit_code == 0
    assert "Configuration is valid" in result.stdout


def test_cli_validate_invalid_yaml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "bmad-orch.yaml"
    config_file.write_text("invalid: [yaml: structure")
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 2
    assert "YAML syntax error" in result.stdout
