import json
import pathlib
import hashlib
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from bmad_orch.cli import app
from bmad_orch.state.manager import StateManager
from bmad_orch.state.schema import CycleRecord, RunState, RunStatus, StepRecord
from bmad_orch.types import StepOutcome

runner = CliRunner()

def get_config_hash(path: pathlib.Path) -> str:
    """Calculate MD5 hash of the normalized config file."""
    with path.open("rb") as f:
        return hashlib.md5(f.read(), usedforsecurity=False).hexdigest()

@pytest.fixture
def mock_config(tmp_path):
    config_content = """
providers:
  1:
    name: "mock"
    cli: "mock"
    model: "m1"
cycles:
  c1:
    repeat: 1
    steps:
      - skill: "s1"
        provider: 1
        type: "validation"
        prompt: "do thing"
  c2:
    repeat: 1
    steps:
      - skill: "s2"
        provider: 1
        type: "validation"
        prompt: "do another thing"
git:
  enabled: false
pauses:
  between_steps: 0
  between_cycles: 0
  between_cycle_types: 0
  between_workflows: 0
error_handling:
  retry_transient: true
  max_retries: 3
  retry_delay: 1
"""
    config_path = tmp_path / "bmad-orch.yaml"
    config_path.write_text(config_content)
    return config_path

@pytest.fixture
def failed_state(tmp_path, mock_config):
    state = RunState(
        run_id="test-run",
        status=RunStatus.FAILED,
        config_hash=get_config_hash(mock_config),
        failure_point="cycle:c1:1/step:s1_0",
        failure_reason="Test failure",
        error_type="RuntimeError",
        halted_at=datetime.now(UTC),
        template_context={"key": "value"},
        run_history=[
            CycleRecord(
                cycle_id="c1:1",
                started_at=datetime.now(UTC),
                steps=[
                    StepRecord(
                        step_id="s1_0",
                        provider_name="mock",
                        outcome=StepOutcome.FAILURE,
                        timestamp=datetime.now(UTC)
                    )
                ],
                context_snapshot={"key": "original-value"}
            )
        ]
    )
    state_path = tmp_path / "bmad-orch-state.json"
    state_path.write_text(state.model_dump_json())
    return state_path

def test_resume_no_state(tmp_path):
    with patch("bmad_orch.state.manager.StateManager.DEFAULT_STATE_FILE", str(tmp_path / "nonexistent.json")):
        result = runner.invoke(app, ["resume"])
        assert result.exit_code == 1
        assert "No previous run found" in result.output

def test_resume_completed_state(tmp_path):
    state = RunState(run_id="test", status=RunStatus.COMPLETED)
    state_path = tmp_path / "bmad-orch-state.json"
    state_path.write_text(state.model_dump_json())
    
    with patch("bmad_orch.state.manager.StateManager.DEFAULT_STATE_FILE", str(state_path)):
        result = runner.invoke(app, ["resume"])
        assert result.exit_code == 0
        assert "completed successfully" in result.output

def test_resume_running_state(tmp_path):
    state = RunState(run_id="test", status=RunStatus.RUNNING)
    state_path = tmp_path / "bmad-orch-state.json"
    state_path.write_text(state.model_dump_json())
    
    with patch("bmad_orch.state.manager.StateManager.DEFAULT_STATE_FILE", str(state_path)):
        result = runner.invoke(app, ["resume"])
        assert result.exit_code == 1
        assert "run is currently in progress" in result.output
        
        # Test force unlock
        with patch("bmad_orch.engine.runner.Runner.run", new_callable=AsyncMock) as mock_run:
            # We also need a config file
            config_path = tmp_path / "bmad-orch.yaml"
            config_path.write_text("providers: {1: {name: m, cli: c, model: m}}\ncycles: {c: {steps: [{skill: s, provider: 1, type: validation, prompt: p}]}}\npauses:\n  between_steps: 0\n  between_cycles: 0\n  between_cycle_types: 0\n  between_workflows: 0\nerror_handling:\n  retry_transient: true\n  max_retries: 3\n  retry_delay: 1\ngit:\n  enabled: false")
            
            result = runner.invoke(app, ["resume", "--force-unlock", "--config", str(config_path), "--resume-option", "4"])
            if result.exit_code != 0:
                print(result.output)
            assert result.exit_code == 0
            assert "State reset" in result.output

