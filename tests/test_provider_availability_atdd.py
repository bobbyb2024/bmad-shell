"""
ATDD Tests for Story 2.4: Single-Provider Graceful Mode
Level: Unit — validate_provider_availability() function
TDD Phase: GREEN (all tests active)

Acceptance Criteria:
  AC1: Missing Provider Warning — ConfigError with missing name, install hint, and guidance
  AC2: Single-Provider Validation — single-provider configs pass validation
  AC3: Execution with Single Provider — (covered by CLI integration tests)
  AC4: No Provider Error — ConfigError listing all adapters with install hints
  AC5: Detection Failure Handling — exception treated as unavailable + WARNING to stderr
"""

import sys
import time
from typing import Any, AsyncIterator
from unittest.mock import patch

import pytest
import yaml

from bmad_orch.config.discovery import validate_provider_availability
from bmad_orch.config.schema import validate_config
from bmad_orch.exceptions import ConfigError
from bmad_orch.providers import register_adapter, clear_registry, _instances
from bmad_orch.providers.base import ProviderAdapter
from bmad_orch.types import OutputChunk


# ---------------------------------------------------------------------------
# Test adapter stubs
# ---------------------------------------------------------------------------

class DetectedAdapter(ProviderAdapter):
    """Adapter stub that is always detected."""
    install_hint = "pip install detected-provider"

    def detect(self, cli_path: str | None = None) -> bool:
        return True

    def list_models(self) -> list[dict[str, Any]]:
        return [{"id": "detected-model"}]

    async def _execute(self, prompt: str, **kwargs: Any) -> AsyncIterator[OutputChunk]:
        yield OutputChunk(content="ok", timestamp=time.time(), metadata={})


class UndetectedAdapter(ProviderAdapter):
    """Adapter stub that is never detected."""
    install_hint = "pip install undetected-provider"

    def detect(self, cli_path: str | None = None) -> bool:
        return False

    def list_models(self) -> list[dict[str, Any]]:
        return []

    async def _execute(self, prompt: str, **kwargs: Any) -> AsyncIterator[OutputChunk]:
        yield OutputChunk(content="", timestamp=time.time(), metadata={})


class ExplodingAdapter(ProviderAdapter):
    """Adapter stub whose detect() raises an unexpected exception (AC5)."""
    install_hint = "pip install exploding-provider"

    def detect(self, cli_path: str | None = None) -> bool:
        raise RuntimeError("subprocess timeout simulated")

    def list_models(self) -> list[dict[str, Any]]:
        return []

    async def _execute(self, prompt: str, **kwargs: Any) -> AsyncIterator[OutputChunk]:
        yield OutputChunk(content="", timestamp=time.time(), metadata={})


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
# Helpers
# ---------------------------------------------------------------------------

