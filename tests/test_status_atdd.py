"""ATDD tests for Story 4.5: Status Command (AC 3, 4, 5, 6).

TDD RED PHASE — All tests are skipped. Remove @pytest.mark.skip to verify
implementation (green phase). Every test asserts EXPECTED behavior that does
not exist yet.

Acceptance Criteria covered:
  AC3: Status command displays run status, last step, cycle progress,
       elapsed time, errors. Exit code 0 for non-failed; 3 for FAILED/HALTED.
       Corrupted state file exits with code 2.
  AC4: Missing state file reports to stderr and exits with code 1.
  AC5: FAILED/HALTED shows failure details; suggests resume only if
       recoverable. NON_RECOVERABLE_ERROR_TYPES constant in errors.py.
  AC6: --json outputs full RunState JSON to stdout; suppresses all other output.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from bmad_orch.state.schema import CycleRecord, ErrorRecord, RunState, StepRecord

SKIP_REASON = "ATDD red phase: Story 4.5 not implemented"

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_step(
    step_id: str = "generate-code",
    provider: str = "claude",
    outcome: str = "success",
    ts: datetime | None = None,
    error: ErrorRecord | None = None,
) -> StepRecord:
    return StepRecord(
        step_id=step_id,
        provider_name=provider,
        outcome=outcome,
        timestamp=ts or datetime.now(UTC),
        error=error,
    )


def _make_completed_state(run_id: str = "test-run-1") -> RunState:
    """State in COMPLETED status with one cycle and one step."""
    from bmad_orch.state.schema import RunStatus

    step = _make_step()
    cycle = CycleRecord(
        cycle_id="c1",
        steps=[step],
        started_at=datetime.now(UTC) - timedelta(minutes=5),
        finished_at=datetime.now(UTC),
        outcome="success",
    )
    return RunState(
        run_id=run_id,
        status=RunStatus.COMPLETED,
        run_history=[cycle],
    )


def _make_failed_state(
    error_type: str = "ProviderCrashError",
    run_id: str = "test-run-1",
) -> RunState:
    """State in FAILED status with failure details."""
    from bmad_orch.state.schema import RunStatus

    step = _make_step(outcome="failure", error=ErrorRecord(
        message="Provider timed out",
        error_type=error_type,
    ))
    cycle = CycleRecord(
        cycle_id="c1",
        steps=[step],
        started_at=datetime.now(UTC) - timedelta(minutes=5),
        finished_at=datetime.now(UTC),
        outcome="failure",
    )
    return RunState(
        run_id=run_id,
        status=RunStatus.FAILED,
        run_history=[cycle],
        failure_point="cycle:1/step:generate-code",
        failure_reason="Provider timed out",
        error_type=error_type,
        halted_at=datetime.now(UTC),
    )


def _make_running_state(run_id: str = "test-run-1") -> RunState:
    """State in RUNNING status."""
    from bmad_orch.state.schema import RunStatus

    step = _make_step()
    cycle = CycleRecord(
        cycle_id="c1",
        steps=[step],
        started_at=datetime.now(UTC) - timedelta(minutes=2),
    )
    return RunState(
        run_id=run_id,
        status=RunStatus.RUNNING,
        run_history=[cycle],
    )


def _make_pending_state(run_id: str = "test-run-1") -> RunState:
    """State in PENDING status."""
    from bmad_orch.state.schema import RunStatus

    return RunState(
        run_id=run_id,
        status=RunStatus.PENDING,
        run_history=[],
    )


def _make_halted_state(run_id: str = "test-run-1") -> RunState:
    """State in HALTED status (user abort)."""
    from bmad_orch.state.schema import RunStatus

    step = _make_step(outcome="failure")
    cycle = CycleRecord(
        cycle_id="c1",
        steps=[step],
        started_at=datetime.now(UTC) - timedelta(minutes=3),
        finished_at=datetime.now(UTC),
    )
    return RunState(
        run_id=run_id,
        status=RunStatus.HALTED,
        run_history=[cycle],
        failure_point="cycle:1/step:generate-code",
        failure_reason="User pressed Ctrl+C",
        error_type="UserAbort",
        halted_at=datetime.now(UTC),
    )


def _write_state_file(state: RunState, path: Path) -> Path:
    """Write RunState as JSON to a file and return the path."""
    state_file = path / "bmad-orch-state.json"
    state_file.write_text(state.model_dump_json(indent=2))
    return state_file


# ---------------------------------------------------------------------------
# AC3: Status display for various RunStatus values
# ---------------------------------------------------------------------------


class TestStatusDisplayCompleted:
    """AC3: Status command for COMPLETED runs."""

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_completed_run_shows_status(self, tmp_path):
        """Status output includes run status for COMPLETED."""
        from bmad_orch.cli import app

        state = _make_completed_state()
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "COMPLETED" in result.output or "completed" in result.output.lower()

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_completed_run_shows_last_step(self, tmp_path):
        """Status output includes last completed step with provider."""
        from bmad_orch.cli import app

        state = _make_completed_state()
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status"])

        assert "generate-code" in result.output
        assert "claude" in result.output

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_completed_run_shows_cycle_progress(self, tmp_path):
        """Status output includes cycle progress (completed/total)."""
        from bmad_orch.cli import app

        state = _make_completed_state()
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status"])

        # Should show something like "1/1" or "100%"
        assert "1" in result.output

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_completed_run_shows_elapsed_time(self, tmp_path):
        """Elapsed time = end_time - start_time for terminal states."""
        from bmad_orch.cli import app

        state = _make_completed_state()
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        # Should contain some time indication (minutes, seconds, etc.)
        output_lower = result.output.lower()
        assert any(t in output_lower for t in ["elapsed", "time", "duration", "min", "sec"])

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_completed_run_exit_code_0(self, tmp_path):
        """AC3: Exit code 0 for non-failed states."""
        from bmad_orch.cli import app

        state = _make_completed_state()
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0


class TestStatusDisplayRunning:
    """AC3: Status command for RUNNING state."""

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_running_shows_elapsed_since_start(self, tmp_path):
        """Elapsed time = now - start_time for RUNNING."""
        from bmad_orch.cli import app

        state = _make_running_state()
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_running_exit_code_0(self, tmp_path):
        """AC3: RUNNING is a non-failed state → exit code 0."""
        from bmad_orch.cli import app

        state = _make_running_state()
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0


class TestStatusDisplayPending:
    """AC3: Status command for PENDING state."""

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_pending_shows_not_started(self, tmp_path):
        """AC3: PENDING displays 'not started' for elapsed time."""
        from bmad_orch.cli import app

        state = _make_pending_state()
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status"])

        assert "not started" in result.output.lower()
        assert result.exit_code == 0


class TestStatusDisplayFailed:
    """AC3, AC5: Status for FAILED runs with failure details."""

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_failed_run_exit_code_3(self, tmp_path):
        """AC3: Exit code 3 for FAILED state."""
        from bmad_orch.cli import app

        state = _make_failed_state()
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 3

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_failed_shows_failure_point(self, tmp_path):
        """AC5: Output includes failure_point."""
        from bmad_orch.cli import app

        state = _make_failed_state()
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status"])

        assert "cycle:1/step:generate-code" in result.output

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_failed_shows_failure_reason(self, tmp_path):
        """AC5: Output includes failure_reason."""
        from bmad_orch.cli import app

        state = _make_failed_state()
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status"])

        assert "Provider timed out" in result.output

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_failed_shows_error_type(self, tmp_path):
        """AC5: Output includes error_type."""
        from bmad_orch.cli import app

        state = _make_failed_state()
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status"])

        assert "ProviderCrashError" in result.output

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_failed_suggests_resume_for_recoverable(self, tmp_path):
        """AC5: Suggests bmad-orch resume for recoverable failure."""
        from bmad_orch.cli import app

        state = _make_failed_state(error_type="ProviderCrashError")
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status"])

        assert "resume" in result.output.lower()

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_failed_no_resume_for_config_error(self, tmp_path):
        """AC5: No resume suggestion for ConfigError (non-recoverable)."""
        from bmad_orch.cli import app

        state = _make_failed_state(error_type="ConfigError")
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status"])

        # Should NOT suggest resume
        assert "resume" not in result.output.lower()

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_failed_no_resume_for_schema_validation_error(self, tmp_path):
        """AC5: No resume suggestion for SchemaValidationError."""
        from bmad_orch.cli import app

        state = _make_failed_state(error_type="SchemaValidationError")
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status"])

        assert "resume" not in result.output.lower()

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_failed_no_resume_for_system_error(self, tmp_path):
        """AC5: No resume suggestion for SystemError."""
        from bmad_orch.cli import app

        state = _make_failed_state(error_type="SystemError")
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status"])

        assert "resume" not in result.output.lower()


class TestStatusDisplayHalted:
    """AC3: Status for HALTED (user abort) runs."""

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_halted_run_exit_code_3(self, tmp_path):
        """AC3: Exit code 3 for HALTED state."""
        from bmad_orch.cli import app

        state = _make_halted_state()
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 3

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_halted_suggests_resume(self, tmp_path):
        """AC5: UserAbort is recoverable — suggest resume."""
        from bmad_orch.cli import app

        state = _make_halted_state()
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status"])

        assert "resume" in result.output.lower()


# ---------------------------------------------------------------------------
# AC4: Missing state file
# ---------------------------------------------------------------------------


class TestStatusMissingState:
    """AC4: Missing state file handling."""

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_no_state_file_exit_code_1(self, tmp_path):
        """AC4: No state file → exit code 1."""
        from bmad_orch.cli import app

        nonexistent = tmp_path / "does-not-exist.json"

        with patch("bmad_orch.cli._resolve_state_path", return_value=nonexistent):
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 1

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_no_state_file_reports_to_stderr(self, tmp_path):
        """AC4: Missing state reports to stderr."""
        from bmad_orch.cli import app

        nonexistent = tmp_path / "does-not-exist.json"

        with patch("bmad_orch.cli._resolve_state_path", return_value=nonexistent):
            result = runner.invoke(app, ["status"])

        # CliRunner captures both stdout and stderr; check for error message
        assert "no previous run" in result.output.lower() or result.exit_code == 1

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_specific_run_id_not_found_exit_code_1(self, tmp_path):
        """AC4: --run-id for nonexistent run exits with code 1."""
        from bmad_orch.cli import app

        result = runner.invoke(app, ["status", "--run-id", "nonexistent-run"])

        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# AC3: Corrupted state file
# ---------------------------------------------------------------------------


class TestStatusCorruptedState:
    """AC3: Corrupted/unreadable state file handling."""

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_corrupted_json_exit_code_2(self, tmp_path):
        """AC3: Corrupted JSON → exit code 2."""
        from bmad_orch.cli import app

        state_file = tmp_path / "bmad-orch-state.json"
        state_file.write_text("{invalid json!!!")

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 2

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_invalid_schema_exit_code_2(self, tmp_path):
        """AC3: Valid JSON but invalid RunState schema → exit code 2."""
        from bmad_orch.cli import app

        state_file = tmp_path / "bmad-orch-state.json"
        state_file.write_text('{"not_a_valid_field": true}')

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 2

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_corrupted_reports_to_stderr(self, tmp_path):
        """AC3: Corruption error reported to stderr."""
        from bmad_orch.cli import app

        state_file = tmp_path / "bmad-orch-state.json"
        state_file.write_text("{bad}")

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status"])

        assert "corrupt" in result.output.lower() or result.exit_code == 2


# ---------------------------------------------------------------------------
# AC5: NON_RECOVERABLE_ERROR_TYPES constant
# ---------------------------------------------------------------------------


class TestNonRecoverableErrorTypes:
    """AC5: NON_RECOVERABLE_ERROR_TYPES constant in errors.py."""

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_constant_exists(self):
        """NON_RECOVERABLE_ERROR_TYPES must exist in errors.py."""
        from bmad_orch.engine.errors import NON_RECOVERABLE_ERROR_TYPES

        assert isinstance(NON_RECOVERABLE_ERROR_TYPES, set)

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_constant_contains_required_types(self):
        """Must contain ConfigError, SchemaValidationError, SystemError."""
        from bmad_orch.engine.errors import NON_RECOVERABLE_ERROR_TYPES

        assert "ConfigError" in NON_RECOVERABLE_ERROR_TYPES
        assert "SchemaValidationError" in NON_RECOVERABLE_ERROR_TYPES
        assert "SystemError" in NON_RECOVERABLE_ERROR_TYPES

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_constant_is_set_of_strings(self):
        """All entries must be strings."""
        from bmad_orch.engine.errors import NON_RECOVERABLE_ERROR_TYPES

        assert all(isinstance(t, str) for t in NON_RECOVERABLE_ERROR_TYPES)


# ---------------------------------------------------------------------------
# AC6: --json flag
# ---------------------------------------------------------------------------


class TestStatusJsonOutput:
    """AC6: --json outputs full serialized RunState JSON."""

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_json_flag_outputs_valid_json(self, tmp_path):
        """--json output must be valid, parseable JSON."""
        from bmad_orch.cli import app

        state = _make_completed_state()
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status", "--json"])

        parsed = json.loads(result.output)
        assert isinstance(parsed, dict)

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_json_output_matches_run_state_schema(self, tmp_path):
        """--json output must deserialize back into a valid RunState."""
        from bmad_orch.cli import app

        state = _make_completed_state()
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status", "--json"])

        parsed = json.loads(result.output)
        roundtripped = RunState.model_validate(parsed)
        assert roundtripped.run_id == state.run_id
        assert roundtripped.status == state.status

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_json_output_has_iso8601_datetimes(self, tmp_path):
        """Datetimes serialized as ISO-8601 strings."""
        from bmad_orch.cli import app

        state = _make_completed_state()
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status", "--json"])

        parsed = json.loads(result.output)
        # Check that datetime fields are ISO-8601 strings
        if parsed.get("halted_at"):
            datetime.fromisoformat(parsed["halted_at"])

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_json_output_has_enum_as_string(self, tmp_path):
        """Enums serialized as string values, not integers."""
        from bmad_orch.cli import app

        state = _make_completed_state()
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status", "--json"])

        parsed = json.loads(result.output)
        status_val = parsed.get("status", "")
        assert isinstance(status_val, str)
        assert status_val.lower() in ("completed", "running", "pending", "failed", "halted")

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_json_flag_suppresses_rich_output(self, tmp_path):
        """--json must suppress all non-JSON output from stdout."""
        from bmad_orch.cli import app

        state = _make_completed_state()
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status", "--json"])

        # stdout must be ONLY valid JSON — no Rich formatting, progress bars, etc.
        output = result.output.strip()
        assert output.startswith("{")
        assert output.endswith("}")
        json.loads(output)  # Must not raise

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_json_uses_model_dump_json_indent_2(self, tmp_path):
        """AC6: Output uses Pydantic's .model_dump_json(indent=2)."""
        from bmad_orch.cli import app

        state = _make_completed_state()
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status", "--json"])

        # Indented JSON should have lines starting with spaces
        lines = result.output.strip().split("\n")
        assert any(line.startswith("  ") for line in lines)


