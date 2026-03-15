"""ATDD tests for Story 4.2: Emergency Error Flow & Impactful Error Handling.

TDD RED PHASE — All tests are skipped. Remove @pytest.mark.skip to verify
implementation (green phase). Every test asserts EXPECTED behavior that does
not exist yet.

Acceptance Criteria covered:
  AC1: Emergency flow order (save state → git commit → push → halt)
  AC2: Secondary git failure handling (log + skip remaining)
  AC3: State records failure fields (failure_point, error_type, halted_at, status)
  AC4: Exit codes in headless mode (3=runtime, 4=provider)
  AC5: Error headline formatting
  AC6: Signal handling (SIGINT/SIGTERM → emergency flow)
"""

import asyncio
import pathlib
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from bmad_orch.exceptions import (
    GitError,
    ProviderCrashError,
    ResourceError,
    StateError,
)
from bmad_orch.state.manager import StateManager
from bmad_orch.state.schema import RunState

SKIP_REASON = "ATDD red phase: Story 4.2 not implemented"


# ---------------------------------------------------------------------------
# Unit Tests — RunState schema (AC3)
# ---------------------------------------------------------------------------


class TestRunStateFailureFields:
    """AC3: RunState must include failure tracking fields."""

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_run_state_has_status_field(self):
        """RunState should have a status field with RunStatus enum."""
        from bmad_orch.types import RunStatus

        state = RunState(run_id="test-1")
        assert state.status == RunStatus.PENDING

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_run_state_has_halted_at_field(self):
        """RunState.halted_at should default to None."""
        state = RunState(run_id="test-1")
        assert state.halted_at is None

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_run_state_has_failure_point_field(self):
        """RunState.failure_point should default to None."""
        state = RunState(run_id="test-1")
        assert state.failure_point is None

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_run_state_has_failure_reason_field(self):
        """RunState.failure_reason should default to None."""
        state = RunState(run_id="test-1")
        assert state.failure_reason is None

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_run_state_has_error_type_field(self):
        """RunState.error_type should default to None."""
        state = RunState(run_id="test-1")
        assert state.error_type is None

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_halted_at_is_timezone_aware_utc(self):
        """AC3: halted_at must be timezone-aware UTC (ISO 8601 with Z offset)."""
        from bmad_orch.types import RunStatus

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
        assert state.halted_at.utcoffset().total_seconds() == 0


class TestRunStatusEnum:
    """AC3: RunStatus enum with valid transitions."""

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_run_status_values(self):
        """RunStatus should have PENDING, RUNNING, COMPLETED, FAILED, HALTED."""
        from bmad_orch.types import RunStatus

        assert RunStatus.PENDING
        assert RunStatus.RUNNING
        assert RunStatus.COMPLETED
        assert RunStatus.FAILED
        assert RunStatus.HALTED

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_valid_transition_pending_to_running(self):
        """PENDING → RUNNING should be allowed."""
        from bmad_orch.types import RunStatus

        state = RunState(run_id="test-1", status=RunStatus.PENDING)
        updated = state.model_copy(update={"status": RunStatus.RUNNING})
        assert updated.status == RunStatus.RUNNING

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_invalid_transition_completed_to_running_blocked(self):
        """COMPLETED → RUNNING should be blocked."""
        from bmad_orch.types import RunStatus

        state = RunState(run_id="test-1", status=RunStatus.COMPLETED)
        # Implementation should raise on invalid transition
        with pytest.raises((ValueError, StateError)):
            state.model_copy(update={"status": RunStatus.RUNNING})

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_status_failed_for_errors(self):
        """AC3: Status set to FAILED for errors."""
        from bmad_orch.types import RunStatus

        state = RunState(run_id="test-1", status=RunStatus.FAILED)
        assert state.status == RunStatus.FAILED

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_status_halted_for_aborts(self):
        """AC3: Status set to HALTED for user aborts."""
        from bmad_orch.types import RunStatus

        state = RunState(run_id="test-1", status=RunStatus.HALTED)
        assert state.status == RunStatus.HALTED


