import os
import json
import time
import uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pytest
from bmad_orch.state.manager import StateManager
from bmad_orch.state.schema import RunState, CycleRecord, StepRecord, ErrorRecord
from bmad_orch.types import StepOutcome
from bmad_orch.exceptions import StateError

@pytest.fixture
def state_file(tmp_path):
    return tmp_path / "bmad-orch-state.json"

def test_load_fresh(state_file):
    state = StateManager.load(state_file)
    assert isinstance(state, RunState)
    assert state.run_id is not None
    assert state.schema_version == 1
    assert state.run_history == []

def test_load_with_expected_hash(state_file):
    state = RunState(run_id="test-run", config_hash="old-hash")
    StateManager.save(state, state_file)
    
    # Should load fine but log warning if mismatch (warning is logged not raised)
    loaded = StateManager.load(state_file, expected_hash="new-hash")
    assert loaded.config_hash == "old-hash"

def test_save_atomic(state_file):
    state = RunState(run_id="test-run", config_hash="hash1")
    StateManager.save(state, state_file)
    
    assert state_file.exists()
    # Check it's pretty-printed JSON with UTF-8
    content = state_file.read_text(encoding="utf-8")
    assert '"run_id": "test-run"' in content
    
    loaded = StateManager.load(state_file)
    assert loaded.run_id == "test-run"
    assert loaded.config_hash == "hash1"

def test_load_corrupt_renames(state_file):
    state_file.write_text("not json")
    
    with pytest.raises(StateError):
        StateManager.load(state_file)
    
    # Check that it was renamed
    corrupt_files = list(state_file.parent.glob("bmad-orch-state.json.corrupt.*"))
    assert len(corrupt_files) == 1

def test_load_empty_file_raises_and_renames(state_file):
    state_file.touch()

    # AC8: Empty (0-byte) file is a validation failure — raises StateError
    with pytest.raises(StateError):
        StateManager.load(state_file)

    # Corrupt file should be renamed with timestamp suffix
    corrupt_files = list(state_file.parent.glob("bmad-orch-state.json.corrupt.*"))
    assert len(corrupt_files) == 1

def test_record_step(state_file):
    state = RunState(run_id="test-run")
    # Add a cycle that doesn't match to hit the coverage for the 'else' branch
    state = StateManager.start_cycle(state, "other-cycle")
    
    cycle_id = "cycle-1"
    now = datetime.now(timezone.utc)
    state = StateManager.start_cycle(state, cycle_id, started_at=now)
    
    error = ErrorRecord(message="fail", error_type="RuntimeError")
    step = StepRecord(
        step_id="step-1",
        provider_name="p1",
        outcome=StepOutcome("failure"),
        timestamp=now,
        error=error
    )
    
    new_state = StateManager.record_step(state, cycle_id, step)
    
    assert len(new_state.run_history) == 2
    # Verify both the matched and unmatched cycles are preserved correctly
    assert new_state.run_history[0].cycle_id == "other-cycle"
    assert new_state.run_history[1].cycle_id == "cycle-1"
    assert len(new_state.run_history[1].steps) == 1
    assert new_state.run_history[1].steps[0].step_id == "step-1"
    assert new_state.run_history[1].steps[0].error.message == "fail"

def test_start_finish_cycle(state_file):
    state = RunState(run_id="r1")
    now = datetime.now(timezone.utc)
    
    state = StateManager.start_cycle(state, "c1", started_at=now)
    assert len(state.run_history) == 1
    assert state.run_history[0].cycle_id == "c1"
    assert state.run_history[0].started_at == now
    
    later = now + timedelta(minutes=5)
    state = StateManager.finish_cycle(state, "c1", outcome=StepOutcome("success"), finished_at=later)
    assert state.run_history[0].outcome == StepOutcome("success")
    assert state.run_history[0].finished_at == later

def test_finish_cycle_missing(state_file):
    state = RunState(run_id="r1")
    with pytest.raises(StateError, match="Cycle missing not found"):
        StateManager.finish_cycle(state, "missing", outcome=StepOutcome("success"))

def test_record_step_missing_cycle(state_file):
    state = RunState(run_id="test-run")
    step = StepRecord(
        step_id="step-1",
        provider_name="p1",
        outcome=StepOutcome("success"),
        timestamp=datetime.now(timezone.utc)
    )
    with pytest.raises(StateError, match="Cycle missing not found"):
        StateManager.record_step(state, "missing", step)

def test_cleanup_stale_tmp(state_file):
    # Create a stale tmp file
    stale_tmp = state_file.parent / ".bmad-orch-state.json.old-uuid.tmp"
    stale_tmp.touch()
    
    # Backdate it more than 24 hours
    old_time = time.time() - (25 * 3600)
    os.utime(stale_tmp, (old_time, old_time))
    
    # Create a fresh tmp file
    fresh_tmp = state_file.parent / ".bmad-orch-state.json.new-uuid.tmp"
    fresh_tmp.touch()
    
    StateManager.load(state_file)
    
    assert not stale_tmp.exists()
    assert fresh_tmp.exists()

def test_save_error_handling(state_file):
    # Make directory read-only to trigger save error
    os.chmod(state_file.parent, 0o555)
    try:
        state = RunState(run_id="test")
        with pytest.raises(StateError, match="Failed to save state"):
            StateManager.save(state, state_file)
    finally:
        os.chmod(state_file.parent, 0o755)


def test_load_schema_version_mismatch(state_file):
    """AC8: Schema version mismatch should raise StateError."""
    # Write a state file with an unsupported schema version
    state_data = RunState(run_id="test-run", schema_version=1).model_dump_json(indent=2)
    # Manually patch the version in JSON
    bad_data = state_data.replace('"schema_version": 1', '"schema_version": 99')
    state_file.write_text(bad_data, encoding="utf-8")

    with pytest.raises(StateError, match="Schema version mismatch"):
        StateManager.load(state_file)

    # Corrupt file should be preserved
    corrupt_files = list(state_file.parent.glob("bmad-orch-state.json.corrupt.*"))
    assert len(corrupt_files) == 1


def test_load_corrupt_rename_failure_returns_fresh(state_file, monkeypatch):
    """AC8: If renaming corrupt file fails, log error and return fresh state."""
    state_file.write_text("not json", encoding="utf-8")

    # Make os.replace fail for the corrupt rename
    original_replace = os.replace
    def failing_replace(src, dst):
        if ".corrupt." in str(dst):
            raise OSError("Simulated rename failure")
        return original_replace(src, dst)

    monkeypatch.setattr(os, "replace", failing_replace)

    # Should return fresh state (not raise) when rename fails
    state = StateManager.load(state_file)
    assert isinstance(state, RunState)
    assert state.run_id is not None
    assert state.run_history == []


def test_save_creates_parent_directories(tmp_path):
    """Verify save creates parent directories if they don't exist."""
    nested_path = tmp_path / "a" / "b" / "state.json"
    state = RunState(run_id="test-run")
    StateManager.save(state, nested_path)

    assert nested_path.exists()
    loaded = StateManager.load(nested_path)
    assert loaded.run_id == "test-run"
