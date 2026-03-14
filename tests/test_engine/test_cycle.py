import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch, call
from datetime import datetime, timezone
from pathlib import Path

from bmad_orch.engine.cycle import CycleExecutor
from bmad_orch.config.schema import CycleConfig, StepConfig, OrchestratorConfig
from bmad_orch.state.schema import RunState, CycleRecord, StepRecord
from bmad_orch.types import StepType, StepOutcome
from bmad_orch.engine.events import (
    CycleStarted, CycleCompleted, StepStarted, StepCompleted, ErrorOccurred
)
from bmad_orch.exceptions import ConfigError

@pytest.fixture
def mock_emitter():
    return MagicMock()

@pytest.fixture
def mock_state_manager():
    sm = MagicMock()
    # Mock state updates properly
    def mock_start_cycle(state, cycle_id, started_at=None):
        new_cycle = CycleRecord(cycle_id=cycle_id, started_at=started_at or datetime.now(timezone.utc))
        return state.model_copy(update={"run_history": list(state.run_history) + [new_cycle]})
    
    def mock_record_step(state, cycle_id, step_record):
        new_history = []
        for cycle in state.run_history:
            if cycle.cycle_id == cycle_id:
                new_history.append(cycle.model_copy(update={"steps": list(cycle.steps) + [step_record]}))
            else:
                new_history.append(cycle)
        return state.model_copy(update={"run_history": new_history})

    def mock_finish_cycle(state, cycle_id, outcome, finished_at=None):
        new_history = []
        for cycle in state.run_history:
            if cycle.cycle_id == cycle_id:
                new_history.append(cycle.model_copy(update={"outcome": outcome, "finished_at": finished_at or datetime.now(timezone.utc)}))
            else:
                new_history.append(cycle)
        return state.model_copy(update={"run_history": new_history})

    sm.start_cycle.side_effect = mock_start_cycle
    sm.record_step.side_effect = mock_record_step
    sm.finish_cycle.side_effect = mock_finish_cycle
    return sm

@pytest.fixture
def mock_resolver():
    resolver = MagicMock()
    resolver.resolve.side_effect = lambda prompt, context, **kwargs: prompt
    return resolver

@pytest.fixture
def config():
    return OrchestratorConfig(
        providers={1: {"name": "test-provider", "cli": "test", "model": "test"}},
        cycles={
            "test-cycle": CycleConfig(
                steps=[
                    StepConfig(skill="test-skill", provider=1, type=StepType.GENERATIVE, prompt="test-prompt")
                ],
                repeat=1
            )
        },
        git={"commit_at": "step", "push_at": "end"},
        pauses={"between_steps": 0, "between_cycles": 0, "between_workflows": 0},
        error_handling={"retry_transient": True, "max_retries": 3, "retry_delay": 0}
    )

@pytest.fixture
def initial_state():
    return RunState(run_id="test-run", run_history=[])

@pytest.mark.asyncio
async def test_execute_cycle_basic(mock_emitter, mock_state_manager, mock_resolver, config, initial_state):
    executor = CycleExecutor(mock_emitter, mock_state_manager, mock_resolver, config, Path("state.json"))
    executor._execute_step = AsyncMock(return_value=(True, "OK"))
    
    cycle_config = config.cycles["test-cycle"]
    final_state = await executor.execute_cycle("test-cycle", cycle_config, initial_state, {"var": "val"})
    
    assert len(final_state.run_history) == 1
    assert len(final_state.run_history[0].steps) == 1
    assert final_state.run_history[0].steps[0].outcome == "success"
    
    # Verify events
    calls = [c[0][0] for c in mock_emitter.emit.call_args_list]
    assert any(isinstance(c, CycleStarted) for c in calls)
    assert any(isinstance(c, StepStarted) for c in calls)
    assert any(isinstance(c, StepCompleted) for c in calls)
    assert any(isinstance(c, CycleCompleted) for c in calls)

@pytest.mark.asyncio
async def test_execute_cycle_step_type_logic(mock_emitter, mock_state_manager, mock_resolver, config, initial_state):
    # Update config for multiple repetitions
    config.cycles["test-cycle"] = CycleConfig(
        steps=[
            StepConfig(skill="gen", provider=1, type=StepType.GENERATIVE, prompt="gen"),
            StepConfig(skill="val", provider=1, type=StepType.VALIDATION, prompt="val"),
        ],
        repeat=2
    )
    
    executor = CycleExecutor(mock_emitter, mock_state_manager, mock_resolver, config, Path("state.json"))
    executor._execute_step = AsyncMock(return_value=(True, "OK"))
    
    final_state = await executor.execute_cycle("test-cycle", config.cycles["test-cycle"], initial_state, {})
    
    # Iteration 1: gen, val
    # Iteration 2: val
    # Total steps should be 3 across 2 CycleRecords
    assert len(final_state.run_history) == 2
    assert len(final_state.run_history[0].steps) == 2
    assert len(final_state.run_history[1].steps) == 1
    assert final_state.run_history[1].steps[0].step_id == "val_1"

