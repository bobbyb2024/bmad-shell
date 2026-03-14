import pathlib

import pytest
import yaml

from bmad_orch.config.discovery import discover_config_path, get_config, load_config_file
from bmad_orch.errors import ConfigError


def test_discover_config_path_explicit(tmp_path):
    config_file = tmp_path / "my-config.yaml"
    config_file.touch()
    path = discover_config_path(str(config_file))
    assert path == config_file


def test_discover_config_path_explicit_not_found():
    with pytest.raises(ConfigError) as excinfo:
        discover_config_path("nonexistent.yaml")
    assert "Explicit config not found" in str(excinfo.value)


def test_discover_config_path_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "bmad-orch.yaml"
    config_file.touch()
    path = discover_config_path()
    assert path == config_file


def test_discover_config_path_not_found(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigError) as excinfo:
        discover_config_path()
    assert "No config found" in str(excinfo.value)


def test_load_config_file_valid(tmp_path):
    config_file = tmp_path / "config.yaml"
    data = {"key": "value"}
    config_file.write_text(yaml.dump(data))
    loaded = load_config_file(config_file)
    assert loaded == data


def test_load_config_file_invalid_yaml(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("invalid: [yaml: structure")
    with pytest.raises(ConfigError) as excinfo:
        load_config_file(config_file)
    assert "YAML syntax error" in str(excinfo.value)


def test_load_config_file_generic_exception(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    config_file.touch()

    def mock_open(*_args, **_kwargs):
        raise PermissionError("Permission denied")

    monkeypatch.setattr(pathlib.Path, "open", mock_open)
    with pytest.raises(ConfigError) as excinfo:
        load_config_file(config_file)
    assert "Failed to read config file" in str(excinfo.value)
    assert "Permission denied" in str(excinfo.value)


def test_get_config_full_cycle(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "bmad-orch.yaml"
    valid_data = {
        "providers": {1: {"name": "p1", "cli": "c1", "model": "m1"}},
        "cycles": {"c1": {"steps": [{"skill": "s1", "provider": 1, "type": "generative", "prompt": "p1"}]}},
        "git": {"commit_at": "cycle", "push_at": "end"},
        "pauses": {"between_steps": 1, "between_cycles": 1, "between_workflows": 1},
        "error_handling": {"retry_transient": True, "max_retries": 3, "retry_delay": 10},
    }
    config_file.write_text(yaml.dump(valid_data))
    config = get_config()
    assert config.providers[1].name == "p1"
