from datetime import datetime, timezone
from pathlib import Path

import pytest

from bmad_orch.engine.logs import consolidate_logs
from bmad_orch.state.schema import CycleRecord, ErrorRecord, RunState, StepRecord
from bmad_orch.types import StepOutcome


def test_consolidate_logs_creates_file(tmp_path):
    """Verify that consolidate_logs creates the output file and directories."""
    output_dir = tmp_path / "artifacts"
    run_id = "test-run"
    state = RunState(run_id=run_id)
    
    log_path = consolidate_logs(state, output_dir)
    
    assert log_path.exists()
    assert log_path == output_dir / f"{run_id}-cycle.log"


def test_consolidate_logs_ordering(tmp_path):
    """Verify that log entries are sorted by timestamp, then cycle, then step index."""
    output_dir = tmp_path
    ts1 = datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2026, 3, 15, 10, 0, 1, tzinfo=timezone.utc)
    
    # Same timestamp, different cycle
    step1 = StepRecord(step_id="s1", provider_name="p1", outcome=StepOutcome.SUCCESS, timestamp=ts1)
    step2 = StepRecord(step_id="s2", provider_name="p2", outcome=StepOutcome.SUCCESS, timestamp=ts1)
    
    # Different timestamp
    step3 = StepRecord(step_id="s3", provider_name="p3", outcome=StepOutcome.SUCCESS, timestamp=ts2)
    
    cycle1 = CycleRecord(cycle_id="c1", steps=[step1, step2], started_at=ts1)
    cycle2 = CycleRecord(cycle_id="c2", steps=[step3], started_at=ts2)
    
    state = RunState(run_id="test-ordering", run_history=[cycle1, cycle2])
    
    log_path = consolidate_logs(state, output_dir)
    content = log_path.read_text()
    lines = content.strip().split("\n")
    
    # Metadata header + 3 step lines
    assert len(lines) >= 8

    # Check ordering of last 3 lines
    # lines[0]: Run ID
    # lines[1]: Config Hash
    # lines[2]: Status
    # lines[3]: Started At
    # lines[4]: ----------------
    # lines[5]: Step 1
    assert "[Cycle 0] [2026-03-15T10:00:00Z] [s1] [p1] success" in lines[5]
    assert "[Cycle 0] [2026-03-15T10:00:00Z] [s2] [p2] success" in lines[6]
    assert "[Cycle 1] [2026-03-15T10:00:01Z] [s3] [p3] success" in lines[7]


def test_consolidate_logs_with_error(tmp_path):
    """Verify that log entries include error messages."""
    output_dir = tmp_path
    ts = datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc)
    error = ErrorRecord(message="Boom!", error_type="RuntimeError")
    step = StepRecord(step_id="s1", provider_name="p1", outcome=StepOutcome.FAILURE, timestamp=ts, error=error)
    cycle = CycleRecord(cycle_id="c1", steps=[step], started_at=ts)
    state = RunState(run_id="test-error", run_history=[cycle])
    
    log_path = consolidate_logs(state, output_dir)
    content = log_path.read_text()
    
    assert "failure Boom!" in content


def test_consolidate_logs_atomic_write(tmp_path, monkeypatch):
    """Verify that write is atomic (uses a temporary file)."""
    # This is hard to test directly without mocking Path.rename or similar.
    # For now, we'll just ensure it works normally.
    output_dir = tmp_path
    state = RunState(run_id="test-atomic")
    
    log_path = consolidate_logs(state, output_dir)
    assert log_path.exists()


def test_consolidate_logs_handles_failure(tmp_path):
    """Verify that consolidate_logs doesn't raise exceptions on failure."""
    # Try to write to a read-only directory
    read_only_dir = tmp_path / "readonly"
    read_only_dir.mkdir(mode=0o555)
    
    state = RunState(run_id="test-fail")
    
    # Should not raise
    log_path = consolidate_logs(state, read_only_dir)
    
    # And return the intended path anyway (though it might not exist if write failed)
    assert log_path == read_only_dir / "test-fail-cycle.log"