@pytest.mark.asyncio
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_execute_cycle_pauses(mock_sleep, mock_emitter, mock_state_manager, mock_resolver, config, initial_state):
    config.cycles["test-cycle"] = CycleConfig(
        steps=[
            StepConfig(skill="s1", provider=1, type=StepType.VALIDATION, prompt="p1"),
            StepConfig(skill="s2", provider=1, type=StepType.VALIDATION, prompt="p2"),
        ],
        repeat=2,
        pause_between_steps=1.5,
        pause_between_cycles=2.5
    )
    
    executor = CycleExecutor(mock_emitter, mock_state_manager, mock_resolver, config, Path("state.json"))
    executor._execute_step = AsyncMock(return_value=(True, "OK"))
    
    await executor.execute_cycle("test-cycle", config.cycles["test-cycle"], initial_state, {})
    
    assert mock_sleep.call_count == 3
    mock_sleep.assert_has_calls([
        call(1.5),
        call(2.5),
        call(1.5)
    ])

@pytest.mark.asyncio
async def test_execute_cycle_step_failure(mock_emitter, mock_state_manager, mock_resolver, config, initial_state):
    executor = CycleExecutor(mock_emitter, mock_state_manager, mock_resolver, config, Path("state.json"))
    # Mock failure
    executor._execute_step = AsyncMock(return_value=(False, "Failed"))

    final_state = await executor.execute_cycle("test-cycle", config.cycles["test-cycle"], initial_state, {})

    assert len(final_state.run_history) == 1
    assert final_state.run_history[0].steps[0].outcome == "failure"
    assert final_state.run_history[0].outcome == "failure"

    # AC10: Must emit ErrorOccurred AND CycleCompleted(success=False)
    calls = [c[0][0] for c in mock_emitter.emit.call_args_list]
    assert any(isinstance(c, ErrorOccurred) for c in calls), "AC10: ErrorOccurred must be emitted on step failure"
    assert any(isinstance(c, CycleCompleted) and c.success is False for c in calls)

@pytest.mark.asyncio
async def test_execute_cycle_template_failure(mock_emitter, mock_state_manager, mock_resolver, config, initial_state):
    mock_resolver.resolve.side_effect = ConfigError("Template error")
    executor = CycleExecutor(mock_emitter, mock_state_manager, mock_resolver, config, Path("state.json"))
    
    final_state = await executor.execute_cycle("test-cycle", config.cycles["test-cycle"], initial_state, {})
    
    assert final_state.run_history[0].steps[0].outcome == "failure"
    assert final_state.run_history[0].outcome == "failure"
    
    calls = [c[0][0] for c in mock_emitter.emit.call_args_list]
    assert any(isinstance(c, ErrorOccurred) and "Template error" in c.message for c in calls)
    assert any(isinstance(c, CycleCompleted) and c.success is False for c in calls)

@pytest.mark.asyncio
@patch("bmad_orch.engine.cycle.unbind_contextvars")
@patch("bmad_orch.engine.cycle.bind_contextvars")
async def test_execute_cycle_logging_context(mock_bind, mock_unbind, mock_emitter, mock_state_manager, mock_resolver, config, initial_state):
    executor = CycleExecutor(mock_emitter, mock_state_manager, mock_resolver, config, Path("state.json"))
    executor._execute_step = AsyncMock(return_value=(True, "OK"))
    
    await executor.execute_cycle("test-cycle", config.cycles["test-cycle"], initial_state, {})
    
    # Verify unbind_contextvars called for steps and cycle
    mock_unbind.assert_has_calls([
        call("step_name", "provider_name"),
        call("cycle_id")
    ])
    
    # Verify bind_contextvars called
    mock_bind.assert_any_call(cycle_id="test-cycle")
    mock_bind.assert_any_call(step_name="test-skill_0", provider_name="test-provider")


@pytest.mark.asyncio
async def test_execute_cycle_empty_steps(mock_emitter, mock_state_manager, mock_resolver, config, initial_state):
    """AC11: Empty step list must emit ErrorOccurred and skip execution."""
    # Bypass pydantic validation to create a cycle with empty steps
    cycle_config = CycleConfig.model_construct(steps=[], repeat=1)

    executor = CycleExecutor(mock_emitter, mock_state_manager, mock_resolver, config, Path("state.json"))
    final_state = await executor.execute_cycle("test-cycle", cycle_config, initial_state, {})

    # State should be unchanged (no cycles executed)
    assert final_state.run_history == []

    calls = [c[0][0] for c in mock_emitter.emit.call_args_list]
    assert any(
        isinstance(c, ErrorOccurred) and c.error_type == "ConfigError" and "zero steps" in c.message
        for c in calls
    ), "AC11: ErrorOccurred must be emitted for empty step list"


