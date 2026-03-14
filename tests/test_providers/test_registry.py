import pytest
from bmad_orch.providers import register_adapter, get_adapter, ProviderAdapter
from bmad_orch.exceptions import ProviderNotFoundError
from typing import AsyncIterator, Any
from bmad_orch.types import OutputChunk


class DummyProvider(ProviderAdapter):
    def detect(self): return True
    def list_models(self): return []
    async def _execute(self, p, **kw): yield OutputChunk(p, 0.0)


def test_registry_registration_and_retrieval():
    register_adapter("dummy", DummyProvider)
    adapter = get_adapter("dummy")
    assert isinstance(adapter, DummyProvider)


def test_registry_case_insensitivity():
    register_adapter("Claude", DummyProvider)
    with pytest.raises(ValueError, match="already exists"):
        register_adapter("claude", DummyProvider)

    adapter = get_adapter("CLAUDE")
    assert isinstance(adapter, DummyProvider)


def test_registry_unknown_provider():
    register_adapter("p1", DummyProvider)
    register_adapter("p2", DummyProvider)
    with pytest.raises(ProviderNotFoundError) as excinfo:
        get_adapter("unknown")
    assert "unknown" in str(excinfo.value)
    assert set(excinfo.value.available_providers) == {"p1", "p2"}


def test_registry_subclass_validation():
    class NotAnAdapter:
        pass
    with pytest.raises(TypeError, match="subclass of ProviderAdapter"):
        register_adapter("invalid", NotAnAdapter)


def test_registry_instantiation_with_config():
    class ConfigProvider(DummyProvider):
        def __init__(self, **config):
            self.config = config

    register_adapter("config", ConfigProvider)
    adapter = get_adapter("config", api_key="test-key")
    assert adapter.config["api_key"] == "test-key"
