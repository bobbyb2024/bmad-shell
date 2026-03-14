import pathlib
import pytest
import yaml
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from bmad_orch.cli import app
from bmad_orch.providers import _registry, clear_registry, register_adapter
from bmad_orch.providers.base import ProviderAdapter

runner = CliRunner()

@pytest.fixture
def mock_providers():
    """Setup clean registry with mock providers."""
    clear_registry()
    
    class MockClaude(ProviderAdapter):
        install_hint = "npm install -g @anthropic-ai/claude-code"
        def detect(self): return True
        def list_models(self): return []
        async def _execute(self, p, **k): yield MagicMock()

    class MockGemini(ProviderAdapter):
        install_hint = "npm install -g @google/gemini-cli"
        def detect(self): return True
        def list_models(self): return []
        async def _execute(self, p, **k): yield MagicMock()

    register_adapter("claude", MockClaude)
    register_adapter("gemini", MockGemini)
    
    yield
    clear_registry()

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

def test_ac1_missing_referenced_provider(mock_providers, temp_config):
    """Test AC1: Referenced provider is missing."""
    from bmad_orch.providers import _registry
    _registry["claude"].detect = MagicMock(return_value=True)
    _registry["gemini"].detect = MagicMock(return_value=False)

    result = runner.invoke(app, ["validate", "--config", str(temp_config)])
    assert result.exit_code == 2
    # Typer/CliRunner captures stderr in result.stderr or result.stdout depending on configuration,
    # but by default it should be in result.stderr if it was printed to stderr.
    output = result.stdout + result.stderr
    assert "Missing referenced provider(s):" in output
    assert "gemini" in output
    assert "npm install -g @google/gemini-cli" in output

def test_ac2_single_provider_valid(mock_providers, tmp_path):
    """Test AC2: Single provider config is valid."""
    config_data = get_valid_config_dict()
    del config_data["providers"][2] # Remove gemini
    
    config_file = tmp_path / "bmad-orch.yaml"
    config_file.write_text(yaml.dump(config_data))

    from bmad_orch.providers import _registry
    _registry["claude"].detect = MagicMock(return_value=True)
    _registry["gemini"].detect = MagicMock(return_value=False)

    result = runner.invoke(app, ["validate", "--config", str(config_file)])
    assert result.exit_code == 0
    output = result.stdout + result.stderr
    assert "Configuration is valid and providers are available." in output

def test_ac4_no_providers_detected(mock_providers, temp_config):
    """Test AC4: No providers detected at all."""
    from bmad_orch.providers import _registry
    _registry["claude"].detect = MagicMock(return_value=False)
    _registry["gemini"].detect = MagicMock(return_value=False)

    result = runner.invoke(app, ["validate", "--config", str(temp_config)])
    assert result.exit_code == 2
    output = result.stdout + result.stderr
    assert "No CLI providers detected. Please install at least one:" in output
    assert "claude" in output
    assert "gemini" in output

def test_ac5_detection_failure_handling(mock_providers, temp_config):
    """Test AC5: detect() raises unexpected exception."""
    from bmad_orch.providers import _registry
    _registry["claude"].detect = MagicMock(side_effect=RuntimeError("Timeout"))
    _registry["gemini"].detect = MagicMock(return_value=True)

    result = runner.invoke(app, ["validate", "--config", str(temp_config)])
    assert result.exit_code == 2
    output = result.stdout + result.stderr
    assert "Missing referenced provider(s):" in output
    assert "claude" in output
    assert "WARNING: Unexpected error detecting provider 'claude': Timeout" in output

def test_ac3_execution_single_provider(mock_providers, tmp_path):
    """Test AC3: Execution with single provider completes."""
    config_data = get_valid_config_dict()
    del config_data["providers"][2]
    
    config_file = tmp_path / "bmad-orch.yaml"
    config_file.write_text(yaml.dump(config_data))

    from bmad_orch.providers import _registry
    _registry["claude"].detect = MagicMock(return_value=True)
    
    with patch("bmad_orch.cli.Runner") as mock_runner:
        mock_instance = mock_runner.return_value
        
        result = runner.invoke(app, ["start", "--config", str(config_file), "--no-preflight"])
        assert result.exit_code == 0
        mock_instance.run.assert_called_once()
