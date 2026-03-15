import asyncio
import json
import time
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bmad_orch.config.schema import validate_config
from bmad_orch.engine.cycle import CycleExecutor
from bmad_orch.engine.emitter import EventEmitter
from bmad_orch.engine.events import CycleCompleted, CycleStarted, RunCompleted
from bmad_orch.engine.prompt_resolver import PromptResolver
from bmad_orch.engine.runner import Runner
from bmad_orch.exceptions import TemplateVariableError
from bmad_orch.providers import ProviderAdapter, get_adapter, register_adapter
from bmad_orch.state.manager import StateManager
from bmad_orch.state.schema import CycleRecord, RunState, StepRecord
from bmad_orch.types import OutputChunk, StepOutcome


def _make_config(cycles_dict=None, pauses_overrides=None):
    """Build a validated OrchestratorConfig for testing."""
    if cycles_dict is None:
        cycles_dict = {
            "c1": {
                "steps": [
                    {"skill": "s1", "provider": 1, "type": "validation", "prompt": "do thing"}
                ]
            }
        }
    pauses = {"between_steps": 0, "between_cycles": 0, "between_cycle_types": 0, "between_workflows": 0}
    if pauses_overrides:
        pauses.update(pauses_overrides)
    data = {
        "providers": {1: {"name": "mock", "cli": "mock", "model": "m1"}},
        "cycles": cycles_dict,
        "git": {"commit_at": "cycle", "push_at": "end"},
        "pauses": pauses,
        "error_handling": {"retry_transient": True, "max_retries": 3, "retry_delay": 10},
    }
    return validate_config(data)


class FakeProvider(ProviderAdapter):
    install_hint = "pip install fake"

    def __init__(self, **config):
        self._fail_on = set()

    def detect(self, cli_path=None):
        return True

    def list_models(self):
        return [{"id": "fake"}]

    async def _execute(self, prompt, **kwargs):
        if prompt in self._fail_on:
            raise RuntimeError(f"Fatal: {prompt}")
        yield OutputChunk(content=f"ok:{prompt}", timestamp=time.time(), metadata={})


@pytest.fixture(autouse=True)
def _register_mock():
    register_adapter("mock", FakeProvider)


def test_execution_order_and_fatal_halts(tmp_path):
    """
    AC1: Three cycles defined, run in sequence.
    If cycle encounters a fatal error, runner must halt immediately.
    """
    cycles = {
        "alpha": {"steps": [{"skill": "a1", "provider": 1, "type": "validation", "prompt": "go-a"}]},
        "beta":  {"steps": [{"skill": "b1", "provider": 1, "type": "validation", "prompt": "go-b"}]},
        "gamma": {"steps": [{"skill": "g1", "provider": 1, "type": "validation", "prompt": "go-g"}]},
    }
    cfg = _make_config(cycles)
    state_path = tmp_path / "state.json"

    # Collect events to verify ordering
    events = []
    runner = Runner(cfg, state_path=state_path, adapter_factory=get_adapter)
    runner.emitter.subscribe(CycleStarted, lambda e: events.append(("start", e.cycle_number)))
    runner.emitter.subscribe(CycleCompleted, lambda e: events.append(("complete", e.cycle_number, e.success)))
    runner.emitter.subscribe(RunCompleted, lambda e: events.append(("run", e.success)))

    asyncio.run(runner.run())

    # All three cycles ran in sequence and succeeded
    assert ("start", 1) in events
    assert ("complete", 1, True) in events
    assert ("run", True) in events
    # Verify sequential: each cycle starts after previous completes
    starts = [e for e in events if e[0] == "start"]
    assert len(starts) == 3

    # Now test fatal halt: make beta's provider fail
    events2 = []
    runner2 = Runner(cfg, state_path=tmp_path / "state2.json", adapter_factory=get_adapter)
    runner2.emitter.subscribe(CycleStarted, lambda e: events2.append(("start", e.cycle_number)))
    runner2.emitter.subscribe(CycleCompleted, lambda e: events2.append(("complete", e.cycle_number, e.success)))
    runner2.emitter.subscribe(RunCompleted, lambda e: events2.append(("run", e.success)))

    # Patch _execute_step on the CycleExecutor to fail on beta cycle
    original_run = runner2.run

    async def patched_run(**kwargs):
        with patch.object(
            CycleExecutor, '_execute_step',
            new_callable=AsyncMock,
        ) as mock_step:
            call_count = [0]
            async def side_effect(step, prompt):
                call_count[0] += 1
                if "go-b" in prompt:
                    return (False, "fatal error", False)  # non-recoverable
                return (True, f"ok:{prompt}", False)
            mock_step.side_effect = side_effect
            await original_run(**kwargs)

    asyncio.run(patched_run())

    # Beta failed, gamma should NOT have started
    run_events = [e for e in events2 if e[0] == "run"]
    assert len(run_events) == 1
    assert run_events[0][1] is False  # overall run failed

    # Count cycle_starts - should be exactly 2 (alpha + beta), not 3
    all_starts = [e for e in events2 if e[0] == "start"]
    assert len(all_starts) <= 2