# ---------------------------------------------------------------------------
# AC3: --run-id option
# ---------------------------------------------------------------------------


class TestStatusRunIdOption:
    """AC3: --run-id option loads the correct state file."""

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_run_id_option_accepted(self, tmp_path):
        """status command accepts --run-id option."""
        from bmad_orch.cli import app

        state = _make_completed_state(run_id="specific-run")
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status", "--run-id", "specific-run"])

        assert result.exit_code == 0

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_run_id_loads_correct_state(self, tmp_path):
        """--run-id should load state for the specified run."""
        from bmad_orch.cli import app

        state = _make_completed_state(run_id="my-specific-run")
        state_file = _write_state_file(state, tmp_path)

        with patch("bmad_orch.cli._resolve_state_path", return_value=state_file):
            result = runner.invoke(app, ["status", "--run-id", "my-specific-run", "--json"])

        parsed = json.loads(result.output)
        assert parsed["run_id"] == "my-specific-run"


# ---------------------------------------------------------------------------
# Integration: status does not start a new run
# ---------------------------------------------------------------------------


class TestStatusDoesNotStartRun:
    """AC3: Status command must not start a new run."""

    # @pytest.mark.skip(reason=SKIP_REASON)
    def test_status_does_not_invoke_runner(self, tmp_path):
        """status should never instantiate or call Runner."""
        from bmad_orch.cli import app

        state = _make_completed_state()
        state_file = _write_state_file(state, tmp_path)

        with (
            patch("bmad_orch.cli._resolve_state_path", return_value=state_file),
            patch("bmad_orch.cli.Runner", side_effect=AssertionError("Runner should not be created")) as mock_runner,
        ):
            result = runner.invoke(app, ["status"])

        mock_runner.assert_not_called()
