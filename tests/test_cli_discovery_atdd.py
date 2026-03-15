import time
from collections.abc import AsyncIterator
from typing import Any

import pytest
from typer.testing import CliRunner

from bmad_orch.cli import app
from bmad_orch.providers import register_adapter
from bmad_orch.providers.base import ProviderAdapter
from bmad_orch.types import OutputChunk


class _AlwaysDetectedAdapter(ProviderAdapter):
    install_hint = "test-only"

    def detect(self, cli_path: str | None = None) -> bool:
        return True

    def list_models(self) -> list[dict[str, Any]]:
        return [{"id": "test"}]

    async def _execute(self, prompt: str, **kwargs: Any) -> AsyncIterator[OutputChunk]:
        yield OutputChunk(content="ok", timestamp=time.time(), metadata={})


# Initialize CliRunner for Typer CLI testing
runner = CliRunner()


@pytest.fixture(autouse=True)
def _register_test_providers():
    """Register adapter for provider name 'p1' used in VALID_CONFIG_DATA."""
    register_adapter("p1", _AlwaysDetectedAdapter)


def test_cli_validate_cwd_discovery_ac1(tmp_path, monkeypatch, valid_config_file):
    """
    GIVEN a 'bmad-orch.yaml' exists in the current working directory
    WHEN I run 'bmad-orch validate' with no flags
    THEN the system discovers and loads 'bmad-orch.yaml' from the cwd
    """
    # Move the valid config file to the temporary directory's root
    config_path = tmp_path / "bmad-orch.yaml"
    config_path.write_text(valid_config_file.read_text())
    
    # Change current working directory to the temporary path
    monkeypatch.chdir(tmp_path)
    
    result = runner.invoke(app, ["validate"])
    
    assert result.exit_code == 0
    assert "Configuration is valid" in result.stdout
    assert "bmad-orch.yaml" in result.stdout


def test_cli_validate_explicit_path_override_ac2(tmp_path, monkeypatch, valid_config_file):
    """
    GIVEN a config file exists at an explicit path
    WHEN I run 'bmad-orch validate --config <path>'
    THEN the system loads the config from the explicit path (overriding cwd discovery)
    """
    # Create an explicit config file in a subdirectory
    other_dir = tmp_path / "custom_configs"
    other_dir.mkdir()
    explicit_config_path = other_dir / "my-config.yaml"
    explicit_config_path.write_text(valid_config_file.read_text())
    
    # Change directory to an empty path to ensure no CWD discovery happens
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    monkeypatch.chdir(empty_dir)
    
    result = runner.invoke(app, ["validate", "--config", str(explicit_config_path)])
    
    assert result.exit_code == 0
    assert str(explicit_config_path) in result.stdout
    assert "Configuration is valid" in result.stdout


def test_cli_validate_exit_code_2_no_config_ac3(tmp_path, monkeypatch):
    """
    GIVEN no 'bmad-orch.yaml' exists in cwd and no '--config' flag is provided
    WHEN I run 'bmad-orch validate'
    THEN the system exits with code 2 and a clear error
    """
    # Ensure current directory is empty
    monkeypatch.chdir(tmp_path)
    
    result = runner.invoke(app, ["validate"])
    
    assert result.exit_code == 2
    assert "No config found" in result.stdout
    assert "create bmad-orch.yaml or use --config" in result.stdout


def test_cli_validate_success_report_details_ac4(valid_config_file):
    """
    GIVEN a valid config file
    WHEN I run 'bmad-orch validate'
    THEN the system reports schema correctness (exit 0)
    AND the output confirms provider names and model names from the config
    """
    result = runner.invoke(app, ["validate", "--config", str(valid_config_file)])
    
    assert result.exit_code == 0
    assert "Configuration is valid" in result.stdout
    # p1 and m1 are defined in VALID_CONFIG_DATA in conftest.py
    assert "p1" in result.stdout
    assert "m1" in result.stdout


def test_cli_validate_yaml_syntax_error_ac5(tmp_path, monkeypatch):
    """
    GIVEN a config file with a YAML syntax error
    WHEN I run 'bmad-orch validate'
    THEN the system exits with code 2 and a clear error identifying the failure
    """
    # Create an invalid YAML file
    bad_config = tmp_path / "bmad-orch.yaml"
    bad_config.write_text("providers: [unclosed bracket")
    
    monkeypatch.chdir(tmp_path)
    
    result = runner.invoke(app, ["validate"])
    
    assert result.exit_code == 2
    assert "YAML syntax error" in result.stdout
    assert "line" in result.stdout or "position" in result.stdout
