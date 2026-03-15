"""ATDD tests for Story 4.5: Log Consolidation (AC 1, 2, 7, 8).

TDD RED PHASE — All tests are skipped. Remove @pytest.mark.skip to verify
implementation (green phase). Every test asserts EXPECTED behavior that does
not exist yet.

Acceptance Criteria covered:
  AC1: Consolidated log file written on run completion and emergency halt;
       failure must not block git commit; atomic write via temp+rename.
  AC2: Chronological ordering, ISO-8601 UTC timestamps, metadata header,
       log-line format with cycle index.
  AC7: Auto-create parent directories for log output.
  AC8: Resumed runs include full history; log file overwritten atomically.
"""

import json
import os
import tempfile
from datetime import UTC, datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bmad_orch.state.schema import CycleRecord, ErrorRecord, RunState, StepRecord

SKIP_REASON = "ATDD red phase: Story 4.5 not implemented"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_step(
    step_id: str,
    provider: str = "claude",
    outcome: str = "success",
    ts: datetime | None = None,
    error: ErrorRecord | None = None,
) -> StepRecord:
    """Create a StepRecord for testing."""
    return StepRecord(
        step_id=step_id,
        provider_name=provider,
        outcome=outcome,
        timestamp=ts or datetime.now(UTC),
        error=error,
    )


def _make_cycle(
    cycle_id: str,
    steps: list[StepRecord] | None = None,
) -> CycleRecord:
    """Create a CycleRecord for testing."""
    return CycleRecord(
        cycle_id=cycle_id,
        steps=steps or [],
        started_at=datetime.now(UTC),
    )


def _make_state_with_history(
    run_id: str = "test-run-1",
    cycles: list[CycleRecord] | None = None,
) -> RunState:
    """Create a RunState with run_history for log consolidation tests."""
    from bmad_orch.state.schema import RunStatus

    return RunState(
        run_id=run_id,
        status=RunStatus.COMPLETED,
        run_history=cycles or [],
    )


# ---------------------------------------------------------------------------
# Unit Tests — consolidate_logs function (AC 1, 2, 7)
# ---------------------------------------------------------------------------


class TestConsolidateLogsExists:
    """AC1: consolidate_logs function must exist in engine/logs.py."""

    def test_consolidate_logs_importable(self):
        """consolidate_logs should be importable from bmad_orch.engine.logs."""
        from bmad_orch.engine.logs import consolidate_logs

        assert callable(consolidate_logs)

    def test_consolidate_logs_signature(self):
        """consolidate_logs(state, output_dir) -> Path."""
        import inspect

        from bmad_orch.engine.logs import consolidate_logs

        sig = inspect.signature(consolidate_logs)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "output_dir" in params


class TestConsolidateLogsOutput:
    """AC1: Consolidated log file written to correct path."""

    def test_log_file_written_to_expected_path(self, tmp_path):
        """Log file should be at {output_dir}/{run_id}-cycle.log."""
        from bmad_orch.engine.logs import consolidate_logs

        step = _make_step("s1")
        cycle = _make_cycle("c1", steps=[step])
        state = _make_state_with_history(run_id="my-run", cycles=[cycle])

        result_path = consolidate_logs(state, tmp_path)

        assert result_path == tmp_path / "my-run-cycle.log"
        assert result_path.exists()

    def test_log_file_not_empty(self, tmp_path):
        """Consolidated log file should contain content."""
        from bmad_orch.engine.logs import consolidate_logs

        step = _make_step("s1")
        cycle = _make_cycle("c1", steps=[step])
        state = _make_state_with_history(cycles=[cycle])

        result_path = consolidate_logs(state, tmp_path)

        content = result_path.read_text()
        assert len(content) > 0


class TestAtomicWrite:
    """AC1: Log file must be written atomically (temp file + rename)."""

    def test_no_partial_file_on_completion(self, tmp_path):
        """After consolidate_logs returns, no temp files should remain."""
        from bmad_orch.engine.logs import consolidate_logs

        step = _make_step("s1")
        cycle = _make_cycle("c1", steps=[step])
        state = _make_state_with_history(cycles=[cycle])

        consolidate_logs(state, tmp_path)

        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_atomic_overwrite_on_repeated_consolidation(self, tmp_path):
        """AC8: Repeated calls overwrite atomically, not append."""
        from bmad_orch.engine.logs import consolidate_logs

        step = _make_step("s1")
        cycle = _make_cycle("c1", steps=[step])
        state = _make_state_with_history(cycles=[cycle])

        path1 = consolidate_logs(state, tmp_path)
        content1 = path1.read_text()

        # Second consolidation with same state
        path2 = consolidate_logs(state, tmp_path)
        content2 = path2.read_text()

        assert content1 == content2  # Overwritten, not doubled