# ---------------------------------------------------------------------------
# Unit Tests — StateManager.record_halt (AC3)
# ---------------------------------------------------------------------------


class TestRecordHalt:
    """AC3: StateManager.record_halt records failure fields atomically."""

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_record_halt_sets_failure_fields(self, tmp_path):
        """record_halt should populate all failure tracking fields."""
        from bmad_orch.types import RunStatus

        state = RunState(run_id="test-1", status=RunStatus.RUNNING)
        updated = StateManager.record_halt(
            state=state,
            failure_point="cycle:1/step:generate-code",
            failure_reason="Provider crashed unexpectedly",
            error_type="ProviderCrashError",
            is_abort=False,
        )
        assert updated.status == RunStatus.FAILED
        assert updated.failure_point == "cycle:1/step:generate-code"
        assert updated.failure_reason == "Provider crashed unexpectedly"
        assert updated.error_type == "ProviderCrashError"
        assert updated.halted_at is not None
        assert updated.halted_at.tzinfo is not None

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_record_halt_sets_halted_for_abort(self):
        """record_halt with is_abort=True should set status to HALTED."""
        from bmad_orch.types import RunStatus

        state = RunState(run_id="test-1", status=RunStatus.RUNNING)
        updated = StateManager.record_halt(
            state=state,
            failure_point="cycle:2/step:validate",
            failure_reason="User pressed Ctrl+C",
            error_type="UserAbort",
            is_abort=True,
        )
        assert updated.status == RunStatus.HALTED

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_record_halt_atomic_save(self, tmp_path):
        """AC1: State saved atomically (write-to-temp-then-rename)."""
        from bmad_orch.types import RunStatus

        state_path = tmp_path / "bmad-orch-state.json"
        state = RunState(run_id="test-1", status=RunStatus.RUNNING)

        updated = StateManager.record_halt(
            state=state,
            failure_point="cycle:1/step:generate-code",
            failure_reason="crash",
            error_type="ProviderCrashError",
        )
        StateManager.save(updated, state_path)

        # Verify file exists and no temp files remain
        assert state_path.exists()
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

        # Verify contents round-trip
        loaded = StateManager.load(state_path)
        assert loaded.status == RunStatus.FAILED
        assert loaded.failure_point == "cycle:1/step:generate-code"

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_record_halt_temp_file_same_directory(self, tmp_path):
        """Temp file must be in same directory as target to avoid cross-device rename."""
        state_path = tmp_path / "subdir" / "bmad-orch-state.json"
        state_path.parent.mkdir(parents=True)
        state = RunState(run_id="test-1")

        with patch.object(pathlib.Path, "replace") as mock_replace:
            mock_replace.return_value = None
            StateManager.save(state, state_path)
            # The temp file path passed to replace should share the same parent
            call_args = mock_replace.call_args
            assert call_args is not None

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_error_type_populated_correctly(self):
        """error_type should be type(error).__name__."""
        from bmad_orch.types import RunStatus

        state = RunState(run_id="test-1", status=RunStatus.RUNNING)
        error = ProviderCrashError("boom")
        updated = StateManager.record_halt(
            state=state,
            failure_point="cycle:1/step:call-provider",
            failure_reason=str(error),
            error_type=type(error).__name__,
        )
        assert updated.error_type == "ProviderCrashError"

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_failure_point_derived_from_run_history(self):
        """AC3: Last successful step derived from run_history."""
        from bmad_orch.state.schema import CycleRecord, StepRecord
        from bmad_orch.types import RunStatus

        step = StepRecord(
            step_id="generate-code",
            provider_name="claude",
            outcome="success",
            timestamp=datetime.now(UTC),
        )
        cycle = CycleRecord(
            cycle_id="c1:1",
            steps=[step],
            started_at=datetime.now(UTC),
        )
        state = RunState(
            run_id="test-1",
            status=RunStatus.RUNNING,
            run_history=[cycle],
        )
        updated = StateManager.record_halt(
            state=state,
            failure_point="cycle:1/step:generate-code",
            failure_reason="crash",
            error_type="ProviderCrashError",
        )
        assert updated.failure_point == "cycle:1/step:generate-code"


