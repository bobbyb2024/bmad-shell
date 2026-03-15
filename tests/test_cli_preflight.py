import json
from datetime import UTC
from unittest.mock import patch

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
    with cfg_path.open("w") as f:
        yaml.dump(d, f)
    return cfg_path

@patch("bmad_orch.cli.typer.getchar")
def test_cli_preflight_first_run_proceed(mock_getchar, config_file):
    # AC2: First run waits for confirmation
    mock_getchar.return_value = "\r"
    result = runner.invoke(app, ["start", "--config", str(config_file)])
    assert result.exit_code == 0
    assert "PRE-FLIGHT SUMMARY" in result.stdout
    assert "Confirmation:" in result.stdout

@patch("bmad_orch.cli.typer.getchar")
def test_cli_preflight_quit(mock_getchar, config_file):
    # AC2: Quit with exit code 130
    mock_getchar.return_value = "q"
    result = runner.invoke(app, ["start", "--config", str(config_file)])
    assert result.exit_code == 130

def test_cli_no_preflight(config_file):
    # AC6: --no-preflight skips summary
    result = runner.invoke(app, ["start", "--config", str(config_file), "--no-preflight"])
    assert result.exit_code == 0
    assert "PRE-FLIGHT SUMMARY" not in result.stdout

@patch("bmad_orch.cli.handle_auto_dismiss")
def test_cli_preflight_subsequent_run_auto_dismiss(mock_dismiss, config_file, tmp_path):
    # AC3: Subsequent run with same hash auto-dismisses
    state_path = config_file.parent / "bmad-orch-state.json"
    import hashlib
    from datetime import datetime
    with config_file.open("rb") as f:
        cfg_hash = hashlib.md5(f.read(), usedforsecurity=False).hexdigest()

    # Write a valid RunState with run_history so first_run=False
    state_data = {
        "run_id": "test-run-id",
        "schema_version": 1,
        "config_hash": cfg_hash,
        "run_history": [
            {
                "cycle_id": "story:1",
                "steps": [],
                "started_at": datetime.now(UTC).isoformat(),
                "finished_at": datetime.now(UTC).isoformat(),
                "outcome": "success",
            }
        ],
        "template_context": {},
    }
    with state_path.open("w") as f:
        json.dump(state_data, f)

    mock_dismiss.return_value = "proceed"
    result = runner.invoke(app, ["start", "--config", str(config_file)])
    assert result.exit_code == 0
    mock_dismiss.assert_called_once()

@patch("bmad_orch.cli.open_editor")
@patch("bmad_orch.cli.typer.getchar")
def test_cli_preflight_modify_flow(mock_getchar, mock_editor, config_file):
    # AC4: Modify flow re-validates and prompts again
    # Initial confirmation: 'm' (modify)
    # After editor: Enter (proceed)
    mock_getchar.side_effect = ["m", "\r"]
    mock_editor.return_value = True

    result = runner.invoke(app, ["start", "--config", str(config_file)])
    assert result.exit_code == 0
    mock_editor.assert_called_once()

@patch("bmad_orch.cli.open_editor")
@patch("bmad_orch.cli.typer.getchar")
def test_cli_preflight_modify_no_editor_found(mock_getchar, mock_editor, config_file):
    # AC4 / Task 4.8: No editor found → error message, return to summary confirmation
    # First getchar: 'm' (modify), editor fails, falls back to confirmation
    # Second getchar: Enter (proceed)
    mock_getchar.side_effect = ["m", "\r"]
    mock_editor.return_value = False  # Simulates no editor found

    result = runner.invoke(app, ["start", "--config", str(config_file)])
    assert result.exit_code == 0
    mock_editor.assert_called_once()
    # After editor failure, should return to confirmation (handle_confirmation called again)

@patch("bmad_orch.cli.typer.getchar")
def test_cli_preflight_config_changed(mock_getchar, config_file):
    # AC2: Config changed triggers mandatory confirmation
    state_path = config_file.parent / "bmad-orch-state.json"
    with state_path.open("w") as f:
        json.dump({"config_hash": "old-hash-is-different"}, f)
    
    mock_getchar.return_value = "\r"
    result = runner.invoke(app, ["start", "--config", str(config_file)])
    assert result.exit_code == 0
    assert "PRE-FLIGHT SUMMARY" in result.stdout
    assert "Confirmation:" in result.stdout

@patch("bmad_orch.cli.typer.getchar")
def test_cli_start_headless(mock_getchar, config_file):
    # AC6/Headless: --headless with --no-preflight skips pre-flight and runs
    mock_getchar.return_value = "\r"
    result = runner.invoke(app, ["start", "--config", str(config_file), "--headless", "--no-preflight"])
    assert result.exit_code == 0
    assert "PRE-FLIGHT SUMMARY" not in result.stdout
