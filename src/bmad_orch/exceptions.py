from dataclasses import dataclass

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


class TemplateVariableError(BmadOrchError):
    """Raised when a prompt contains unresolved variables."""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.BLOCKING) -> None:
        super().__init__(message, severity)


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


class ProviderTransientError(ProviderError):
    """Raised when a provider encounters a transient, retryable error (e.g., 502, 429)."""

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

@dataclass(frozen=True)
class ErrorClassification:
    is_recoverable: bool
    severity: ErrorSeverity

def classify_error(error: Exception) -> ErrorClassification:
    if isinstance(error, BmadOrchError):
        sev = error.severity
        return ErrorClassification(is_recoverable=(sev == ErrorSeverity.RECOVERABLE), severity=sev)

    status: int | None = getattr(error, 'status_code', None)
    if status in (429, 502, 503, 504):
        return ErrorClassification(is_recoverable=True, severity=ErrorSeverity.RECOVERABLE)

    exit_code: int | None = getattr(error, 'exit_code', None)
    if exit_code is not None and exit_code != 0:
        return ErrorClassification(is_recoverable=False, severity=ErrorSeverity.IMPACTFUL)

    return ErrorClassification(is_recoverable=False, severity=ErrorSeverity.IMPACTFUL)