def test_resume_option_1_rerun(failed_state, mock_config):
    with patch("bmad_orch.state.manager.StateManager.DEFAULT_STATE_FILE", str(failed_state)), \
         patch("bmad_orch.engine.runner.Runner.run", new_callable=AsyncMock) as mock_run:
        
        result = runner.invoke(app, ["resume", "--config", str(mock_config), "--resume-option", "1"])
        if result.exit_code != 0:
            print(result.output)
        assert result.exit_code == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert kwargs["start_cycle_id"] == "c1"
        assert kwargs["start_step_index"] == 0
        assert kwargs["template_context"] == {"key": "value"}

def test_resume_option_2_skip(failed_state, mock_config):
    with patch("bmad_orch.state.manager.StateManager.DEFAULT_STATE_FILE", str(failed_state)), \
         patch("bmad_orch.engine.runner.Runner.run", new_callable=AsyncMock) as mock_run:
        
        # We need to answer the skip confirmation if not forced
        result = runner.invoke(app, ["resume", "--config", str(mock_config), "--resume-option", "2"], input="y\n")
        if result.exit_code != 0:
            print(result.output)
        assert result.exit_code == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert kwargs["start_cycle_id"] == "c1"
        assert kwargs["start_step_index"] == 1

def test_resume_option_3_restart_cycle(failed_state, mock_config):
    with patch("bmad_orch.state.manager.StateManager.DEFAULT_STATE_FILE", str(failed_state)), \
         patch("bmad_orch.engine.runner.Runner.run", new_callable=AsyncMock) as mock_run:
        
        result = runner.invoke(app, ["resume", "--config", str(mock_config), "--resume-option", "3"])
        if result.exit_code != 0:
            print(result.output)
        assert result.exit_code == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert kwargs["start_cycle_id"] == "c1"
        assert kwargs["start_step_index"] == 0
        assert kwargs["template_context"] == {"key": "original-value"}

def test_resume_option_4_start_fresh(failed_state, mock_config):
    with patch("bmad_orch.state.manager.StateManager.DEFAULT_STATE_FILE", str(failed_state)), \
         patch("bmad_orch.engine.runner.Runner.run", new_callable=AsyncMock) as mock_run:
        
        result = runner.invoke(app, ["resume", "--config", str(mock_config), "--resume-option", "4"])
        if result.exit_code != 0:
            print(result.output)
        assert result.exit_code == 0
        assert not failed_state.exists() # It should be renamed
        # Check if backup exists (format: bmad-orch-state-[timestamp].json.bak)
        backups = list(failed_state.parent.glob("bmad-orch-state-*.json.bak"))
        assert len(backups) == 1
        
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert kwargs["start_cycle_id"] is None
        assert kwargs["start_step_index"] == 0
        assert kwargs["template_context"] == {}

def test_resume_config_mismatch(failed_state, mock_config):
    # Change config to cause mismatch
    mock_config.write_text("providers: {1: {name: m, cli: c, model: m}}\ncycles: {new_cycle: {steps: [{skill: s, provider: 1, type: validation, prompt: p}]}}\npauses:\n  between_steps: 0\n  between_cycles: 0\n  between_cycle_types: 0\n  between_workflows: 0\nerror_handling:\n  retry_transient: true\n  max_retries: 3\n  retry_delay: 1\ngit:\n  enabled: false")
    
    with patch("bmad_orch.state.manager.StateManager.DEFAULT_STATE_FILE", str(failed_state)):
        # Test abort without force
        result = runner.invoke(app, ["resume", "--config", str(mock_config), "--resume-option", "5"], input="n\n")
        assert "config has changed" in result.output
        
        # Test continue with force
        result = runner.invoke(app, ["resume", "--config", str(mock_config), "--resume-option", "5", "--force"])
        assert "Cancelled" in result.output # Selection 5 is cancel
