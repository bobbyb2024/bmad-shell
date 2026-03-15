import pytest
from bmad_orch.config.schema import OrchestratorConfig, validate_config, ResourceConfig
from bmad_orch.exceptions import ConfigError

@pytest.fixture
def valid_config_data():
    return {
        "providers": {
            1: {"name": "claude", "cli": "claude", "model": "opus-4"},
        },
        "cycles": {
            "story": {
                "steps": [
                    {"skill": "create-story", "provider": 1, "type": "generative", "prompt": "p1"},
                ],
            }
        },
        "git": {"enabled": False},
        "pauses": {"between_steps": 0.0, "between_cycles": 0.0, "between_workflows": 0.0},
        "error_handling": {"max_retries": 1},
    }

def test_resource_config_defaults(valid_config_data):
    config = validate_config(valid_config_data)
    assert config.resources.polling_interval == 1.0
    assert config.resources.cpu_threshold == 80.0
    assert config.resources.memory_threshold == 80.0

def test_resource_config_custom_values(valid_config_data):
    valid_config_data["resources"] = {
        "polling_interval": 0.5,
        "cpu_threshold": 90.0,
        "memory_threshold": 75.0
    }
    config = validate_config(valid_config_data)
    assert config.resources.polling_interval == 0.5
    assert config.resources.cpu_threshold == 90.0
    assert config.resources.memory_threshold == 75.0

def test_resource_config_invalid_polling_interval(valid_config_data):
    valid_config_data["resources"] = {"polling_interval": 0.0}
    with pytest.raises(ConfigError) as excinfo:
        validate_config(valid_config_data)
    assert "polling_interval" in str(excinfo.value)

    valid_config_data["resources"] = {"polling_interval": -1.0}
    with pytest.raises(ConfigError) as excinfo:
        validate_config(valid_config_data)
    assert "polling_interval" in str(excinfo.value)

def test_resource_config_invalid_memory_threshold(valid_config_data):
    # Must be between 0 and 100 (exclusive)
    valid_config_data["resources"] = {"memory_threshold": 0.0}
    with pytest.raises(ConfigError) as excinfo:
        validate_config(valid_config_data)
    assert "memory_threshold" in str(excinfo.value)

    valid_config_data["resources"] = {"memory_threshold": 100.0}
    with pytest.raises(ConfigError) as excinfo:
        validate_config(valid_config_data)
    assert "memory_threshold" in str(excinfo.value)

def test_resource_config_invalid_cpu_threshold(valid_config_data):
    # Must be > 0
    valid_config_data["resources"] = {"cpu_threshold": 0.0}
    with pytest.raises(ConfigError) as excinfo:
        validate_config(valid_config_data)
    assert "cpu_threshold" in str(excinfo.value)