def _make_config(provider_names: list[str]):
    """Build a minimal OrchestratorConfig referencing the given provider names."""
    providers = {}
    for i, name in enumerate(provider_names, start=1):
        providers[i] = {"name": name, "cli": f"{name}-cli", "model": f"{name}-model"}
    raw = {
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
    return validate_config(raw)


# ===========================================================================
# AC1: Missing Provider Warning
# ===========================================================================

def test_ac1_missing_provider_raises_config_error():
    """
    GIVEN a config referencing providers 'alpha' and 'beta'
      AND only 'alpha' is detected on the host
    WHEN validate_provider_availability() is called
    THEN it raises ConfigError naming 'beta' as missing with its install hint.
    """
    register_adapter("alpha", DetectedAdapter)
    register_adapter("beta", UndetectedAdapter)
    config = _make_config(["alpha", "beta"])

    with pytest.raises(ConfigError) as exc_info:
        validate_provider_availability(config)

    msg = str(exc_info.value)
    assert "beta" in msg
    assert "pip install undetected-provider" in msg


def test_ac1_error_includes_update_config_guidance():
    """
    GIVEN a config referencing an unavailable provider
    WHEN validate_provider_availability() raises ConfigError
    THEN the error message includes 'OR update your config to use an available provider'.
    """
    register_adapter("alpha", DetectedAdapter)
    register_adapter("beta", UndetectedAdapter)
    config = _make_config(["alpha", "beta"])

    with pytest.raises(ConfigError) as exc_info:
        validate_provider_availability(config)

    msg = str(exc_info.value)
    assert "Missing referenced provider" in msg
    assert "OR update your config to use an available provider" in msg


def test_ac1_error_names_missing_adapter():
    """
    GIVEN a config referencing 'gamma' which is not detected
    WHEN validate_provider_availability() raises ConfigError
    THEN the message names 'gamma' by adapter name.
    """
    register_adapter("gamma", UndetectedAdapter)
    register_adapter("delta", DetectedAdapter)
    config = _make_config(["gamma"])

    with pytest.raises(ConfigError) as exc_info:
        validate_provider_availability(config)

    assert "gamma" in str(exc_info.value)


# ===========================================================================
# AC2: Single-Provider Validation
# ===========================================================================

def test_ac2_single_provider_config_passes():
    """
    GIVEN a config referencing only one provider 'solo'
      AND 'solo' is detected on the host
    WHEN validate_provider_availability() is called
    THEN validation passes without raising any exception.
    """
    register_adapter("solo", DetectedAdapter)
    config = _make_config(["solo"])

    # Should not raise
    validate_provider_availability(config)


def test_ac2_single_provider_no_warnings(capsys):
    """
    GIVEN a single-provider config with the provider detected
    WHEN validate_provider_availability() is called
    THEN no WARNING-level messages are printed to stderr.
    """
    register_adapter("solo", DetectedAdapter)
    config = _make_config(["solo"])

    validate_provider_availability(config)

    captured = capsys.readouterr()
    assert "WARNING" not in captured.err


# ===========================================================================
# AC4: No Provider Error
# ===========================================================================

def test_ac4_no_providers_detected_raises_config_error():
    """
    GIVEN no CLI providers are detected at all
    WHEN validate_provider_availability() is called
    THEN it raises ConfigError.
    """
    register_adapter("absent_a", UndetectedAdapter)
    register_adapter("absent_b", UndetectedAdapter)
    config = _make_config(["absent_a"])

    with pytest.raises(ConfigError):
        validate_provider_availability(config)


def test_ac4_error_lists_all_adapters_with_install_hints():
    """
    GIVEN no providers detected
    WHEN ConfigError is raised
    THEN the message lists every registered adapter with its install_hint.
    """
    register_adapter("absent_a", UndetectedAdapter)
    register_adapter("absent_b", UndetectedAdapter)
    config = _make_config(["absent_a"])

    with pytest.raises(ConfigError) as exc_info:
        validate_provider_availability(config)

    msg = str(exc_info.value)
    assert "absent_a" in msg
    assert "absent_b" in msg
    assert "pip install undetected-provider" in msg


def test_ac4_error_message_text():
    """
    GIVEN no providers detected
    WHEN ConfigError is raised
    THEN the message starts with 'No CLI providers detected'.
    """
    register_adapter("absent_a", UndetectedAdapter)
    config = _make_config(["absent_a"])

    with pytest.raises(ConfigError) as exc_info:
        validate_provider_availability(config)

    assert "No CLI providers detected" in str(exc_info.value)


# ===========================================================================
# AC5: Detection Failure Handling
# ===========================================================================

def test_ac5_detect_exception_treated_as_unavailable():
    """
    GIVEN a provider whose detect() raises RuntimeError
      AND another provider that is detected normally
    WHEN validate_provider_availability() is called with a config referencing only the good provider
    THEN validation passes (the exploding provider is treated as unavailable, not referenced).
    """
    register_adapter("good", DetectedAdapter)
    register_adapter("exploding", ExplodingAdapter)
    config = _make_config(["good"])

    # Should not raise — exploding provider is not referenced in config
    validate_provider_availability(config)


def test_ac5_warning_printed_to_stderr(capsys):
    """
    GIVEN a provider whose detect() raises an exception
    WHEN validate_provider_availability() is called
    THEN a WARNING is printed to stderr naming the provider and the exception.
    """
    register_adapter("good", DetectedAdapter)
    register_adapter("exploding", ExplodingAdapter)
    config = _make_config(["good"])

    validate_provider_availability(config)

    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    assert "exploding" in captured.err
    assert "subprocess timeout simulated" in captured.err


def test_ac5_continues_checking_after_failure():
    """
    GIVEN provider 'exploding' whose detect() raises
      AND provider 'good' whose detect() returns True
    WHEN validate_provider_availability() is called with config referencing 'good'
    THEN validation passes (proving remaining providers were still checked).
    """
    register_adapter("exploding", ExplodingAdapter)
    register_adapter("good", DetectedAdapter)
    config = _make_config(["good"])

    # If it didn't continue checking after 'exploding' failed,
    # 'good' would never be detected and AC4 error would fire.
    validate_provider_availability(config)


def test_ac5_referenced_exploding_provider_raises():
    """
    GIVEN a config referencing provider 'exploding' whose detect() raises
      AND no other providers are detected
    WHEN validate_provider_availability() is called
    THEN ConfigError is raised (provider treated as unavailable).
    """
    register_adapter("exploding", ExplodingAdapter)
    config = _make_config(["exploding"])

    with pytest.raises(ConfigError):
        validate_provider_availability(config)