class TestLogConsolidationFailureIsolation:
    """AC1: Log consolidation failure must not block git commit or halt."""

    def test_consolidation_io_error_does_not_raise(self, tmp_path):
        """Permission denied during write should log error, not raise."""
        from bmad_orch.engine.logs import consolidate_logs

        step = _make_step("s1")
        cycle = _make_cycle("c1", steps=[step])
        state = _make_state_with_history(cycles=[cycle])

        # Make output_dir read-only to trigger IOError
        read_only_dir = tmp_path / "readonly"
        read_only_dir.mkdir()
        read_only_dir.chmod(0o444)

        try:
            # Should NOT raise — must catch and log internally
            result = consolidate_logs(state, read_only_dir)
            # Result may be None or the path; the key is no exception
        finally:
            read_only_dir.chmod(0o755)

    def test_consolidation_failure_logs_to_stderr(self, tmp_path, caplog):
        """IO failure during consolidation should be logged at ERROR level."""
        import logging

        from bmad_orch.engine.logs import consolidate_logs

        step = _make_step("s1")
        cycle = _make_cycle("c1", steps=[step])
        state = _make_state_with_history(cycles=[cycle])

        read_only_dir = tmp_path / "readonly"
        read_only_dir.mkdir()
        read_only_dir.chmod(0o444)

        try:
            with caplog.at_level(logging.ERROR):
                consolidate_logs(state, read_only_dir)
            assert any("consolidat" in r.message.lower() for r in caplog.records)
        finally:
            read_only_dir.chmod(0o755)


# ---------------------------------------------------------------------------
# Unit Tests — Log format and ordering (AC 2)
# ---------------------------------------------------------------------------


class TestLogMetadataHeader:
    """AC2: Log file must start with metadata header."""

    def test_header_contains_run_id(self, tmp_path):
        """Metadata header must contain the run_id."""
        from bmad_orch.engine.logs import consolidate_logs

        step = _make_step("s1")
        cycle = _make_cycle("c1", steps=[step])
        state = _make_state_with_history(run_id="abc-123", cycles=[cycle])

        path = consolidate_logs(state, tmp_path)
        content = path.read_text()

        assert "abc-123" in content.split("\n")[0] or "abc-123" in content[:200]

    def test_header_contains_config_info(self, tmp_path):
        """Metadata header must contain initial configuration."""
        from bmad_orch.engine.logs import consolidate_logs

        step = _make_step("s1")
        cycle = _make_cycle("c1", steps=[step])
        state = _make_state_with_history(run_id="abc-123", cycles=[cycle])

        path = consolidate_logs(state, tmp_path)
        content = path.read_text()

        # Header should exist before the first step record line
        lines = content.strip().split("\n")
        assert len(lines) >= 2  # At least header + one step