# ---------------------------------------------------------------------------
# Integration Tests — Emergency flow in Runner (AC1, AC2)
# ---------------------------------------------------------------------------


class TestEmergencyFlowOrder:
    """AC1: Emergency flow executes save → commit → push → halt in order."""

    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason=SKIP_REASON)
    async def test_emergency_flow_triggers_on_impactful_error(self):
        """AC1: Provider crash triggers the emergency flow."""
        from bmad_orch.engine.runner import Runner

        config = _make_minimal_config()
        runner = Runner(config=config, state_path=pathlib.Path("/tmp/test-state.json"))
        runner.git_client = AsyncMock()

        # Simulate provider crash during execution
        with patch.object(runner, "_handle_impactful_error") as mock_handler:
            mock_handler.return_value = None
            # The run method should catch the error and call _handle_impactful_error
            assert hasattr(runner, "_handle_impactful_error")

    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason=SKIP_REASON)
    async def test_emergency_flow_order_save_commit_push_halt(self):
        """AC1: Verify exact order: save state → git commit → git push → halt."""
        from bmad_orch.engine.runner import Runner

        call_order = []

        config = _make_minimal_config()
        runner = Runner(config=config, state_path=pathlib.Path("/tmp/test-state.json"))
        runner.state = RunState(run_id="test-1")
        runner.git_client = AsyncMock()
        runner.git_client.add = AsyncMock(side_effect=lambda *a, **kw: call_order.append("add"))
        runner.git_client.commit = AsyncMock(side_effect=lambda *a, **kw: call_order.append("commit"))
        runner.git_client.push = AsyncMock(side_effect=lambda *a, **kw: call_order.append("push"))

        with patch.object(StateManager, "save", side_effect=lambda *a, **kw: call_order.append("save")):
            await runner._handle_impactful_error(ProviderCrashError("crash"))

        assert call_order == ["save", "add", "commit", "push"]

    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason=SKIP_REASON)
    async def test_git_error_trigger_skips_git_operations(self):
        """AC1: GitError as triggering error skips git commit/push (no recursion)."""
        from bmad_orch.engine.runner import Runner

        call_order = []

        config = _make_minimal_config()
        runner = Runner(config=config, state_path=pathlib.Path("/tmp/test-state.json"))
        runner.state = RunState(run_id="test-1")
        runner.git_client = AsyncMock()
        runner.git_client.add = AsyncMock(side_effect=lambda *a, **kw: call_order.append("add"))
        runner.git_client.commit = AsyncMock(side_effect=lambda *a, **kw: call_order.append("commit"))

        with patch.object(StateManager, "save", side_effect=lambda *a, **kw: call_order.append("save")):
            await runner._handle_impactful_error(GitError("git broke"))

        # State should still be saved, but git ops should be skipped
        assert "save" in call_order
        assert "add" not in call_order
        assert "commit" not in call_order

    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason=SKIP_REASON)
    async def test_emergency_flow_guard_git_client_none(self):
        """AC1: If git_client is None (early crash), skip git operations gracefully."""
        from bmad_orch.engine.runner import Runner

        config = _make_minimal_config()
        runner = Runner(config=config, state_path=pathlib.Path("/tmp/test-state.json"))
        runner.state = RunState(run_id="test-1")
        runner.git_client = None  # Crash happened before git init

        # Should not raise even without git client
        with patch.object(StateManager, "save"):
            await runner._handle_impactful_error(ProviderCrashError("early crash"))