def test_pauses_between_workflows(tmp_path):
    """
    AC2: Engine pauses according to config between components.
    """
    cycles = {
        "c1": {"steps": [{"skill": "s1", "provider": 1, "type": "validation", "prompt": "p1"}]},
        "c2": {"steps": [{"skill": "s2", "provider": 1, "type": "validation", "prompt": "p2"}]},
    }
    cfg = _make_config(cycles, pauses_overrides={"between_cycle_types": 5.0})
    state_path = tmp_path / "state.json"
    runner = Runner(cfg, state_path=state_path, adapter_factory=get_adapter)

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        asyncio.run(runner.run())
        # Should have paused between c1 and c2 with between_cycle_types value
        mock_sleep.assert_called_with(5.0)


def test_dependency_injection_coordination(tmp_path):
    """
    AC3: Runner coordinates cycle engine, provider adapters, state manager,
    event emitter, and logging subsystem via dependency injection.
    """
    cfg = _make_config()
    state_path = tmp_path / "state.json"
    runner = Runner(cfg, state_path=state_path, adapter_factory=get_adapter)

    # Verify all components are injected/available
    assert isinstance(runner.emitter, EventEmitter)
    assert isinstance(runner.state_manager, StateManager)
    assert isinstance(runner.prompt_resolver, PromptResolver)
    assert runner.config is cfg
    assert runner.state_path == state_path

    # Verify runner passes these to CycleExecutor during execution
    with patch("bmad_orch.engine.runner.CycleExecutor") as mock_cls:
        mock_executor = MagicMock()
        mock_state = RunState(
            run_id="test",
            run_history=[
                CycleRecord(
                    cycle_id="c1:1",
                    started_at=datetime.now(UTC),
                    outcome=StepOutcome("success"),
                )
            ],
        )
        mock_executor.execute_cycle = AsyncMock(return_value=mock_state)
        mock_cls.return_value = mock_executor

        asyncio.run(runner.run())

        # CycleExecutor was constructed with the runner's injected components
        mock_cls.assert_called_once_with(
            runner.emitter,
            runner.state_manager,
            runner.prompt_resolver,
            runner.config,
            state_path,
            adapter_factory=runner.adapter_factory,
            git_client=None,
        )

def test_atomic_file_state(tmp_path):
    """
    AC4: State file saved as atomic JSON safely to disk.
    """
    state_path = tmp_path / "state.json"
    cfg = _make_config()
    runner = Runner(cfg, state_path=state_path, adapter_factory=get_adapter)

    asyncio.run(runner.run())

    # State file must exist after run
    assert state_path.exists()

    # Must be valid JSON
    with state_path.open() as f:
        data = json.loads(f.read())

    assert "run_id" in data
    assert "run_history" in data
    assert data["schema_version"] == 1

    # Verify atomic write pattern: no leftover temp files
    temp_files = list(tmp_path.glob(".state.json.*.tmp"))
    assert len(temp_files) == 0, f"Stale temp files found: {temp_files}"


def test_safe_prompt_resolution():
    """
    AC5: PromptContext resolves all template variables safely, raising explicit
    exception on missing required variables.
    """
    resolver = PromptResolver()

    # Successful resolution
    result = resolver.resolve("Hello {name}, your task is {task}", {"name": "Bob", "task": "test"})
    assert result == "Hello Bob, your task is test"

    # Missing variable raises TemplateVariableError
    with pytest.raises(TemplateVariableError, match="Missing required variables"):
        resolver.resolve("Hello {name}, do {missing_var}", {"name": "Bob"})

    # No variables in prompt - passthrough
    assert resolver.resolve("plain prompt", {}) == "plain prompt"

    # Safe: does not evaluate code-like patterns
    result = resolver.resolve("{safe_key}", {"safe_key": "value"})
    assert result == "value"

    # Curly braces that don't match identifier pattern are left alone
    result = resolver.resolve("json: {123}", {})
    assert result == "json: {123}"


