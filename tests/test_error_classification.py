from unittest.mock import AsyncMock, Mock, patch

import pytest

from bmad_orch.engine.cycle import CycleExecutor
from bmad_orch.engine.events import ErrorOccurred
from bmad_orch.exceptions import BmadOrchError, classify_error
from bmad_orch.types import ErrorSeverity


def test_rate_limit_error_classification():
    error = type('MockProviderError', (Exception,), {'status_code': 429})()
    classification = classify_error(error)
    assert classification.is_recoverable is True
    assert classification.severity == ErrorSeverity.RECOVERABLE


def test_subprocess_crash_classification():
    error = type('MockSubprocessCrash', (Exception,), {'exit_code': -9})()
    classification = classify_error(error)
    assert classification.is_recoverable is False
    assert classification.severity == ErrorSeverity.IMPACTFUL


@patch('bmad_orch.engine.cycle.logger')
def test_recoverable_error_logs_warning(logger_mock):
    """AC2/AC5: Recoverable errors log at WARNING level, not ERROR."""
    executor = CycleExecutor(Mock(), Mock(), Mock(), Mock(), Mock(), adapter_factory=Mock())
    error = BmadOrchError("Test error", severity=ErrorSeverity.RECOVERABLE)
    executor.log_error(error, "Execution continues to the next retry or step")
    logger_mock.warning.assert_called_once()
    logger_mock.error.assert_not_called()


@patch('bmad_orch.engine.cycle.logger')
def test_impactful_error_logs_error(logger_mock):
    """AC5: Impactful errors log at ERROR level."""
    executor = CycleExecutor(Mock(), Mock(), Mock(), Mock(), Mock(), adapter_factory=Mock())
    error = BmadOrchError("Test crash", severity=ErrorSeverity.IMPACTFUL)
    executor.log_error(error, "Check provider configuration and logs")
    logger_mock.error.assert_called_once()
    logger_mock.warning.assert_not_called()


@pytest.mark.asyncio
async def test_impactful_error_cleanup():
    """AC4: Impactful error emits ErrorOccurred and cleans up subprocess."""
    event_emitter = Mock()
    executor = CycleExecutor(event_emitter, Mock(), Mock(), Mock(), Mock(), adapter_factory=Mock())
    process_mock = AsyncMock()
    error = BmadOrchError("Test crash", severity=ErrorSeverity.IMPACTFUL)
    await executor.handle_error_async(error, process=process_mock)
    process_mock.kill.assert_called_once()
    process_mock.wait.assert_called_once()
    emitted = event_emitter.emit.call_args[0][0]
    assert isinstance(emitted, ErrorOccurred)
    assert emitted.recoverable is False
    assert emitted.suggested_action == "Check provider configuration and logs"


@pytest.mark.asyncio
async def test_recoverable_error_no_event():
    """AC2: Recoverable errors do NOT emit ErrorOccurred."""
    event_emitter = Mock()
    executor = CycleExecutor(event_emitter, Mock(), Mock(), Mock(), Mock(), adapter_factory=Mock())
    error = BmadOrchError("Transient error", severity=ErrorSeverity.RECOVERABLE)
    await executor.handle_error_async(error, process=None)
    event_emitter.emit.assert_not_called()


@patch('bmad_orch.engine.cycle.logger')
def test_structured_logging_format(logger_mock):
    """AC5: Log format is ✗ [What happened] — [What to do next]."""
    executor = CycleExecutor(Mock(), Mock(), Mock(), Mock(), Mock(), adapter_factory=Mock())
    executor.log_error(Exception("Test context error"), "ACTION HERE")
    log_msg = logger_mock.error.call_args[0][0]
    assert log_msg.startswith('✗ [Test context error]')
    assert ' — [ACTION HERE]' in log_msg


def test_enum_severity_check():
    """AC6: classify_error uses error.severity enum, not isinstance()."""
    error = BmadOrchError("custom error", severity=ErrorSeverity.IMPACTFUL)
    classification = classify_error(error)
    assert classification.severity == ErrorSeverity.IMPACTFUL
    assert classification.is_recoverable is False


def test_transient_http_status_codes():
    """AC1: All transient HTTP status codes are classified as RECOVERABLE."""
    for status in (429, 502, 503, 504):
        error = type('HttpError', (Exception,), {'status_code': status})()
        classification = classify_error(error)
        assert classification.is_recoverable is True, f"Status {status} should be recoverable"
        assert classification.severity == ErrorSeverity.RECOVERABLE
