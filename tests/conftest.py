import pathlib
import tomllib
import pytest
import yaml
import time
from typing import AsyncIterator, Any
from bmad_orch.providers import ProviderAdapter, register_adapter, clear_registry
from bmad_orch.types import OutputChunk
from bmad_orch.providers.claude import ClaudeAdapter
from bmad_orch.providers.gemini import GeminiAdapter

VALID_CONFIG_DATA = {
    "providers": {1: {"name": "p1", "cli": "c1", "model": "m1"}},
    "cycles": {
        "c1": {
            "steps": [
                {"skill": "s1", "provider": 1, "type": "generative", "prompt": "p1"}
            ]
        }
    },
    "git": {"commit_at": "cycle", "push_at": "end"},
    "pauses": {"between_steps": 1, "between_cycles": 1, "between_workflows": 1},
    "error_handling": {"retry_transient": True, "max_retries": 3, "retry_delay": 10},
}


@pytest.fixture
def project_root() -> pathlib.Path:
    """Fixture to get the project root directory."""
    return pathlib.Path(__file__).parent.parent


@pytest.fixture
def pyproject_content(project_root: pathlib.Path):
    """Fixture to read and parse pyproject.toml."""
    path = project_root / "pyproject.toml"
    with path.open("rb") as f:
        return tomllib.load(f)


@pytest.fixture
def valid_config_file(tmp_path):
    """Create a valid bmad-orch.yaml in tmp_path and return its Path."""
    config_file = tmp_path / "bmad-orch.yaml"
    config_file.write_text(yaml.dump(VALID_CONFIG_DATA))
    return config_file


class MockProvider(ProviderAdapter):
    def __init__(self, **config):
        self.config = config

    def detect(self, cli_path: str | None = None) -> bool:
        return True

    def list_models(self) -> list[dict[str, Any]]:
        return [{"id": "mock-model"}]

    async def _execute(self, prompt: str, **kwargs) -> AsyncIterator[OutputChunk]:
        yield OutputChunk(
            content=f"Echo: {prompt}",
            timestamp=time.time(),
            metadata={}
        )


@pytest.fixture(autouse=True)
def reset_registry():
    """Clear the provider registry and restore defaults before each test."""
    clear_registry()
    # Manual re-registration to avoid circular import issues
    register_adapter("claude", ClaudeAdapter)
    register_adapter("gemini", GeminiAdapter)
    yield
    clear_registry()
    register_adapter("claude", ClaudeAdapter)
    register_adapter("gemini", GeminiAdapter)
