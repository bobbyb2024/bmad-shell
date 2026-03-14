import pytest
import asyncio
from bmad_orch.config.schema import validate_config
from bmad_orch.engine.runner import Runner

@pytest.fixture
def valid_config():
    data = {
        "providers": {
            1: {"name": "claude", "cli": "claude", "model": "opus-4"},
        },
        "cycles": {
            "story": {
                "steps": [
                    {"skill": "s1", "provider": 1, "type": "generative", "prompt": "p1"},
                ],
                "repeat": 1,
            }
        },
        "git": {"commit_at": "cycle", "push_at": "end"},
        "pauses": {"between_steps": 5.0, "between_cycles": 15.0, "between_workflows": 30.0},
        "error_handling": {"retry_transient": True, "max_retries": 3, "retry_delay": 10.0},
    }
    return validate_config(data)

@pytest.mark.asyncio
async def test_runner_dry_run_walks_plan(valid_config):
    runner = Runner(valid_config)
    # This should complete without errors
    await runner.run(dry_run=True)

def test_runner_initialization_no_state(valid_config):
    runner = Runner(valid_config, state_path=None)
    assert runner.state_path is None
    assert runner.state is None
