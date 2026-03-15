import pathlib
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from bmad_orch.config.schema import OrchestratorConfig
from bmad_orch.exceptions import (
    GitError,
    ProviderCrashError,
    ResourceError,
)
from bmad_orch.state.manager import StateManager
from bmad_orch.state.schema import RunState, RunStatus

# ---------------------------------------------------------------------------
# Unit Tests — RunState schema (AC3)
# ---------------------------------------------------------------------------


class TestRunStateFailureFields:
    """AC3: RunState must include failure tracking fields."""

    def test_run_state_has_status_field(self) -> None:
        """RunState should have a status field with RunStatus enum."""
        state = RunState(run_id="test-1")
        assert state.status == RunStatus.PENDING

    def test_run_state_has_halted_at_field(self) -> None:
        """RunState.halted_at should default to None."""
        state = RunState(run_id="test-1")
        assert state.halted_at is None

    def test_run_state_has_failure_point_field(self) -> None:
        """RunState.failure_point should default to None."""
        state = RunState(run_id="test-1")
        assert state.failure_point is None

    def test_run_state_has_failure_reason_field(self) -> None:
        """RunState.failure_reason should default to None."""
        state = RunState(run_id="test-1")
        assert state.failure_reason is None

    def test_run_state_has_error_type_field(self) -> None:
        """RunState.error_type should default to None."""
        state = RunState(run_id="test-1")
        assert state.error_type is None

    def test_halted_at_is_timezone_aware_utc(self) -> None:
        """AC3: halted_at must be timezone-aware UTC (ISO 8601 with Z offset)."""
        now = datetime.now(UTC)
        state = RunState(
            run_id="test-1",
            status=RunStatus.FAILED,
            halted_at=now,
            failure_point="cycle:1/step:generate-code",
            failure_reason="Provider crashed",
            error_type="ProviderCrashError",
        )
        assert state.halted_at is not None
        assert state.halted_at.tzinfo is not None
        # In Python 3.11+ UTC offset is 0 for UTC
        offset = state.halted_at.utcoffset()
        assert offset is not None
        assert offset.total_seconds() == 0


class TestRunStatusEnum:
    """AC3: RunStatus enum with valid transitions."""

    def test_run_status_values(self) -> None:
        """RunStatus should have PENDING, RUNNING, COMPLETED, FAILED, HALTED."""
        assert RunStatus.PENDING
        assert RunStatus.RUNNING
        assert RunStatus.COMPLETED
        assert RunStatus.FAILED
        assert RunStatus.HALTED

    def test_valid_transition_pending_to_running(self) -> None:
        """PENDING → RUNNING should be allowed via update_status."""
        state = RunState(run_id="test-1", status=RunStatus.PENDING)
        state.update_status(RunStatus.RUNNING)
        assert state.status == RunStatus.RUNNING

    def test_invalid_transition_completed_to_running_blocked(self) -> None:
        """COMPLETED → RUNNING should be blocked."""
        state = RunState(run_id="test-1", status=RunStatus.COMPLETED)
        # Implementation should raise on invalid transition
        with pytest.raises(ValueError, match="Invalid status transition"):
            state.update_status(RunStatus.RUNNING)

    def test_status_failed_for_errors(self) -> None:
        """AC3: Status set to FAILED for errors."""
        state = RunState(run_id="test-1", status=RunStatus.FAILED)
        assert state.status == RunStatus.FAILED

    def test_status_halted_for_aborts(self) -> None:
        """AC3: Status set to HALTED for user aborts."""
        state = RunState(run_id="test-1", status=RunStatus.HALTED)
        assert state.status == RunStatus.HALTED


# ---------------------------------------------------------------------------
# Unit Tests — StateManager.record_halt (AC3)
# ---------------------------------------------------------------------------