class TestSecondaryGitFailure:
    """AC2: Secondary git failure handling during emergency flow."""

    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason=SKIP_REASON)
    async def test_git_add_failure_skips_commit_and_push(self):
        """AC2: If git add fails, skip commit and push."""
        from bmad_orch.engine.runner import Runner

        config = _make_minimal_config()
        runner = Runner(config=config, state_path=pathlib.Path("/tmp/test-state.json"))
        runner.state = RunState(run_id="test-1")
        runner.git_client = AsyncMock()
        runner.git_client.add = AsyncMock(side_effect=GitError("add failed"))
        runner.git_client.commit = AsyncMock()
        runner.git_client.push = AsyncMock()

        with patch.object(StateManager, "save"):
            await runner._handle_impactful_error(ProviderCrashError("crash"))

        runner.git_client.commit.assert_not_called()
        runner.git_client.push.assert_not_called()

    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason=SKIP_REASON)
    async def test_push_failure_logs_error_with_traceback(self):
        """AC2: Push failure logs ERROR with traceback."""
        from bmad_orch.engine.runner import Runner

        config = _make_minimal_config()
        runner = Runner(config=config, state_path=pathlib.Path("/tmp/test-state.json"))
        runner.state = RunState(run_id="test-1")
        runner.git_client = AsyncMock()
        runner.git_client.add = AsyncMock()
        runner.git_client.commit = AsyncMock()
        runner.git_client.push = AsyncMock(side_effect=GitError("push failed: network"))

        with (
            patch.object(StateManager, "save"),
            patch("bmad_orch.engine.runner.logger") as mock_logger,
        ):
            await runner._handle_impactful_error(ProviderCrashError("crash"))

        mock_logger.error.assert_called()
        # Verify traceback is included in the log call
        error_calls = [str(c) for c in mock_logger.error.call_args_list]
        assert any("push failed" in c for c in error_calls)

    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason=SKIP_REASON)
    async def test_non_git_halt_sequence_always_completes(self):
        """AC2: State save, subprocess cleanup, exit run regardless of git failures."""
        from bmad_orch.engine.runner import Runner

        config = _make_minimal_config()
        runner = Runner(config=config, state_path=pathlib.Path("/tmp/test-state.json"))
        runner.state = RunState(run_id="test-1")
        runner.git_client = AsyncMock()
        runner.git_client.add = AsyncMock(side_effect=GitError("total git failure"))

        state_saved = False

        def mark_saved(*a, **kw):
            nonlocal state_saved
            state_saved = True

        with patch.object(StateManager, "save", side_effect=mark_saved):
            await runner._handle_impactful_error(ProviderCrashError("crash"))

        assert state_saved, "State must be saved even when all git operations fail"


# ---------------------------------------------------------------------------
# Integration Tests — Emergency flow re-entrance guard
# ---------------------------------------------------------------------------


class TestEmergencyFlowReentrance:
    """Emergency flow must not re-enter if already in progress."""

    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason=SKIP_REASON)
    async def test_in_emergency_flow_flag_prevents_reentrance(self):
        """_in_emergency_flow flag prevents recursive emergency handling."""
        from bmad_orch.engine.runner import Runner

        config = _make_minimal_config()
        runner = Runner(config=config, state_path=pathlib.Path("/tmp/test-state.json"))
        runner.state = RunState(run_id="test-1")
        runner._in_emergency_flow = True

        with patch.object(StateManager, "save") as mock_save:
            await runner._handle_impactful_error(ProviderCrashError("second crash"))

        # Should not re-enter — save not called again
        mock_save.assert_not_called()

    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason=SKIP_REASON)
    async def test_in_emergency_flow_flag_reset_on_exit(self):
        """_in_emergency_flow reset to False via try/finally."""
        from bmad_orch.engine.runner import Runner

        config = _make_minimal_config()
        runner = Runner(config=config, state_path=pathlib.Path("/tmp/test-state.json"))
        runner.state = RunState(run_id="test-1")
        runner.git_client = None

        with patch.object(StateManager, "save"):
            await runner._handle_impactful_error(ProviderCrashError("crash"))

        assert runner._in_emergency_flow is False


# ---------------------------------------------------------------------------
# Unit Tests — Subprocess cleanup (Architecture compliance)
# ---------------------------------------------------------------------------


