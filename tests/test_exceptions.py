import pytest
from bmad_orch.exceptions import (
    BmadOrchError,
    ProviderError,
    ProviderNotFoundError,
    ProviderCrashError,
    ProviderTimeoutError,
    ErrorSeverity,
)


def test_exception_hierarchy():
    assert issubclass(ProviderError, BmadOrchError)
    assert issubclass(ProviderNotFoundError, ProviderError)
    assert issubclass(ProviderCrashError, ProviderError)
    assert issubclass(ProviderTimeoutError, ProviderError)


def test_exception_severities():
    assert BmadOrchError("test").severity == ErrorSeverity.IMPACTFUL
    assert ProviderNotFoundError("test").severity == ErrorSeverity.BLOCKING
    assert ProviderCrashError("test").severity == ErrorSeverity.IMPACTFUL
    assert ProviderTimeoutError("test").severity == ErrorSeverity.RECOVERABLE


def test_provider_not_found_available_providers():
    with pytest.raises(ProviderNotFoundError) as excinfo:
        raise ProviderNotFoundError("foo", available_providers=["claude", "gemini"])
    assert excinfo.value.available_providers == ["claude", "gemini"]