class TestRecordHalt:
    """AC3: StateManager.record_halt records failure fields atomically."""

    def test_record_halt_sets_failure_fields(self, tmp_path: pathlib.Path) -> None:
        """record_halt should populate all failure tracking fields."""
        state_path = tmp_path / "bmad-orch-state.json"
        state = RunState(run_id="test-1", status=RunStatus.RUNNING)
        updated = StateManager.record_halt(
            state=state,
            failure_point="cycle:1/step:generate-code",
            failure_reason="Provider crashed unexpectedly",
            error_type="ProviderCrashError",
            path=state_path,
            is_abort=False,
        )
        assert updated.status == RunStatus.FAILED
        assert updated.failure_point == "cycle:1/step:generate-code"
        assert updated.failure_reason == "Provider crashed unexpectedly"
        assert updated.error_type == "ProviderCrashError"
        assert updated.halted_at is not None
        assert updated.halted_at.tzinfo is not None

    def test_record_halt_sets_halted_for_abort(self, tmp_path: pathlib.Path) -> None:
        """record_halt with is_abort=True should set status to HALTED."""
        state_path = tmp_path / "bmad-orch-state.json"
        state = RunState(run_id="test-1", status=RunStatus.RUNNING)
        updated = StateManager.record_halt(
            state=state,
            failure_point="cycle:2/step:validate",
            failure_reason="User pressed Ctrl+C",
            error_type="UserAbort",
            path=state_path,
            is_abort=True,
        )
        assert updated.status == RunStatus.HALTED

    def test_record_halt_atomic_save(self, tmp_path: pathlib.Path) -> None:
        """AC1: State saved atomically (write-to-temp-then-rename)."""
        state_path = tmp_path / "bmad-orch-state.json"
        state = RunState(run_id="test-1", status=RunStatus.RUNNING)

        StateManager.record_halt(
            state=state,
            failure_point="cycle:1/step:generate-code",
            failure_reason="crash",
            error_type="ProviderCrashError",
            path=state_path,
        )

        # Verify file exists and no temp files remain
        assert state_path.exists()
        tmp_files = list(tmp_path.glob(".*.tmp"))
        assert len(tmp_files) == 0

        # Verify contents round-trip
        loaded = StateManager.load(state_path)
        assert loaded.status == RunStatus.FAILED
        assert loaded.failure_point == "cycle:1/step:generate-code"


# ---------------------------------------------------------------------------
# Integration Tests — Emergency flow in Runner (AC1, AC2)
# ---------------------------------------------------------------------------


