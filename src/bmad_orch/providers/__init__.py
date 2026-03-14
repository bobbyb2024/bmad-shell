from typing import Any, Type
from bmad_orch.providers.base import ProviderAdapter
from bmad_orch.exceptions import ProviderNotFoundError

# Internal registry of provider classes
_registry: dict[str, Type[ProviderAdapter]] = {}

# Internal registry of instantiated singletons
_instances: dict[str, ProviderAdapter] = {}


def register_adapter(name: str, adapter_cls: Type[ProviderAdapter]) -> None:
    """Register a new provider adapter class."""
    if not issubclass(adapter_cls, ProviderAdapter):
        raise TypeError(f"{adapter_cls} must be a subclass of ProviderAdapter")

    normalized_name = name.lower()
    if normalized_name in _registry:
        raise ValueError(f"Provider '{name}' already exists.")

    _registry[normalized_name] = adapter_cls


def get_adapter(name: str, **config: Any) -> ProviderAdapter:
    """Get an instantiated adapter for the requested provider."""
    normalized_name = name.lower()

    if normalized_name not in _registry:
        available = list(_registry.keys())
        raise ProviderNotFoundError(
            f"Provider '{name}' not found.",
            available_providers=available
        )

    # Use existing singleton if no new config is provided
    # If config IS provided, we re-instantiate (standard singleton with re-config support)
    if normalized_name in _instances and not config:
        return _instances[normalized_name]

    adapter_cls = _registry[normalized_name]
    adapter = adapter_cls(**config)
    _instances[normalized_name] = adapter
    return adapter


def clear_registry() -> None:
    """Clear all registered adapters and singleton instances. For test isolation."""
    _registry.clear()
    _instances.clear()


__all__ = ["ProviderAdapter", "get_adapter", "register_adapter", "clear_registry"]