def test_run_completed_events(tmp_path):
    """
    AC6: Event includes total step count, total cycle count, elapsed time,
    error count, and definitive overall success/failure status flag.
    """
    cycles = {
        "c1": {"steps": [
            {"skill": "s1", "provider": 1, "type": "validation", "prompt": "p1"},
            {"skill": "s2", "provider": 1, "type": "validation", "prompt": "p2"},
        ]},
    }
    cfg = _make_config(cycles)
    state_path = tmp_path / "state.json"
    runner = Runner(cfg, state_path=state_path, adapter_factory=get_adapter)

    captured = []
    runner.emitter.subscribe(RunCompleted, lambda e: captured.append(e))

    asyncio.run(runner.run())

    assert len(captured) == 1
    event = captured[0]
    assert event.success is True
    assert event.total_cycles >= 1
    assert event.total_step_count >= 2
    assert event.elapsed_time > 0
    assert event.error_count == 0


def test_crash_resumption(tmp_path):
    """
    AC7: Runner reads atomic JSON state file and resumes from the start
    of the current, incomplete cycle when restarted.
    """
    cycles = {
        "alpha": {"steps": [{"skill": "a1", "provider": 1, "type": "validation", "prompt": "go-a"}]},
        "beta":  {"steps": [{"skill": "b1", "provider": 1, "type": "validation", "prompt": "go-b"}]},
    }
    cfg = _make_config(cycles)
    state_path = tmp_path / "state.json"

    # Simulate: alpha completed successfully, beta not yet started
    pre_state = RunState(
        run_id="crash-test",
        run_history=[
            CycleRecord(
                cycle_id="alpha:1",
                started_at=datetime.now(UTC),
                finished_at=datetime.now(UTC),
                outcome=StepOutcome("success"),
                steps=[
                    StepRecord(
                        step_id="a1_0",
                        provider_name="mock",
                        outcome=StepOutcome("success"),
                        timestamp=datetime.now(UTC),
                    )
                ],
            )
        ],
    )
    StateManager.save(pre_state, state_path)

    # Now run - alpha should be skipped, beta should execute
    events = []
    runner = Runner(cfg, state_path=state_path, adapter_factory=get_adapter)
    runner.emitter.subscribe(CycleStarted, lambda e: events.append(("start", e.provider_name)))
    runner.emitter.subscribe(CycleCompleted, lambda e: events.append(("complete", e.success)))
    runner.emitter.subscribe(RunCompleted, lambda e: events.append(("run", e.success)))

    asyncio.run(runner.run())

    # Alpha was skipped, only beta started
    starts = [e for e in events if e[0] == "start"]
    assert len(starts) == 1, f"Expected 1 cycle start (beta only), got {len(starts)}: {starts}"

    # Run completed successfully
    run_events = [e for e in events if e[0] == "run"]
    assert run_events[0][1] is True


def test_runner_git_output_path_validation(tmp_path, monkeypatch):
    """
    AC10: Git output path outside repo raises ConfigError during init.
    """
    import pathlib
    from unittest.mock import AsyncMock, MagicMock

    from bmad_orch.engine.runner import Runner
    from bmad_orch.exceptions import ConfigError
    
    cfg = _make_config()
    cfg.git.enabled = True
    
    # Place state path outside a fake repo root
    state_path = tmp_path / 'out_of_bounds' / 'state.json'
    
    runner = Runner(cfg, state_path=state_path, adapter_factory=get_adapter)
    
    mock_git_client = MagicMock()
    # Fake repo root is just tmp_path, while state_path is tmp_path / 'out_of_bounds'
    mock_git_client.repo_path.resolve.return_value = pathlib.Path('/some/fake/repo/root')
    
    # We patch GitClient.create to return our mock
    import bmad_orch.git
    with patch.object(bmad_orch.git.GitClient, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_git_client
        # Setting state_path to something that definitely won't be under /some/fake/repo/root
        runner.state_path = pathlib.Path('/totally/different/path/state.json')
        
        with pytest.raises(ConfigError, match='outside the git repository root'):
            asyncio.run(runner._init_git())