class TestEmergencyFlowOrder:
    """AC1: Emergency flow executes save → commit → push → halt in order."""

    @pytest.mark.asyncio
    async def test_emergency_flow_triggers_on_impactful_error(self, tmp_path: pathlib.Path) -> None:
        """AC1: Provider crash triggers the emergency flow."""
        from bmad_orch.engine.runner import Runner

        config = _make_minimal_config()
        state_path = tmp_path / "test-state.json"
        runner = Runner(config=config, state_path=state_path)
        runner.git_client = AsyncMock()

        # Simulate provider crash during execution by patching _run_internal
        with (
            patch.object(runner, "_handle_impactful_error", new_callable=AsyncMock) as mock_handler,
            patch.object(runner, "_run_internal", side_effect=ProviderCrashError("crash"))
        ):
            try:
                await runner.run()
            except ProviderCrashError:
                pass
            assert mock_handler.called

    @pytest.mark.asyncio
    async def test_emergency_flow_order_save_commit_push_halt(self, tmp_path: pathlib.Path) -> None:
        """AC1: Verify exact order: save state → git commit → git push → halt."""
        from bmad_orch.engine.runner import Runner

        call_order = []

        config = _make_minimal_config()
        state_path = tmp_path / "bmad-orch-state.json"
        runner = Runner(config=config, state_path=state_path)
        runner.state = RunState(run_id="test-1", status=RunStatus.RUNNING)
        runner.git_client = AsyncMock()
        runner.git_client.enabled = True
        runner.git_client.add = AsyncMock(side_effect=lambda *a, **kw: call_order.append("add"))
        runner.git_client.commit = AsyncMock(side_effect=lambda *a, **kw: call_order.append("commit"))
        runner.git_client.push = AsyncMock(side_effect=lambda *a, **kw: call_order.append("push"))

        with patch.object(StateManager, "save", side_effect=lambda *a, **kw: call_order.append("save")):
            await runner._handle_impactful_error(ProviderCrashError("crash"))

        assert call_order == ["save", "add", "commit", "push"]

    @pytest.mark.asyncio
    async def test_git_error_trigger_skips_git_operations(self, tmp_path: pathlib.Path) -> None:
        """AC1: GitError as triggering error skips git commit/push (no recursion)."""
        from bmad_orch.engine.runner import Runner

        call_order = []

        config = _make_minimal_config()
        state_path = tmp_path / "bmad-orch-state.json"
        runner = Runner(config=config, state_path=state_path)
        runner.state = RunState(run_id="test-1", status=RunStatus.RUNNING)
        runner.git_client = AsyncMock()
        runner.git_client.add = AsyncMock(side_effect=lambda *a, **kw: call_order.append("add"))
        runner.git_client.commit = AsyncMock(side_effect=lambda *a, **kw: call_order.append("commit"))

        with patch.object(StateManager, "save", side_effect=lambda *a, **kw: call_order.append("save")):
            await runner._handle_impactful_error(GitError("git broke"))

        # State should still be saved, but git ops should be skipped
        assert "save" in call_order
        assert "add" not in call_order
        assert "commit" not in call_order


class TestSecondaryGitFailure:
    """AC2: Secondary git failure handling during emergency flow."""

    @pytest.mark.asyncio
    async def test_git_add_failure_skips_commit_and_push(self, tmp_path: pathlib.Path) -> None:
        """AC2: If git add fails, skip commit and push."""
        from bmad_orch.engine.runner import Runner

        config = _make_minimal_config()
        state_path = tmp_path / "bmad-orch-state.json"
        runner = Runner(config=config, state_path=state_path)
        runner.state = RunState(run_id="test-1", status=RunStatus.RUNNING)
        runner.git_client = AsyncMock()
        runner.git_client.add = AsyncMock(side_effect=GitError("add failed"))
        runner.git_client.commit = AsyncMock()
        runner.git_client.push = AsyncMock()

        with patch.object(StateManager, "save"):
            await runner._handle_impactful_error(ProviderCrashError("crash"))

        runner.git_client.commit.assert_not_called()
        runner.git_client.push.assert_not_called()


    @pytest.mark.asyncio
    async def test_git_push_failure_produces_valid_halt_state(self, tmp_path: pathlib.Path) -> None:
        """AC2: Partial emergency completion (push failed) still produces a valid halt state."""
        from bmad_orch.engine.runner import Runner

        config = _make_minimal_config()
        state_path = tmp_path / "bmad-orch-state.json"
        runner = Runner(config=config, state_path=state_path)
        runner.state = RunState(run_id="test-1", status=RunStatus.RUNNING)
        runner.git_client = AsyncMock()
        runner.git_client.add = AsyncMock()
        runner.git_client.commit = AsyncMock()
        runner.git_client.push = AsyncMock(side_effect=GitError("push failed"))

        await runner._handle_impactful_error(ProviderCrashError("crash"))

        # State should have been saved
        loaded = StateManager.load(state_path)
        assert loaded.status == RunStatus.FAILED
        assert loaded.error_type == "ProviderCrashError"
        # Git operations before push should have been called
        runner.git_client.add.assert_called_once()
        runner.git_client.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Unit Tests — Subprocess cleanup (Architecture compliance)
# ---------------------------------------------------------------------------