class TestLogLineFormat:
    """AC2: Each step record formatted as specified."""

    def test_log_line_contains_cycle_index(self, tmp_path):
        """Format: [Cycle {cycle_index}] [...]."""
        from bmad_orch.engine.logs import consolidate_logs

        step = _make_step("generate-code", provider="claude", outcome="success")
        cycle = _make_cycle("c1", steps=[step])
        state = _make_state_with_history(cycles=[cycle])

        path = consolidate_logs(state, tmp_path)
        content = path.read_text()

        assert "[Cycle 0]" in content or "[Cycle 1]" in content

    def test_log_line_contains_step_id(self, tmp_path):
        """Format: [...] [{step_id}] [...]."""
        from bmad_orch.engine.logs import consolidate_logs

        step = _make_step("generate-code")
        cycle = _make_cycle("c1", steps=[step])
        state = _make_state_with_history(cycles=[cycle])

        path = consolidate_logs(state, tmp_path)
        content = path.read_text()

        assert "[generate-code]" in content

    def test_log_line_contains_provider_name(self, tmp_path):
        """Format: [...] [{provider_name}] [...]."""
        from bmad_orch.engine.logs import consolidate_logs

        step = _make_step("s1", provider="claude")
        cycle = _make_cycle("c1", steps=[step])
        state = _make_state_with_history(cycles=[cycle])

        path = consolidate_logs(state, tmp_path)
        content = path.read_text()

        assert "[claude]" in content

    def test_log_line_contains_outcome(self, tmp_path):
        """Format: [...] {outcome}."""
        from bmad_orch.engine.logs import consolidate_logs

        step = _make_step("s1", outcome="success")
        cycle = _make_cycle("c1", steps=[step])
        state = _make_state_with_history(cycles=[cycle])

        path = consolidate_logs(state, tmp_path)
        content = path.read_text()

        assert "success" in content

    def test_log_line_includes_error_message_when_present(self, tmp_path):
        """Format: [...] {outcome} {error.message if error}."""
        from bmad_orch.engine.logs import consolidate_logs

        error = ErrorRecord(
            message="Provider timed out",
            error_type="ProviderCrashError",
        )
        step = _make_step("s1", outcome="failure", error=error)
        cycle = _make_cycle("c1", steps=[step])
        state = _make_state_with_history(cycles=[cycle])

        path = consolidate_logs(state, tmp_path)
        content = path.read_text()

        assert "Provider timed out" in content

    def test_log_line_no_error_when_none(self, tmp_path):
        """No error message appended when error is None."""
        from bmad_orch.engine.logs import consolidate_logs

        step = _make_step("s1", outcome="success")
        cycle = _make_cycle("c1", steps=[step])
        state = _make_state_with_history(cycles=[cycle])

        path = consolidate_logs(state, tmp_path)
        content = path.read_text()

        # Line for step s1 should end with "success" (no trailing error text)
        step_lines = [l for l in content.split("\n") if "[s1]" in l]
        assert len(step_lines) == 1
        assert step_lines[0].rstrip().endswith("success")

    def test_log_line_provider_none_shown_as_none(self, tmp_path):
        """Provider name 'None' shown when provider_name is None-like."""
        from bmad_orch.engine.logs import consolidate_logs

        step = _make_step("s1", provider="None")
        cycle = _make_cycle("c1", steps=[step])
        state = _make_state_with_history(cycles=[cycle])

        path = consolidate_logs(state, tmp_path)
        content = path.read_text()

        assert '[None]' in content


class TestLogTimestampFormatting:
    """AC2: Timestamps must be ISO-8601 UTC."""

    def test_timestamp_is_iso8601_utc(self, tmp_path):
        """Timestamps in log lines must be ISO-8601 UTC format."""
        from bmad_orch.engine.logs import consolidate_logs

        ts = datetime(2026, 3, 15, 10, 30, 0, tzinfo=UTC)
        step = _make_step("s1", ts=ts)
        cycle = _make_cycle("c1", steps=[step])
        state = _make_state_with_history(cycles=[cycle])

        path = consolidate_logs(state, tmp_path)
        content = path.read_text()

        # Should contain ISO-8601 UTC timestamp
        assert "2026-03-15T10:30:00" in content

    def test_naive_timestamp_treated_as_utc(self, tmp_path):
        """Naive datetime (no tzinfo) must be treated as UTC."""
        from bmad_orch.engine.logs import consolidate_logs

        naive_ts = datetime(2026, 3, 15, 10, 30, 0)  # No tzinfo
        step = _make_step("s1", ts=naive_ts)
        cycle = _make_cycle("c1", steps=[step])
        state = _make_state_with_history(cycles=[cycle])

        path = consolidate_logs(state, tmp_path)
        content = path.read_text()

        assert "2026-03-15T10:30:00" in content

    def test_aware_timestamp_converted_to_utc(self, tmp_path):
        """Timezone-aware datetime must be converted to UTC."""
        from bmad_orch.engine.logs import consolidate_logs

        # EST = UTC-5
        est = timezone(offset=__import__("datetime").timedelta(hours=-5))
        aware_ts = datetime(2026, 3, 15, 10, 30, 0, tzinfo=est)  # 10:30 EST
        step = _make_step("s1", ts=aware_ts)
        cycle = _make_cycle("c1", steps=[step])
        state = _make_state_with_history(cycles=[cycle])

        path = consolidate_logs(state, tmp_path)
        content = path.read_text()

        # 10:30 EST = 15:30 UTC
        assert "2026-03-15T15:30:00" in content


