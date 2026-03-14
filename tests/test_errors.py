import pytest


def test_error_inheritance():
    """Verify that all custom errors inherit from BmadOrchError."""
    from bmad_orch.exceptions import (
        BmadOrchError,
        ConfigError,
        GitError,
        ProviderCrashError,
        ProviderError,
        ProviderNotFoundError,
        ProviderTimeoutError,
        ResourceError,
        StateError,
        WizardError,
    )

    assert issubclass(BmadOrchError, Exception)
    assert issubclass(ConfigError, BmadOrchError)
    assert issubclass(ProviderError, BmadOrchError)
    assert issubclass(ProviderNotFoundError, ProviderError)
    assert issubclass(ProviderTimeoutError, ProviderError)
    assert issubclass(ProviderCrashError, ProviderError)
    assert issubclass(StateError, BmadOrchError)
    assert issubclass(ResourceError, BmadOrchError)
    assert issubclass(GitError, BmadOrchError)
    assert issubclass(WizardError, BmadOrchError)


def test_error_instantiation():
    """Verify that exceptions can be raised and caught correctly."""
    from bmad_orch.exceptions import BmadOrchError, ConfigError, ProviderNotFoundError

    with pytest.raises(BmadOrchError):
        raise ConfigError("Config failure")
    with pytest.raises(BmadOrchError):
        raise ProviderNotFoundError("Provider not found")


def test_error_severity():
    """Verify that error classes have correct default severity via __init__."""
    from bmad_orch.exceptions import (
        ConfigError,
        ErrorSeverity,
        ProviderCrashError,
        ProviderNotFoundError,
        ProviderTimeoutError,
        WizardError,
    )

    assert ConfigError("test").severity == ErrorSeverity.BLOCKING
    assert ProviderNotFoundError("test").severity == ErrorSeverity.BLOCKING
    assert ProviderTimeoutError("test").severity == ErrorSeverity.RECOVERABLE
    assert ProviderCrashError("test").severity == ErrorSeverity.IMPACTFUL
    assert WizardError("test").severity == ErrorSeverity.BLOCKING