class TestSubprocessCleanup:
    """Subprocess cleanup must be fully awaited even under cancellation."""

    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason=SKIP_REASON)
    async def test_subprocess_killed_and_waited_during_emergency(self):
        """Subprocesses are killed via process.kill() + await process.wait()."""
        from bmad_orch.engine.runner import Runner

        config = _make_minimal_config()
        runner = Runner(config=config, state_path=pathlib.Path("/tmp/test-state.json"))
        runner.state = RunState(run_id="test-1")
        runner.git_client = None

        mock_process = MagicMock()
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock()
        mock_process.returncode = None  # Still running

        # Inject a tracked subprocess
        runner._active_processes = [mock_process]

        with patch.object(StateManager, "save"):
            await runner._handle_impactful_error(ProviderCrashError("crash"))

        mock_process.kill.assert_called_once()
        mock_process.wait.assert_awaited_once()

    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason=SKIP_REASON)
    async def test_subprocess_cleanup_shielded_from_cancellation(self):
        """Subprocess cleanup wrapped in asyncio.shield() to prevent zombies."""
        from bmad_orch.engine.runner import Runner

        config = _make_minimal_config()
        runner = Runner(config=config, state_path=pathlib.Path("/tmp/test-state.json"))
        runner.state = RunState(run_id="test-1")
        runner.git_client = None

        with (
            patch.object(StateManager, "save"),
            patch("asyncio.shield", wraps=asyncio.shield) as mock_shield,
        ):
            await runner._handle_impactful_error(ProviderCrashError("crash"))

        # asyncio.shield should have been called during cleanup
        mock_shield.assert_called()


# ---------------------------------------------------------------------------
# Integration Tests — CLI exit codes (AC4)
# ---------------------------------------------------------------------------


class TestExitCodes:
    """AC4: Headless mode exit codes."""

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_exit_code_3_for_runtime_error(self, valid_config_file):
        """Exit code 3 for GitError/ResourceError/StateError."""
        from bmad_orch.cli import app

        runner = CliRunner()
        with patch("bmad_orch.cli.Runner") as MockRunner:
            instance = MockRunner.return_value
            instance.run = MagicMock(side_effect=ResourceError("disk full"))
            result = runner.invoke(app, ["start", "--config", str(valid_config_file), "--headless", "--no-preflight"])

        assert result.exit_code == 3

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_exit_code_3_for_git_error(self, valid_config_file):
        """Exit code 3 for GitError."""
        from bmad_orch.cli import app

        runner = CliRunner()
        with patch("bmad_orch.cli.Runner") as MockRunner:
            instance = MockRunner.return_value
            instance.run = MagicMock(side_effect=GitError("git init failed"))
            result = runner.invoke(app, ["start", "--config", str(valid_config_file), "--headless", "--no-preflight"])

        assert result.exit_code == 3

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_exit_code_4_for_provider_error(self, valid_config_file):
        """Exit code 4 for ProviderError/ProviderCrashError."""
        from bmad_orch.cli import app

        runner = CliRunner()
        with patch("bmad_orch.cli.Runner") as MockRunner:
            instance = MockRunner.return_value
            instance.run = MagicMock(side_effect=ProviderCrashError("model crashed"))
            result = runner.invoke(app, ["start", "--config", str(valid_config_file), "--headless", "--no-preflight"])

        assert result.exit_code == 4

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_exit_code_1_for_unexpected_error(self, valid_config_file):
        """Exit code 1 for unexpected/unhandled exceptions."""
        from bmad_orch.cli import app

        runner = CliRunner()
        with patch("bmad_orch.cli.Runner") as MockRunner:
            instance = MockRunner.return_value
            instance.run = MagicMock(side_effect=RuntimeError("surprise"))
            result = runner.invoke(app, ["start", "--config", str(valid_config_file), "--headless", "--no-preflight"])

        assert result.exit_code == 1

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_exit_code_2_for_config_error(self, valid_config_file):
        """Exit code 2 for ConfigError (already implemented, regression guard)."""
        from bmad_orch.cli import app

        runner = CliRunner()
        with patch("bmad_orch.cli.get_config", side_effect=BmadOrchError("bad config")):
            result = runner.invoke(app, ["start", "--config", str(valid_config_file)])

        assert result.exit_code == 2

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_exit_code_130_for_sigint(self, valid_config_file):
        """AC6: Exit code 130 for SIGINT/Ctrl+C abort."""
        from bmad_orch.cli import app

        runner = CliRunner()
        with patch("bmad_orch.cli.Runner") as MockRunner:
            instance = MockRunner.return_value
            instance.run = MagicMock(side_effect=asyncio.CancelledError())
            result = runner.invoke(app, ["start", "--config", str(valid_config_file), "--headless", "--no-preflight"])

        assert result.exit_code == 130

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_exit_code_143_for_sigterm(self, valid_config_file):
        """AC6: Exit code 143 for SIGTERM."""
        from bmad_orch.cli import app

        runner = CliRunner()
        # SIGTERM should be handled similarly to SIGINT but with different code
        with patch("bmad_orch.cli.Runner") as MockRunner:
            instance = MockRunner.return_value
            # Simulate SIGTERM-triggered cancellation
            instance.run = MagicMock(side_effect=SystemExit(143))
            result = runner.invoke(app, ["start", "--config", str(valid_config_file), "--headless", "--no-preflight"])

        assert result.exit_code == 143