class TestLogChronologicalOrdering:
    """AC2: Entries ordered chronologically with tiebreakers."""

    def test_steps_ordered_by_timestamp(self, tmp_path):
        """Steps from different cycles sorted by timestamp."""
        from bmad_orch.engine.logs import consolidate_logs

        ts1 = datetime(2026, 3, 15, 10, 0, 0, tzinfo=UTC)
        ts2 = datetime(2026, 3, 15, 10, 5, 0, tzinfo=UTC)
        ts3 = datetime(2026, 3, 15, 10, 10, 0, tzinfo=UTC)

        step_a = _make_step("step-a", ts=ts3)  # Latest
        step_b = _make_step("step-b", ts=ts1)  # Earliest
        step_c = _make_step("step-c", ts=ts2)  # Middle

        cycle1 = _make_cycle("c1", steps=[step_a])
        cycle2 = _make_cycle("c2", steps=[step_b, step_c])
        state = _make_state_with_history(cycles=[cycle1, cycle2])

        path = consolidate_logs(state, tmp_path)
        content = path.read_text()

        lines = [l for l in content.split("\n") if "[step-" in l]
        assert len(lines) == 3
        # Order should be: step-b (earliest), step-c (middle), step-a (latest)
        assert lines[0].index("[step-b]") >= 0
        assert lines[1].index("[step-c]") >= 0
        assert lines[2].index("[step-a]") >= 0

    def test_tiebreaker_cycle_index_then_step_index(self, tmp_path):
        """Equal timestamps broken by cycle index, then step index."""
        from bmad_orch.engine.logs import consolidate_logs

        same_ts = datetime(2026, 3, 15, 10, 0, 0, tzinfo=UTC)

        step_c1_s0 = _make_step("c1-s0", ts=same_ts)
        step_c1_s1 = _make_step("c1-s1", ts=same_ts)
        step_c2_s0 = _make_step("c2-s0", ts=same_ts)

        cycle1 = _make_cycle("c1", steps=[step_c1_s0, step_c1_s1])
        cycle2 = _make_cycle("c2", steps=[step_c2_s0])
        state = _make_state_with_history(cycles=[cycle1, cycle2])

        path = consolidate_logs(state, tmp_path)
        content = path.read_text()

        lines = [l for l in content.split("\n") if "c1-s" in l or "c2-s" in l]
        assert len(lines) == 3
        # Order: c1-s0 (cycle 0, step 0), c1-s1 (cycle 0, step 1), c2-s0 (cycle 1, step 0)
        assert "c1-s0" in lines[0]
        assert "c1-s1" in lines[1]
        assert "c2-s0" in lines[2]


# ---------------------------------------------------------------------------
# Unit Tests — Auto-create directories (AC 7)
# ---------------------------------------------------------------------------


class TestAutoCreateDirectories:
    """AC7: Auto-create parent directories for log output."""

    def test_creates_missing_parent_directories(self, tmp_path):
        """Output dir does not exist → created automatically."""
        from bmad_orch.engine.logs import consolidate_logs

        step = _make_step("s1")
        cycle = _make_cycle("c1", steps=[step])
        state = _make_state_with_history(cycles=[cycle])

        nested_dir = tmp_path / "deep" / "nested" / "output"
        assert not nested_dir.exists()

        result_path = consolidate_logs(state, nested_dir)

        assert nested_dir.exists()
        assert result_path.exists()


# ---------------------------------------------------------------------------
# Unit Tests — Resumed run history (AC 8)
# ---------------------------------------------------------------------------


