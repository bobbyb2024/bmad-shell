"""
ATDD Tests for Story 2.4: Single-Provider Graceful Mode
Level: Integration — CLI commands (validate, start) with provider availability
TDD Phase: GREEN (all tests active)

Acceptance Criteria:
  AC1: Missing Provider Warning — validate exits 2 with provider error
  AC2: Single-Provider Validation — validate exits 0 for single-provider config
  AC3: Execution with Single Provider — start with single provider, no warnings, exit 0
  AC4: No Provider Error — validate exits 2 listing all adapters
"""

import time
from typing import Any, AsyncIterator
from unittest.mock import patch

import pytest
import yaml
from typer.testing import CliRunner

from bmad_orch.cli import app
from bmad_orch.providers import register_adapter, clear_registry
from bmad_orch.providers.base import ProviderAdapter
from bmad_orch.types import OutputChunk

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_registry():
    """Ensure a clean provider registry for each test."""
    clear_registry()
    yield
    clear_registry()


# ---------------------------------------------------------------------------
# Test adapter stubs for CLI integration
# ---------------------------------------------------------------------------

class CLIDetectedAdapter(ProviderAdapter):
    install_hint = "npm install -g cli-detected"

    def detect(self, cli_path: str | None = None) -> bool:
        return True

    def list_models(self) -> list[dict[str, Any]]:
        return [{"id": "test-model"}]

    async def _execute(self, prompt: str, **kwargs: Any) -> AsyncIterator[OutputChunk]:
        yield OutputChunk(content="ok", timestamp=time.time(), metadata={})


class CLIUndetectedAdapter(ProviderAdapter):
    install_hint = "npm install -g cli-undetected"

    def detect(self, cli_path: str | None = None) -> bool:
        return False

    def list_models(self) -> list[dict[str, Any]]:
        return []

    async def _execute(self, prompt: str, **kwargs: Any) -> AsyncIterator[OutputChunk]:
        yield OutputChunk(content="", timestamp=time.time(), metadata={})


# ---------------------------------------------------------------------------
# Config factory
# ---------------------------------------------------------------------------

def _write_config(tmp_path, provider_names: list[str]):
    """Write a valid bmad-orch.yaml referencing the given provider names."""
    providers = {}
    for i, name in enumerate(provider_names, start=1):
        providers[i] = {"name": name, "cli": f"{name}-cli", "model": f"{name}-model"}
    data = {
        "providers": providers,
        "cycles": {
            "c1": {
                "steps": [
                    {"skill": "s1", "provider": 1, "type": "generative", "prompt": "p"}
                ]
            }
        },
        "git": {"commit_at": "cycle", "push_at": "end"},
        "pauses": {"between_steps": 1, "between_cycles": 1, "between_workflows": 1},
        "error_handling": {"retry_transient": True, "max_retries": 3, "retry_delay": 10},
    }
    config_file = tmp_path / "bmad-orch.yaml"
    config_file.write_text(yaml.dump(data))
    return config_file


# ===========================================================================
# AC1: CLI surfaces missing provider error with exit code 2
# ===========================================================================

def test_ac1_validate_exits_2_missing_provider(tmp_path):
    """
    GIVEN a config referencing providers 'alpha' and 'beta'
      AND only 'alpha' is detected
    WHEN I run 'bmad-orch validate'
    THEN exit code is 2 and output names the missing provider.
    """
    register_adapter("alpha", CLIDetectedAdapter)
    register_adapter("beta", CLIUndetectedAdapter)
    config_file = _write_config(tmp_path, ["alpha", "beta"])

    result = runner.invoke(app, ["validate", "--config", str(config_file)])

    assert result.exit_code == 2
    assert "Missing referenced provider" in result.output
    assert "beta" in result.output


def test_ac1_start_exits_2_missing_provider(tmp_path):
    """
    GIVEN a config referencing an unavailable provider
    WHEN I run 'bmad-orch start'
    THEN it exits with code 2 during pre-flight validation.
    """
    register_adapter("alpha", CLIDetectedAdapter)
    register_adapter("beta", CLIUndetectedAdapter)
    config_file = _write_config(tmp_path, ["alpha", "beta"])

    result = runner.invoke(app, ["start", "--config", str(config_file), "--no-preflight"])

    assert result.exit_code == 2


# ===========================================================================
# AC2: CLI validate succeeds for single-provider config
# ===========================================================================

def test_ac2_validate_single_provider_success(tmp_path):
    """
    GIVEN a config referencing only provider 'solo'
      AND 'solo' is detected
    WHEN I run 'bmad-orch validate'
    THEN exit code is 0 and output confirms validity.
    """
    register_adapter("solo", CLIDetectedAdapter)
    config_file = _write_config(tmp_path, ["solo"])

    result = runner.invoke(app, ["validate", "--config", str(config_file)])

    assert result.exit_code == 0
    assert "Configuration is valid" in result.output


# ===========================================================================
# AC3: Single-provider execution — no warnings, exit 0
# ===========================================================================

def test_ac3_single_provider_dry_run_no_warnings(tmp_path):
    """
    GIVEN a valid single-provider config
    WHEN I run 'bmad-orch start --dry-run'
    THEN exit code is 0 and no WARNING about provider availability appears.
    """
    register_adapter("solo", CLIDetectedAdapter)
    config_file = _write_config(tmp_path, ["solo"])

    result = runner.invoke(app, ["start", "--config", str(config_file), "--dry-run"])

    assert result.exit_code == 0
    assert "WARNING" not in result.output


# ===========================================================================
# AC4: CLI surfaces no-provider error with exit code 2
# ===========================================================================

def test_ac4_validate_exits_2_no_providers(tmp_path):
    """
    GIVEN no providers are detected at all
    WHEN I run 'bmad-orch validate'
    THEN exit code is 2 and error lists all registered adapters with install hints.
    """
    register_adapter("absent_a", CLIUndetectedAdapter)
    register_adapter("absent_b", CLIUndetectedAdapter)
    config_file = _write_config(tmp_path, ["absent_a"])

    result = runner.invoke(app, ["validate", "--config", str(config_file)])

    assert result.exit_code == 2
    assert "No CLI providers detected" in result.output


def test_ac4_error_includes_install_hints(tmp_path):
    """
    GIVEN no providers detected
    WHEN validate exits with error
    THEN the output includes install_hint for each registered adapter.
    """
    register_adapter("absent_a", CLIUndetectedAdapter)
    register_adapter("absent_b", CLIUndetectedAdapter)
    config_file = _write_config(tmp_path, ["absent_a"])

    result = runner.invoke(app, ["validate", "--config", str(config_file)])

    assert result.exit_code == 2
    assert "npm install -g cli-undetected" in result.output
