import pathlib

import pytest
import yaml

from bmad_orch.config.discovery import discover_config_path, get_config, load_config_file
from bmad_orch.exceptions import ConfigError


def test_discover_config_path_explicit(tmp_path):
    config_file = tmp_path / "my-config.yaml"
    config_file.touch()
    path = discover_config_path(str(config_file))
    assert path == config_file.resolve()


def test_discover_config_path_explicit_not_found():
    with pytest.raises(ConfigError) as excinfo:
        discover_config_path("nonexistent.yaml")
    assert "Explicit config not found" in str(excinfo.value)


def test_discover_config_path_explicit_empty_string():
    with pytest.raises(ConfigError) as excinfo:
        discover_config_path("")
    assert "Empty config path" in str(excinfo.value)


def test_discover_config_path_explicit_whitespace_only():
    with pytest.raises(ConfigError) as excinfo:
        discover_config_path("   ")
    assert "Empty config path" in str(excinfo.value)


def test_discover_config_path_explicit_is_directory(tmp_path):
    dir_path = tmp_path / "not-a-file"
    dir_path.mkdir()
    with pytest.raises(ConfigError) as excinfo:
        discover_config_path(str(dir_path))
    assert "is not a file" in str(excinfo.value)


def test_discover_config_path_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "bmad-orch.yaml"
    config_file.touch()
    path = discover_config_path()
    assert path == config_file.resolve()


def test_discover_config_path_cwd_is_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    dir_path = tmp_path / "bmad-orch.yaml"
    dir_path.mkdir()
    with pytest.raises(ConfigError) as excinfo:
        discover_config_path()
    assert "is not a file" in str(excinfo.value)


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


def test_load_config_file_empty(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.touch()
    with pytest.raises(ConfigError) as excinfo:
        load_config_file(config_file)
    assert "is empty" in str(excinfo.value)


def test_load_config_file_not_a_mapping(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("- item1\n- item2\n")
    with pytest.raises(ConfigError) as excinfo:
        load_config_file(config_file)
    assert "does not contain a YAML mapping" in str(excinfo.value)


def test_load_config_file_generic_exception(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("key: value")

    def mock_open(*_args, **_kwargs):
        raise PermissionError("Permission denied")

    monkeypatch.setattr(pathlib.Path, "open", mock_open)
    with pytest.raises(ConfigError) as excinfo:
        load_config_file(config_file)
    assert "Failed to read config file" in str(excinfo.value)
    assert "Permission denied" in str(excinfo.value)


def test_get_config_full_cycle(valid_config_file, monkeypatch):
    monkeypatch.chdir(valid_config_file.parent)
    config, source_path = get_config()
    assert config.providers[1].name == "p1"
    assert source_path == valid_config_file.resolve()


def test_get_config_returns_source_path(valid_config_file):
    config, source_path = get_config(str(valid_config_file))
    assert source_path == valid_config_file.resolve()
