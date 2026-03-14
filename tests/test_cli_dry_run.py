import pathlib
import pytest
import yaml
from typer.testing import CliRunner
from bmad_orch.cli import app

runner = CliRunner()

@pytest.fixture
def config_file(tmp_path):
    d = {
        "providers": {
            1: {"name": "claude", "cli": "claude", "model": "opus-4"},
        },
        "cycles": {
            "story": {
                "steps": [
                    {"skill": "s1", "provider": 1, "type": "generative", "prompt": "p1"},
                ],
                "repeat": 1,
            }
        },
        "git": {"commit_at": "cycle", "push_at": "end"},
        "pauses": {"between_steps": 5.0, "between_cycles": 15.0, "between_workflows": 30.0},
        "error_handling": {"retry_transient": True, "max_retries": 3, "retry_delay": 10.0},
    }
    cfg_path = tmp_path / "bmad-orch.yaml"
    with open(cfg_path, "w") as f:
        yaml.dump(d, f)
    return cfg_path

def test_cli_dry_run_output(config_file):
    result = runner.invoke(app, ["start", "--config", str(config_file), "--dry-run"])
    assert result.exit_code == 0
    assert "DRY RUN: PLAYBOOK EXECUTION PLAN" in result.stdout
    assert "Providers Registry" in result.stdout
    assert "Execution Plan" in result.stdout
    assert "Dry run complete" in result.stdout

def test_cli_dry_run_precedence(config_file):
    # AC7: --dry-run and --no-preflight combination
    result = runner.invoke(app, ["start", "--config", str(config_file), "--dry-run", "--no-preflight"])
    assert result.exit_code == 0
    assert "DRY RUN: PLAYBOOK EXECUTION PLAN" in result.stdout

def test_cli_dry_run_invalid_provider_reference(tmp_path):
    # AC5: config error reports to stderr with code 2
    d = {
        "providers": {
            1: {"name": "claude", "cli": "claude", "model": "opus-4"},
        },
        "cycles": {
            "story": {
                "steps": [
                    {"skill": "s1", "provider": 99, "type": "generative", "prompt": "p1"},
                ],
                "repeat": 1,
            }
        },
        "git": {"commit_at": "cycle", "push_at": "end"},
        "pauses": {"between_steps": 5.0, "between_cycles": 15.0, "between_workflows": 30.0},
        "error_handling": {"retry_transient": True, "max_retries": 3, "retry_delay": 10.0},
    }
    cfg_path = tmp_path / "bad-orch.yaml"
    with open(cfg_path, "w") as f:
        yaml.dump(d, f)
    
    result = runner.invoke(app, ["start", "--config", str(cfg_path), "--dry-run"])
    assert result.exit_code == 2
    # AC5: Error goes to stderr via Console(stderr=True) in production.
    # Typer's CliRunner mixes stderr into output, so we verify content here.
    assert "nonexistent provider ID" in result.output