class TestSubprocessCleanup:
    """Subprocess cleanup must be fully awaited even under cancellation."""

    @pytest.mark.asyncio
    async def test_subprocess_killed_and_waited_during_emergency(self, tmp_path: pathlib.Path) -> None:
        """Subprocesses are killed via process.kill() + await process.wait()."""
        from bmad_orch.engine.runner import Runner

        config = _make_minimal_config()
        state_path = tmp_path / "bmad-orch-state.json"
        runner = Runner(config=config, state_path=state_path)
        runner.state = RunState(run_id="test-1", status=RunStatus.RUNNING)
        runner.git_client = None

        # Inject a tracked subprocess via mock executor
        mock_executor = AsyncMock()
        mock_executor.cleanup_processes = AsyncMock()
        runner._executor = mock_executor

        with patch.object(StateManager, "save"):
            await runner._handle_impactful_error(ProviderCrashError("crash"))

        mock_executor.cleanup_processes.assert_awaited_once()


# ---------------------------------------------------------------------------
# Integration Tests — CLI exit codes (AC4)
# ---------------------------------------------------------------------------


class TestExitCodes:
    """AC4: Headless mode exit codes."""

    def test_exit_code_3_for_runtime_error(self, tmp_path: pathlib.Path) -> None:
        """Exit code 3 for ResourceError."""
        from bmad_orch.cli import app
        
        config_file = tmp_path / "bmad-orch.yaml"
        config_file.write_text("providers: {1: {name: p1, cli: c1, model: m1}}\ncycles: {c1: {steps: [{skill: s1, provider: 1}]}}")

        runner = CliRunner()
        with (
            patch("bmad_orch.cli.Runner") as mock_runner_cls,
            patch("bmad_orch.cli.get_config", return_value=(_make_minimal_config(), config_file)),
            patch("bmad_orch.cli.validate_provider_availability"),
            patch("bmad_orch.cli.StateManager.load", return_value=RunState(run_id="test-1")),
        ):
            instance = mock_runner_cls.return_value
            instance.run = AsyncMock(side_effect=ResourceError("disk full"))
            result = runner.invoke(app, ["start", "--config", str(config_file), "--no-preflight"])

        assert result.exit_code == 3

    def test_exit_code_4_for_provider_error(self, tmp_path: pathlib.Path) -> None:
        """Exit code 4 for ProviderCrashError."""
        from bmad_orch.cli import app
        
        config_file = tmp_path / "bmad-orch.yaml"
        config_file.write_text("providers: {1: {name: p1, cli: c1, model: m1}}\ncycles: {c1: {steps: [{skill: s1, provider: 1}]}}")

        runner = CliRunner()
        with (
            patch("bmad_orch.cli.Runner") as mock_runner_cls,
            patch("bmad_orch.cli.get_config", return_value=(_make_minimal_config(), config_file)),
            patch("bmad_orch.cli.validate_provider_availability"),
            patch("bmad_orch.cli.StateManager.load", return_value=RunState(run_id="test-1")),
        ):
            instance = mock_runner_cls.return_value
            instance.run = AsyncMock(side_effect=ProviderCrashError("model crashed"))
            result = runner.invoke(app, ["start", "--config", str(config_file), "--no-preflight"])

        assert result.exit_code == 4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_minimal_config() -> OrchestratorConfig:
    """Create a minimal OrchestratorConfig for testing emergency flow."""
    return OrchestratorConfig.model_validate({
        "providers": {1: {"name": "p1", "cli": "c1", "model": "m1"}},
        "cycles": {
            "c1": {
                "steps": [
                    {"skill": "s1", "provider": 1, "type": "generative", "prompt": "p1"}
                ]
            }
        },
        "git": {"enabled": True, "commit_at": "cycle", "push_at": "end", "remote": "origin", "branch": "main"},
        "pauses": {"between_cycle_types": 0, "between_steps": 0, "between_cycles": 0, "between_workflows": 0},
        "error_handling": {"retry_transient": False, "max_retries": 1, "retry_delay": 0},
    })