@pytest.mark.asyncio
async def test_execute_cycle_repeat_zero(mock_emitter, mock_state_manager, mock_resolver, config, initial_state):
    """AC3: repeat <= 0 must emit ErrorOccurred and skip execution."""
    # Bypass pydantic validation to create a cycle with repeat=0
    cycle_config = CycleConfig.model_construct(
        steps=[StepConfig(skill="s", provider=1, type=StepType.GENERATIVE, prompt="p")],
        repeat=0,
        pause_between_steps=None,
        pause_between_cycles=None,
    )

    executor = CycleExecutor(mock_emitter, mock_state_manager, mock_resolver, config, Path("state.json"))
    final_state = await executor.execute_cycle("test-cycle", cycle_config, initial_state, {})

    assert final_state.run_history == []

    calls = [c[0][0] for c in mock_emitter.emit.call_args_list]
    assert any(
        isinstance(c, ErrorOccurred) and "repeat" in c.message.lower()
        for c in calls
    ), "AC3: ErrorOccurred must be emitted for repeat <= 0"


@pytest.mark.asyncio
async def test_execute_cycle_generative_only_repeat_gt1(mock_emitter, mock_state_manager, mock_resolver, config, initial_state):
    """AC11: Generative-only steps with repeat > 1 must emit ErrorOccurred upfront."""
    config.cycles["test-cycle"] = CycleConfig(
        steps=[
            StepConfig(skill="gen", provider=1, type=StepType.GENERATIVE, prompt="p"),
        ],
        repeat=2,
    )

    executor = CycleExecutor(mock_emitter, mock_state_manager, mock_resolver, config, Path("state.json"))
    executor._execute_step = AsyncMock(return_value=(True, "OK"))

    final_state = await executor.execute_cycle("test-cycle", config.cycles["test-cycle"], initial_state, {})

    # No cycles should have executed
    assert final_state.run_history == []

    calls = [c[0][0] for c in mock_emitter.emit.call_args_list]
    assert any(
        isinstance(c, ErrorOccurred) and c.error_type == "ConfigError" and "generative" in c.message.lower()
        for c in calls
    ), "AC11: ErrorOccurred must be emitted for generative-only + repeat > 1"


@pytest.mark.asyncio
async def test_execute_cycle_invalid_provider(mock_emitter, mock_state_manager, mock_resolver, initial_state):
    """AC12: Invalid provider key must emit ErrorOccurred and follow AC10 protocol."""
    # Provider key 99 does not exist
    bad_config = OrchestratorConfig.model_construct(
        providers={1: MagicMock(name="test-provider")},
        cycles={},
        git=None,
        pauses=None,
        error_handling=None,
    )
    cycle_config = CycleConfig.model_construct(
        steps=[StepConfig(skill="s", provider=99, type=StepType.GENERATIVE, prompt="p")],
        repeat=1,
        pause_between_steps=None,
        pause_between_cycles=None,
    )

    executor = CycleExecutor(mock_emitter, mock_state_manager, mock_resolver, bad_config, Path("state.json"))
    final_state = await executor.execute_cycle("test-cycle", cycle_config, initial_state, {})

    # AC12/AC10: Should have 1 cycle record with failure
    assert len(final_state.run_history) == 1
    assert final_state.run_history[0].outcome == "failure"

    calls = [c[0][0] for c in mock_emitter.emit.call_args_list]
    assert any(
        isinstance(c, ErrorOccurred) and c.error_type == "ConfigError" and c.source == "s_0"
        for c in calls
    ), "AC12: ErrorOccurred with source=step_name must be emitted for invalid provider"
    # AC6: CycleStarted must NOT fire when upfront validation fails
    assert not any(isinstance(c, CycleStarted) for c in calls), \
        "AC6: CycleStarted must not be emitted when provider validation fails"
    assert any(isinstance(c, CycleCompleted) and c.success is False for c in calls)


@pytest.mark.asyncio
async def test_execute_cycle_escalation_detection(mock_emitter, mock_state_manager, mock_resolver, config, initial_state):
    """AC6: Detect escalation trigger and emit event."""
    from bmad_orch.engine.events import EscalationChanged, EscalationLevel
    executor = CycleExecutor(mock_emitter, mock_state_manager, mock_resolver, config, Path("state.json"))
    executor._execute_step = AsyncMock(return_value=(True, "Some output with ESCALATE: ATTENTION included"))

    await executor.execute_cycle("test-cycle", config.cycles["test-cycle"], initial_state, {})

    calls = [c[0][0] for c in mock_emitter.emit.call_args_list]
    assert any(
        isinstance(c, EscalationChanged) and c.new_level == EscalationLevel.ATTENTION
        for c in calls
    ), "AC6: EscalationChanged must be emitted when trigger detected"


