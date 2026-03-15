from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from bmad_orch.state.schema import CycleRecord, ErrorRecord, RunState, StepRecord
from bmad_orch.types import StepOutcome


def test_error_record_frozen():
    error = ErrorRecord(message="test", error_type="ValueError", traceback=None)
    with pytest.raises(ValidationError):
        error.message = "new"

def test_step_record_frozen():
    step = StepRecord(
        step_id="1",
        provider_name="test-provider",
        outcome=StepOutcome("success"),
        timestamp=datetime.now(UTC)
    )
    with pytest.raises(ValidationError):
        step.step_id = "2"

def test_cycle_record_frozen():
    cycle = CycleRecord(
        cycle_id="c1",
        steps=[],
        started_at=datetime.now(UTC),
        finished_at=None,
        outcome=None
    )
    with pytest.raises(ValidationError):
        cycle.cycle_id = "c2"

def test_run_state_frozen():
    state = RunState(
        run_id="r1",
        schema_version=1,
        run_history=[],
        config_hash="abc"
    )
    with pytest.raises(ValidationError):
        state.run_id = "r2"

def test_update_patterns():
    state = RunState(run_id="r1", config_hash="h1")
    # model_copy update
    state2 = state.model_copy(update={"config_hash": "h2"})
    assert state2.run_id == "r1"
    assert state2.config_hash == "h2"
    assert state.config_hash == "h1"

def test_run_state_serialization():
    now = datetime(2026, 3, 14, 12, 0, 0, tzinfo=UTC)
    step = StepRecord(
        step_id="s1",
        provider_name="p1",
        outcome=StepOutcome("success"),
        timestamp=now
    )
    cycle = CycleRecord(
        cycle_id="c1",
        steps=[step],
        started_at=now,
        finished_at=now,
        outcome=StepOutcome("success")
    )
    state = RunState(
        run_id="r1",
        schema_version=1,
        run_history=[cycle],
        config_hash="hash"
    )
    
    json_data = state.model_dump_json(indent=2)
    assert '"schema_version": 1' in json_data
    assert '"config_hash": "hash"' in json_data
    
    restored = RunState.model_validate_json(json_data)
    
    assert restored.run_id == "r1"
    assert restored.run_history[0].cycle_id == "c1"
    assert restored.run_history[0].steps[0].step_id == "s1"
    # Pydantic validates UTC datetime
    assert restored.run_history[0].steps[0].timestamp == now
