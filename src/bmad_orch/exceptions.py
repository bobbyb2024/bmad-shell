from typing import Any
from bmad_orch.types import ErrorSeverity


class BmadOrchError(Exception):
    """Base exception for all bmad-orch errors."""

    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.IMPACTFUL) -> None:
        super().__init__(message)
        self.severity = severity


class ConfigError(BmadOrchError):
    """Raised when configuration is invalid."""

    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.BLOCKING) -> None:
        super().__init__(message, severity)


class ConfigProviderError(ConfigError):
    """Raised when a configuration references a nonexistent provider."""


class ProviderError(BmadOrchError):
    """Base exception for provider-related errors."""

    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.IMPACTFUL) -> None:
        super().__init__(message, severity)


class ProviderNotFoundError(ProviderError):
    """Raised when a provider is not found."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.BLOCKING,
        available_providers: list[str] | None = None,
    ) -> None:
        super().__init__(message, severity)
        self.available_providers = available_providers or []


class ProviderTimeoutError(ProviderError):
    """Raised when a provider times out."""

    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.RECOVERABLE) -> None:
        super().__init__(message, severity)


class ProviderCrashError(ProviderError):
    """Raised when a provider crashes."""

    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.IMPACTFUL) -> None:
        super().__init__(message, severity)


class StateError(BmadOrchError):
    """Raised when state operations fail."""


class GitError(BmadOrchError):
    """Raised when git operations fail."""


class ResourceError(BmadOrchError):
    """Raised when resource limits are breached."""


class WizardError(BmadOrchError):
    """Raised during the init wizard."""

    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.BLOCKING) -> None:
        super().__init__(message, severity)
