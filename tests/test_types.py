from bmad_orch.errors import ErrorSeverity
from bmad_orch.types import (
    EscalationState,
    OutputChunk,
    ProviderName,
    StepOutcome,
    StepType,
)


def test_output_chunk_creation():
    """Verify OutputChunk can be instantiated with correct fields."""
    chunk = OutputChunk(content="hello")
    assert chunk.content == "hello"
    assert chunk.is_stderr is False
    assert chunk.is_complete is False

    chunk_err = OutputChunk(content="err", is_stderr=True, is_complete=True)
    assert chunk_err.is_stderr is True
    assert chunk_err.is_complete is True


def test_output_chunk_frozen():
    """Verify OutputChunk is immutable."""
    import pytest

    chunk = OutputChunk(content="test")
    with pytest.raises(AttributeError):
        chunk.content = "changed"  # type: ignore[misc]


def test_escalation_state_enum():
    """Verify EscalationState has all expected members."""
    members = {m.name for m in EscalationState}
    assert members == {"OK", "ATTENTION", "ACTION", "COMPLETE", "IDLE"}
    assert EscalationState.OK.value == "ok"


def test_error_severity_enum():
    """Verify ErrorSeverity has all expected members."""
    members = {m.name for m in ErrorSeverity}
    assert members == {"BLOCKING", "RECOVERABLE", "IMPACTFUL"}


def test_step_type_enum():
    """Verify StepType has all expected members."""
    members = {m.name for m in StepType}
    assert members == {"GENERATIVE", "VALIDATION"}
    assert StepType.GENERATIVE.value == "generative"


def test_provider_name_newtype():
    """Verify ProviderName is a callable NewType wrapping str."""
    name = ProviderName("claude")
    assert isinstance(name, str)
    assert name == "claude"


def test_step_outcome_newtype():
    """Verify StepOutcome is a callable NewType wrapping str."""
    outcome = StepOutcome("success")
    assert isinstance(outcome, str)
    assert outcome == "success"
