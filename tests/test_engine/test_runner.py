import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bmad_orch.config.schema import validate_config
from bmad_orch.engine.events import RunCompleted
from bmad_orch.engine.runner import Runner
from bmad_orch.state.schema import CycleRecord, RunState
from bmad_orch.types import StepOutcome


@pytest.fixture
def valid_config():
    data = {
        "providers": {
            1: {"name": "claude", "cli": "claude", "model": "opus-4"},
        },
        "cycles": {
            "story": {
                "steps": [
                    {"skill": "s1", "provider": 1, "type": "validation", "prompt": "p1"},
                ],
                "repeat": 1,
            },
            "atdd": {
                "steps": [
                    {"skill": "s2", "provider": 1, "type": "validation", "prompt": "p2"},
                ],
                "repeat": 1,
            }
        },
        "git": {"commit_at": "cycle", "push_at": "end"},
        "pauses": {
            "between_steps": 5.0, "between_cycles": 15.0,
            "between_cycle_types": 10.0, "between_workflows": 30.0,
        },
        "error_handling": {"retry_transient": True, "max_retries": 3, "retry_delay": 10.0},
    }
    return validate_config(data)


@pytest.mark.asyncio
async def test_runner_dry_run_walks_plan(valid_config):
    runner = Runner(valid_config)
    await runner.run(dry_run=True)


def test_runner_initialization_no_state(valid_config):
    runner = Runner(valid_config, state_path=None)
    assert runner.state_path is None
    assert runner.state is None


@pytest.mark.asyncio
@patch("bmad_orch.engine.runner.CycleExecutor")
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_runner_multi_cycle_sequencing_and_pauses(mock_sleep, mock_executor_cls, valid_config):
    mock_executor = MagicMock()
    mock_executor_cls.return_value = mock_executor
    
    mock_state1 = RunState(run_id="test", run_history=[
        CycleRecord(cycle_id="story:1", started_at=time.time(), outcome=StepOutcome("success")),
    ])
    mock_state2 = RunState(run_id="test", run_history=mock_state1.run_history + [
        CycleRecord(cycle_id="atdd:1", started_at=time.time(), outcome=StepOutcome("success")),
    ])
    
    mock_executor = MagicMock()
    mock_executor.execute_cycle = AsyncMock(side_effect=[mock_state1, mock_state2])
    mock_executor_cls.return_value = mock_executor
    
    runner = Runner(valid_config)
    runner.emitter = MagicMock()
    await runner.run()
    
    assert mock_executor.execute_cycle.call_count == 2
    mock_sleep.assert_called_once_with(10.0)
    
    calls = [c[0][0] for c in runner.emitter.emit.call_args_list]
    run_complete_events = [c for c in calls if isinstance(c, RunCompleted)]
    assert len(run_complete_events) == 1
    event = run_complete_events[0]
    assert event.success is True
    assert event.total_cycles == 2

@pytest.mark.asyncio
@patch("bmad_orch.engine.runner.CycleExecutor")
async def test_runner_crash_resume(mock_executor_cls, valid_config):
    mock_executor = MagicMock()
    mock_executor_cls.return_value = mock_executor
    
    # State has 'story' fully complete (repeat is 1, and 1 successful rep)
    initial_state = RunState(
        run_id="test",
        run_history=[
            CycleRecord(
                cycle_id="story:1", outcome=StepOutcome("success"),
                started_at=time.time(), steps=[],
            )
        ]
    )
    
    mock_state_manager = MagicMock()
    mock_state_manager.load.return_value = initial_state
    
    runner = Runner(valid_config, state_path=Path("dummy.json"))
    runner.state_manager = mock_state_manager
    
    # return state2 for 'atdd'
    mock_state2 = initial_state.model_copy(update={"run_history": initial_state.run_history + [
        CycleRecord(cycle_id="atdd:1", started_at=time.time(), outcome=StepOutcome("success")),
    ]})
    mock_executor.execute_cycle = AsyncMock(return_value=mock_state2)
    
    await runner.run()
    
    # Should only call execute_cycle for 'atdd', skipping 'story'
    assert mock_executor.execute_cycle.call_count == 1
    # Check that it called with cycle_id="atdd"
    called_args = mock_executor.execute_cycle.call_args[0]
    assert called_args[0] == "atdd"


@pytest.mark.asyncio
@patch("bmad_orch.engine.runner.CycleExecutor")
async def test_runner_failure_halts_workflow(mock_executor_cls, valid_config):
    mock_executor = MagicMock()
    mock_executor_cls.return_value = mock_executor
    
    # 'story' fails
    mock_state1 = RunState(run_id="test", run_history=[
        CycleRecord(cycle_id="story:1", started_at=time.time(), outcome=StepOutcome("failure")),
    ])
    mock_executor.execute_cycle = AsyncMock(return_value=mock_state1)
    
    runner = Runner(valid_config)
    runner.emitter = MagicMock()
    await runner.run()
    
    # Should stop after story
    assert mock_executor.execute_cycle.call_count == 1
    
    calls = [c[0][0] for c in runner.emitter.emit.call_args_list]
    rc_event = next(c for c in calls if isinstance(c, RunCompleted))
    assert rc_event.success is False

