import pytest

from bmad_orch.config.schema import OrchestratorConfig, validate_config
from bmad_orch.exceptions import ConfigError


@pytest.fixture
def valid_config_data():
    return {
        "providers": {
            1: {"name": "claude", "cli": "claude", "model": "opus-4"},
            2: {"name": "gemini", "cli": "gemini", "model": "gemini-2.5-pro"},
        },
        "cycles": {
            "story": {
                "steps": [
                    {"skill": "create-story", "provider": 1, "type": "generative", "prompt": "p1"},
                    {"skill": "review-story", "provider": 2, "type": "validation", "prompt": "p2"},
                ],
                "repeat": 2,
                "pause_between_steps": 5.0,
                "pause_between_cycles": 15.0,
            }
        },
        "git": {"commit_at": "cycle", "push_at": "end"},
        "pauses": {"between_steps": 5.0, "between_cycles": 15.0, "between_workflows": 30.0},
        "error_handling": {"retry_transient": True, "max_retries": 3, "retry_delay": 10.0},
    }


def test_valid_config_creates_orchestrator_config(valid_config_data):
    config = validate_config(valid_config_data)
    assert isinstance(config, OrchestratorConfig)
    assert config.providers[1].name == "claude"
    assert config.cycles["story"].repeat == 2


def test_missing_providers_raises_config_error(valid_config_data):
    del valid_config_data["providers"]
    with pytest.raises(ConfigError) as excinfo:
        validate_config(valid_config_data)
    assert "providers" in str(excinfo.value)


def test_missing_cycles_raises_config_error(valid_config_data):
    del valid_config_data["cycles"]
    with pytest.raises(ConfigError) as excinfo:
        validate_config(valid_config_data)
    assert "cycles" in str(excinfo.value)


def test_missing_git_raises_config_error(valid_config_data):
    del valid_config_data["git"]
    with pytest.raises(ConfigError) as excinfo:
        validate_config(valid_config_data)
    assert "git" in str(excinfo.value)


def test_invalid_enum_value_raises_config_error_listing_options(valid_config_data):
    valid_config_data["git"]["commit_at"] = "magical"
    with pytest.raises(ConfigError) as excinfo:
        validate_config(valid_config_data)
    assert "git -> commit_at" in str(excinfo.value)
    # Pydantic v2 error message for literals usually contains valid options
    assert "input: magical" in str(excinfo.value)


def test_invalid_step_type_enum_raises_config_error(valid_config_data):
    valid_config_data["cycles"]["story"]["steps"][0]["type"] = "magical"
    with pytest.raises(ConfigError) as excinfo:
        validate_config(valid_config_data)
    assert "type" in str(excinfo.value)
    assert "input: magical" in str(excinfo.value)


def test_step_config_field_types_enforced(valid_config_data):
    valid_config_data["cycles"]["story"]["steps"][0]["provider"] = "one"
    with pytest.raises(ConfigError) as excinfo:
        validate_config(valid_config_data)
    assert "provider" in str(excinfo.value)


def test_step_config_missing_skill_raises_config_error(valid_config_data):
    del valid_config_data["cycles"]["story"]["steps"][0]["skill"]
    with pytest.raises(ConfigError) as excinfo:
        validate_config(valid_config_data)
    assert "skill" in str(excinfo.value)


def test_step_config_empty_skill_raises_config_error(valid_config_data):
    valid_config_data["cycles"]["story"]["steps"][0]["skill"] = ""
    with pytest.raises(ConfigError) as excinfo:
        validate_config(valid_config_data)
    assert "skill" in str(excinfo.value)


def test_cycle_config_repeat_less_than_one_raises_error(valid_config_data):
    valid_config_data["cycles"]["story"]["repeat"] = 0
    with pytest.raises(ConfigError) as excinfo:
        validate_config(valid_config_data)
    assert "repeat" in str(excinfo.value)


def test_cycle_config_default_repeat_works(valid_config_data):
    del valid_config_data["cycles"]["story"]["repeat"]
    config = validate_config(valid_config_data)
    assert config.cycles["story"].repeat == 1


def test_extra_yaml_keys_raise_validation_error(valid_config_data):
    valid_config_data["extra_key"] = "forbidden"
    with pytest.raises(ConfigError) as excinfo:
        validate_config(valid_config_data)
    assert "extra_key" in str(excinfo.value)
    assert "Extra inputs are not permitted" in str(excinfo.value)


def test_provider_reference_nonexistent_raises_config_error(valid_config_data):
    valid_config_data["cycles"]["story"]["steps"][0]["provider"] = 99
    with pytest.raises(ConfigError) as excinfo:
        validate_config(valid_config_data)
    assert "references nonexistent provider ID: 99" in str(excinfo.value)


def test_valid_config_with_optional_pause_overrides(valid_config_data):
    valid_config_data["cycles"]["story"]["pause_between_steps"] = 10.5
    config = validate_config(valid_config_data)
    assert config.cycles["story"].pause_between_steps == 10.5


def test_empty_providers_dict_raises_config_error(valid_config_data):
    valid_config_data["providers"] = {}
    with pytest.raises(ConfigError) as excinfo:
        validate_config(valid_config_data)
    assert "providers dict must have at least one entry" in str(excinfo.value)


def test_empty_steps_list_raises_config_error(valid_config_data):
    valid_config_data["cycles"]["story"]["steps"] = []
    with pytest.raises(ConfigError) as excinfo:
        validate_config(valid_config_data)
    assert "steps" in str(excinfo.value)


def test_invalid_max_retries_raises_config_error(valid_config_data):
    valid_config_data["error_handling"]["max_retries"] = 0
    with pytest.raises(ConfigError) as excinfo:
        validate_config(valid_config_data)
    assert "max_retries" in str(excinfo.value)

    valid_config_data["error_handling"]["max_retries"] = -1
    with pytest.raises(ConfigError) as excinfo:
        validate_config(valid_config_data)
    assert "max_retries" in str(excinfo.value)


def test_negative_pause_values_raise_config_error(valid_config_data):
    valid_config_data["pauses"]["between_steps"] = -1.0
    with pytest.raises(ConfigError) as excinfo:
        validate_config(valid_config_data)
    assert "between_steps" in str(excinfo.value)


def test_cycle_config_negative_pause_raises_config_error(valid_config_data):
    valid_config_data["cycles"]["story"]["pause_between_steps"] = -1.0
    with pytest.raises(ConfigError) as excinfo:
        validate_config(valid_config_data)
    assert "pause_between_steps" in str(excinfo.value)


def test_empty_cycles_dict_raises_config_error(valid_config_data):
    valid_config_data["cycles"] = {}
    with pytest.raises(ConfigError) as excinfo:
        validate_config(valid_config_data)
    assert "cycles dict must have at least one entry" in str(excinfo.value)


def test_config_error_message_format(valid_config_data):
    valid_config_data["git"]["commit_at"] = "invalid"
    with pytest.raises(ConfigError) as excinfo:
        validate_config(valid_config_data)
    msg = str(excinfo.value)
    assert "✗ Config validation failed" in msg
    assert "git -> commit_at" in msg
    assert "input: invalid" in msg


def test_validate_config_returns_orchestrator_config(valid_config_data):
    result = validate_config(valid_config_data)
    assert isinstance(result, OrchestratorConfig)


def test_validate_config_raises_config_error_not_validation_error(valid_config_data):
    valid_config_data["providers"] = {}
    from pydantic import ValidationError

    with pytest.raises(ConfigError) as excinfo:
        validate_config(valid_config_data)
    assert not isinstance(excinfo.value, ValidationError)