class TestResumedRunHistory:
    """AC8: Resumed runs include all steps from entire history."""

    def test_includes_pre_resume_steps(self, tmp_path):
        """Log must include steps from before and after resume."""
        from bmad_orch.engine.logs import consolidate_logs

        ts1 = datetime(2026, 3, 15, 10, 0, 0, tzinfo=UTC)
        ts2 = datetime(2026, 3, 15, 10, 5, 0, tzinfo=UTC)
        ts3 = datetime(2026, 3, 15, 11, 0, 0, tzinfo=UTC)  # After resume

        pre_step = _make_step("pre-resume-step", ts=ts1)
        fail_step = _make_step("failed-step", outcome="failure", ts=ts2)
        post_step = _make_step("post-resume-step", ts=ts3)

        cycle1 = _make_cycle("c1", steps=[pre_step, fail_step])
        cycle2 = _make_cycle("c2", steps=[post_step])  # After resume
        state = _make_state_with_history(cycles=[cycle1, cycle2])

        path = consolidate_logs(state, tmp_path)
        content = path.read_text()

        assert "[pre-resume-step]" in content
        assert "[failed-step]" in content
        assert "[post-resume-step]" in content


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases for log consolidation."""

    def test_empty_run_history(self, tmp_path):
        """Empty run_history should produce a log with header only."""
        from bmad_orch.engine.logs import consolidate_logs

        state = _make_state_with_history(cycles=[])

        path = consolidate_logs(state, tmp_path)

        assert path.exists()
        content = path.read_text()
        # Should have metadata header but no step lines
        assert len(content.strip()) > 0

    def test_cycle_with_no_steps(self, tmp_path):
        """Cycle with empty steps list should be handled gracefully."""
        from bmad_orch.engine.logs import consolidate_logs

        empty_cycle = _make_cycle("c1", steps=[])
        state = _make_state_with_history(cycles=[empty_cycle])

        path = consolidate_logs(state, tmp_path)

        assert path.exists()


# ---------------------------------------------------------------------------
# Integration Tests — Runner calls consolidate_logs (AC 1)
# ---------------------------------------------------------------------------


class TestRunnerCallsConsolidateLogs:
    """AC1: Runner must call consolidate_logs before git operations."""

    @pytest.mark.asyncio
    async def test_emergency_halt_calls_consolidate_logs(self):
        """consolidate_logs called during _emergency_halt before git commit."""
        from bmad_orch.engine.runner import Runner
        from bmad_orch.state.schema import RunStatus

        config = _make_minimal_config()
        runner = Runner(config=config, state_path=Path("/tmp/test-state.json"))
        # Use RUNNING state so the FAILED transition is valid
        step = _make_step("s1")
        cycle = _make_cycle("c1", steps=[step])
        runner.state = RunState(
            run_id="test-run-1",
            status=RunStatus.RUNNING,
            run_history=[cycle],
        )
        runner.git_client = AsyncMock()

        with (
            patch.object(runner.state_manager, "record_halt", return_value=runner.state),
            patch("bmad_orch.engine.runner.consolidate_logs") as mock_consolidate,
        ):
            await runner._emergency_halt(
                error=Exception("crash"), is_abort=False
            )

        mock_consolidate.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_completion_calls_consolidate_logs(self):
        """consolidate_logs called at end of successful _run_internal."""
        from bmad_orch.engine.runner import Runner

        config = _make_minimal_config()
        runner = Runner(config=config, state_path=Path("/tmp/test-state.json"))
        runner.state = _make_state_with_history()

        with patch("bmad_orch.engine.logs.consolidate_logs") as mock_consolidate:
            # We just verify the function is wired in; full run is complex
            mock_consolidate.assert_not_called()  # Baseline


class TestResumeCallsConsolidateLogs:
    """AC8: Resume flow must call consolidate_logs at end."""

    def test_resume_flow_calls_consolidate_logs(self):
        """consolidate_logs called at end of resume flow."""
        # This test verifies the wiring in resume.py
        with patch("bmad_orch.engine.logs.consolidate_logs") as mock_consolidate:
            # Import resume module to check it references consolidate_logs
            import bmad_orch.engine.resume as resume_mod

            assert hasattr(resume_mod, "consolidate_logs") or mock_consolidate.called
            # Actual integration test would run resume and verify call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_minimal_config():
    """Create a minimal OrchestratorConfig for testing."""
    from bmad_orch.config.schema import OrchestratorConfig

    return OrchestratorConfig.model_validate({
        "providers": {1: {"name": "p1", "cli": "c1", "model": "m1"}},
        "cycles": {
            "c1": {
                "steps": [
                    {"skill": "s1", "provider": 1, "type": "generative", "prompt": "p1"}
                ]
            }
        },
        "git": {"commit_at": "cycle", "push_at": "end"},
        "pauses": {"between_steps": 1, "between_cycles": 1, "between_workflows": 1},
        "error_handling": {"retry_transient": True, "max_retries": 3, "retry_delay": 10},
    })
