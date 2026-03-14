from enum import Enum, auto


class ErrorSeverity(Enum):
    BLOCKING = auto()
    RECOVERABLE = auto()
    IMPACTFUL = auto()


class BmadOrchError(Exception):
    """Base exception for all bmad-orch errors."""

    default_severity: ErrorSeverity = ErrorSeverity.IMPACTFUL

    def __init__(self, message: str, severity: ErrorSeverity | None = None) -> None:
        super().__init__(message)
        self.severity = severity or self.default_severity


class ConfigError(BmadOrchError):
    """Raised when configuration is invalid."""

    default_severity = ErrorSeverity.BLOCKING


class ProviderError(BmadOrchError):
    """Base exception for provider-related errors."""


class ProviderNotFoundError(ProviderError):
    """Raised when a provider is not found."""

    default_severity = ErrorSeverity.BLOCKING


class ProviderTimeoutError(ProviderError):
    """Raised when a provider times out."""

    default_severity = ErrorSeverity.RECOVERABLE


class ProviderCrashError(ProviderError):
    """Raised when a provider crashes."""

    default_severity = ErrorSeverity.IMPACTFUL


class StateError(BmadOrchError):
    """Raised when state operations fail."""

    default_severity = ErrorSeverity.IMPACTFUL


class GitError(BmadOrchError):
    """Raised when git operations fail."""

    default_severity = ErrorSeverity.IMPACTFUL


class ResourceError(BmadOrchError):
    """Raised when resource limits are breached."""

    default_severity = ErrorSeverity.IMPACTFUL


class WizardError(BmadOrchError):
    """Raised during the init wizard."""

    default_severity = ErrorSeverity.BLOCKING