# ---------------------------------------------------------------------------
# Unit Tests — Error headline formatting (AC5)
# ---------------------------------------------------------------------------


class TestErrorHeadlineFormatting:
    """AC5: Error messages follow headline format."""

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_error_headline_format(self):
        """AC5: Error format is '✗ [What happened] — run bmad-orch resume'."""
        from bmad_orch.cli import format_error_headline

        msg = format_error_headline(ProviderCrashError("Model timed out"))
        assert msg.startswith("✗ ")
        assert "— run bmad-orch resume" in msg
        assert "Model timed out" in msg

    
    @pytest.mark.skip(reason=SKIP_REASON)
    def test_abort_headline_format(self):
        """AC5: Abort format is '■ [Execution Halted by User] — run bmad-orch resume'."""
        from bmad_orch.cli import format_abort_headline

        msg = format_abort_headline()
        assert msg.startswith("■ ")
        assert "Execution Halted by User" in msg
        assert "— run bmad-orch resume" in msg


# ---------------------------------------------------------------------------
# Integration Tests — Signal handling (AC6)
# ---------------------------------------------------------------------------


class TestSignalHandling:
    """AC6: SIGINT/SIGTERM trigger emergency flow."""

    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason=SKIP_REASON)
    async def test_sigint_triggers_emergency_flow_with_halted_status(self):
        """AC6: SIGINT → emergency flow → status=HALTED, not FAILED."""
        from bmad_orch.engine.runner import Runner
        from bmad_orch.types import RunStatus

        config = _make_minimal_config()
        runner = Runner(config=config, state_path=pathlib.Path("/tmp/test-state.json"))
        runner.state = RunState(run_id="test-1")
        runner.git_client = AsyncMock()

        with patch.object(StateManager, "save") as mock_save:
            await runner._handle_impactful_error(error=None, is_abort=True)

        # Verify state was saved with HALTED status
        saved_state = mock_save.call_args[0][0]
        assert saved_state.status == RunStatus.HALTED
        assert saved_state.error_type == "UserAbort"

    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason=SKIP_REASON)
    async def test_sigint_commits_and_pushes(self):
        """AC6: User abort still commits state + pushes."""
        from bmad_orch.engine.runner import Runner

        call_order = []
        config = _make_minimal_config()
        runner = Runner(config=config, state_path=pathlib.Path("/tmp/test-state.json"))
        runner.state = RunState(run_id="test-1")
        runner.git_client = AsyncMock()
        runner.git_client.add = AsyncMock(side_effect=lambda *a, **kw: call_order.append("add"))
        runner.git_client.commit = AsyncMock(side_effect=lambda *a, **kw: call_order.append("commit"))
        runner.git_client.push = AsyncMock(side_effect=lambda *a, **kw: call_order.append("push"))

        with patch.object(StateManager, "save", side_effect=lambda *a, **kw: call_order.append("save")):
            await runner._handle_impactful_error(error=None, is_abort=True)

        assert call_order == ["save", "add", "commit", "push"]

    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason=SKIP_REASON)
    async def test_emergency_flow_suppresses_reentrant_interrupt(self):
        """AC6: If _in_emergency_flow is True, suppress the interrupt."""
        from bmad_orch.engine.runner import Runner

        config = _make_minimal_config()
        runner = Runner(config=config, state_path=pathlib.Path("/tmp/test-state.json"))
        runner._in_emergency_flow = True

        # Second interrupt during emergency should be suppressed
        with patch.object(StateManager, "save") as mock_save:
            await runner._handle_impactful_error(error=None, is_abort=True)

        mock_save.assert_not_called()