@pytest.mark.asyncio
async def test_execute_cycle_provider_missing_name(mock_emitter, mock_state_manager, mock_resolver, initial_state):
    """AC12: Provider with empty name must emit ErrorOccurred and halt."""
    empty_name_provider = MagicMock()
    empty_name_provider.name = ""
    bad_config = OrchestratorConfig.model_construct(
        providers={1: empty_name_provider},
        cycles={},
        git=None,
        pauses=None,
        error_handling=None,
    )
    cycle_config = CycleConfig.model_construct(
        steps=[StepConfig(skill="s", provider=1, type=StepType.GENERATIVE, prompt="p")],
        repeat=1,
        pause_between_steps=None,
        pause_between_cycles=None,
    )

    executor = CycleExecutor(mock_emitter, mock_state_manager, mock_resolver, bad_config, Path("state.json"))
    final_state = await executor.execute_cycle("test-cycle", cycle_config, initial_state, {})

    # AC12/AC10: Should have 1 cycle record with failure
    assert len(final_state.run_history) == 1
    assert final_state.run_history[0].outcome == "failure"

    calls = [c[0][0] for c in mock_emitter.emit.call_args_list]
    assert any(
        isinstance(c, ErrorOccurred) and c.error_type == "ConfigError"
        for c in calls
    ), "AC12: ErrorOccurred must be emitted for provider with empty name"
    # AC6: CycleStarted must NOT fire when upfront validation fails
    assert not any(isinstance(c, CycleStarted) for c in calls), \
        "AC6: CycleStarted must not be emitted when provider validation fails"


@pytest.mark.asyncio
async def test_execute_cycle_template_failure_populates_error_record(mock_emitter, mock_state_manager, mock_resolver, config, initial_state):
    """AC8: Template resolution failure must record ErrorRecord in StepRecord."""
    mock_resolver.resolve.side_effect = ConfigError("Missing var {foo}")
    executor = CycleExecutor(mock_emitter, mock_state_manager, mock_resolver, config, Path("state.json"))

    final_state = await executor.execute_cycle("test-cycle", config.cycles["test-cycle"], initial_state, {})

    step = final_state.run_history[0].steps[0]
    assert step.outcome == "failure"
    assert step.error is not None, "AC8: StepRecord.error must be populated on template failure"
    assert "Missing var" in step.error.message


@pytest.mark.asyncio
async def test_cycle_completed_uses_first_provider_name(mock_emitter, mock_state_manager, mock_resolver, initial_state):
    """AC6: CycleCompleted must use provider_name from the first step, not the last."""
    multi_provider_config = OrchestratorConfig(
        providers={
            1: {"name": "provider-one", "cli": "test", "model": "test"},
            2: {"name": "provider-two", "cli": "test", "model": "test"},
        },
        cycles={
            "multi": CycleConfig(
                steps=[
                    StepConfig(skill="s1", provider=1, type=StepType.GENERATIVE, prompt="p1"),
                    StepConfig(skill="s2", provider=2, type=StepType.VALIDATION, prompt="p2"),
                ],
                repeat=1,
            )
        },
        git={"commit_at": "step", "push_at": "end"},
        pauses={"between_steps": 0, "between_cycles": 0, "between_workflows": 0},
        error_handling={"retry_transient": True, "max_retries": 3, "retry_delay": 0},
    )

    executor = CycleExecutor(mock_emitter, mock_state_manager, mock_resolver, multi_provider_config, Path("state.json"))
    executor._execute_step = AsyncMock(return_value=(True, "OK"))

    await executor.execute_cycle("multi", multi_provider_config.cycles["multi"], initial_state, {})

    calls = [c[0][0] for c in mock_emitter.emit.call_args_list]
    cycle_completed_events = [c for c in calls if isinstance(c, CycleCompleted)]
    assert len(cycle_completed_events) == 1
    assert cycle_completed_events[0].provider_name == "provider-one", \
        "AC6: CycleCompleted must use first step's provider_name, not last"


@pytest.mark.asyncio
async def test_record_step_return_value_captured(mock_emitter, mock_state_manager, mock_resolver, config, initial_state):
    """Task 5.8: Verify record_step return value is captured (state not stale)."""
    executor = CycleExecutor(mock_emitter, mock_state_manager, mock_resolver, config, Path("state.json"))
    executor._execute_step = AsyncMock(return_value=(True, "OK"))

    final_state = await executor.execute_cycle("test-cycle", config.cycles["test-cycle"], initial_state, {})

    # record_step must have been called and its return value used
    mock_state_manager.record_step.assert_called_once()
    # The final state must contain the recorded step (proves return value was captured)
    assert len(final_state.run_history[0].steps) == 1

