import time
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import yaml
from typer.testing import CliRunner

from bmad_orch.cli import app
from bmad_orch.providers import clear_registry, register_adapter
from bmad_orch.providers.base import ProviderAdapter
from bmad_orch.types import OutputChunk

runner = CliRunner()


class _DetectedClaude(ProviderAdapter):
    install_hint = "npm install -g @anthropic-ai/claude-code"
    def detect(self, cli_path: str | None = None) -> bool: return True
    def list_models(self) -> list[dict[str, Any]]: return []
    async def _execute(self, p: str, **k: Any) -> AsyncIterator[OutputChunk]:
        yield OutputChunk(content="ok", timestamp=time.time(), metadata={})


class _UndetectedClaude(ProviderAdapter):
    install_hint = "npm install -g @anthropic-ai/claude-code"
    def detect(self, cli_path: str | None = None) -> bool: return False
    def list_models(self) -> list[dict[str, Any]]: return []
    async def _execute(self, p: str, **k: Any) -> AsyncIterator[OutputChunk]:
        yield OutputChunk(content="", timestamp=time.time(), metadata={})


class _DetectedGemini(ProviderAdapter):
    install_hint = "npm install -g @google/gemini-cli"
    def detect(self, cli_path: str | None = None) -> bool: return True
    def list_models(self) -> list[dict[str, Any]]: return []
    async def _execute(self, p: str, **k: Any) -> AsyncIterator[OutputChunk]:
        yield OutputChunk(content="ok", timestamp=time.time(), metadata={})


class _UndetectedGemini(ProviderAdapter):
    install_hint = "npm install -g @google/gemini-cli"
    def detect(self, cli_path: str | None = None) -> bool: return False
    def list_models(self) -> list[dict[str, Any]]: return []
    async def _execute(self, p: str, **k: Any) -> AsyncIterator[OutputChunk]:
        yield OutputChunk(content="", timestamp=time.time(), metadata={})


class _ExplodingClaude(ProviderAdapter):
    install_hint = "npm install -g @anthropic-ai/claude-code"
    def detect(self, cli_path: str | None = None) -> bool: raise RuntimeError("Timeout")
    def list_models(self) -> list[dict[str, Any]]: return []
    async def _execute(self, p: str, **k: Any) -> AsyncIterator[OutputChunk]:
        yield OutputChunk(content="", timestamp=time.time(), metadata={})

def get_valid_config_dict():
    return {
        "providers": {
            1: {"name": "claude", "cli": "claude", "model": "opus-4"},
            2: {"name": "gemini", "cli": "gemini", "model": "gemini-2.5-pro"},
        },
        "cycles": {
            "story": {
                "steps": [
                    {"skill": "create-story", "provider": 1, "type": "generative", "prompt": "p1"},
                ],
            }
        },
        "git": {"commit_at": "cycle", "push_at": "end"},
        "pauses": {"between_steps": 5.0, "between_cycles": 15.0, "between_workflows": 30.0},
        "error_handling": {"retry_transient": True, "max_retries": 3, "retry_delay": 10.0},
    }

@pytest.fixture
def temp_config(tmp_path):
    """Create a temporary config file."""
    config_data = get_valid_config_dict()
    config_file = tmp_path / "bmad-orch.yaml"
    config_file.write_text(yaml.dump(config_data))
    return config_file

def test_ac1_missing_referenced_provider(temp_config):
    """Test AC1: Referenced provider is missing."""
    clear_registry()
    register_adapter("claude", _DetectedClaude)
    register_adapter("gemini", _UndetectedGemini)

    result = runner.invoke(app, ["validate", "--config", str(temp_config)])
    assert result.exit_code == 2
    output = result.output
    assert "Missing referenced provider(s):" in output
    assert "gemini" in output
    assert "npm install -g @google/gemini-cli" in output
    assert "OR update your config to use an available provider" in output

def test_ac2_single_provider_valid(tmp_path):
    """Test AC2: Single provider config is valid."""
    clear_registry()
    register_adapter("claude", _DetectedClaude)
    register_adapter("gemini", _UndetectedGemini)

    config_data = get_valid_config_dict()
    del config_data["providers"][2] # Remove gemini

    config_file = tmp_path / "bmad-orch.yaml"
    config_file.write_text(yaml.dump(config_data))

    result = runner.invoke(app, ["validate", "--config", str(config_file)])
    assert result.exit_code == 0
    assert "Configuration is valid and providers are available." in result.output

def test_ac4_no_providers_detected(temp_config):
    """Test AC4: No providers detected at all."""
    clear_registry()
    register_adapter("claude", _UndetectedClaude)
    register_adapter("gemini", _UndetectedGemini)

    result = runner.invoke(app, ["validate", "--config", str(temp_config)])
    assert result.exit_code == 2
    output = result.output
    assert "No CLI providers detected. Please install at least one:" in output
    assert "claude" in output
    assert "npm install -g @anthropic-ai/claude-code" in output
    assert "gemini" in output
    assert "npm install -g @google/gemini-cli" in output

def test_ac5_detection_failure_handling(temp_config):
    """Test AC5: detect() raises unexpected exception."""
    clear_registry()
    register_adapter("claude", _ExplodingClaude)
    register_adapter("gemini", _DetectedGemini)

    result = runner.invoke(app, ["validate", "--config", str(temp_config)])
    assert result.exit_code == 2
    output = result.output
    assert "Missing referenced provider(s):" in output
    assert "claude" in output

def test_ac3_execution_single_provider(tmp_path):
    """Test AC3: Execution with single provider completes."""
    clear_registry()
    register_adapter("claude", _DetectedClaude)
    register_adapter("gemini", _UndetectedGemini)

    config_data = get_valid_config_dict()
    del config_data["providers"][2]

    config_file = tmp_path / "bmad-orch.yaml"
    config_file.write_text(yaml.dump(config_data))

    with patch("bmad_orch.cli.Runner") as mock_runner:
        mock_instance = mock_runner.return_value
        mock_instance.run = AsyncMock()

        result = runner.invoke(app, ["start", "--config", str(config_file), "--no-preflight"])
        assert result.exit_code == 0
        mock_instance.run.assert_called_once()