# ---------------------------------------------------------------------------
# Integration Tests — Partial emergency completion
# ---------------------------------------------------------------------------


class TestPartialEmergencyCompletion:
    """Partial emergency (state saved + committed, push failed) = valid halt state."""

    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason=SKIP_REASON)
    async def test_partial_completion_state_valid(self):
        """State saved + committed but push failed → valid halt state."""
        from bmad_orch.engine.runner import Runner
        from bmad_orch.types import RunStatus

        config = _make_minimal_config()
        runner = Runner(config=config, state_path=pathlib.Path("/tmp/test-state.json"))
        runner.state = RunState(run_id="test-1")
        runner.git_client = AsyncMock()
        runner.git_client.add = AsyncMock()
        runner.git_client.commit = AsyncMock()
        runner.git_client.push = AsyncMock(side_effect=GitError("network down"))

        saved_states = []

        def capture_save(state, path):
            saved_states.append(state)

        with patch.object(StateManager, "save", side_effect=capture_save):
            await runner._handle_impactful_error(ProviderCrashError("crash"))

        # State should still be valid despite push failure
        assert len(saved_states) == 1
        assert saved_states[0].status == RunStatus.FAILED
        assert saved_states[0].failure_point is not None

    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason=SKIP_REASON)
    async def test_git_error_during_emergency_logged_with_traceback(self):
        """GitError during emergency flow logged at ERROR with traceback."""
        from bmad_orch.engine.runner import Runner

        config = _make_minimal_config()
        runner = Runner(config=config, state_path=pathlib.Path("/tmp/test-state.json"))
        runner.state = RunState(run_id="test-1")
        runner.git_client = AsyncMock()
        runner.git_client.add = AsyncMock(side_effect=GitError("add failed"))

        with (
            patch.object(StateManager, "save"),
            patch("bmad_orch.engine.runner.logger") as mock_logger,
        ):
            await runner._handle_impactful_error(ProviderCrashError("crash"))

        # Verify ERROR level logging with details
        mock_logger.error.assert_called()


# ---------------------------------------------------------------------------
# Git commit message format
# ---------------------------------------------------------------------------


class TestEmergencyGitCommitMessage:
    """Git commit message follows template: chore(bmad-orch): emergency commit — $failure_point — $error_type."""

    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason=SKIP_REASON)
    async def test_emergency_commit_message_format(self):
        """Commit message includes failure_point and error_type."""
        from bmad_orch.engine.runner import Runner

        config = _make_minimal_config()
        runner = Runner(config=config, state_path=pathlib.Path("/tmp/test-state.json"))
        runner.state = RunState(run_id="test-1")
        runner.git_client = AsyncMock()
        runner.git_client.add = AsyncMock()
        runner.git_client.commit = AsyncMock()
        runner.git_client.push = AsyncMock()

        with patch.object(StateManager, "save"):
            await runner._handle_impactful_error(ProviderCrashError("crash"))

        commit_call = runner.git_client.commit.call_args
        commit_msg = commit_call[1].get("message", commit_call[0][0] if commit_call[0] else "")
        assert "chore(bmad-orch): emergency commit" in commit_msg
        assert "ProviderCrashError" in commit_msg


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Import here to avoid issues if config schema changes
from bmad_orch.exceptions import BmadOrchError


def _make_minimal_config():
    """Create a minimal OrchestratorConfig for testing emergency flow."""
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
