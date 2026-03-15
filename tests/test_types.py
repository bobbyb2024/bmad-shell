import time
from dataclasses import is_dataclass

from bmad_orch.types import ErrorSeverity, OutputChunk


def test_output_chunk_structure():
    assert is_dataclass(OutputChunk)
    chunk = OutputChunk(content="test", timestamp=time.time(), metadata={"execution_id": "123"})
    assert chunk.content == "test"
    assert isinstance(chunk.timestamp, float)
    assert chunk.metadata["execution_id"] == "123"

def test_output_chunk_immutability():
    from dataclasses import FrozenInstanceError

    import pytest
    chunk = OutputChunk(content="test", timestamp=time.time())
    with pytest.raises(FrozenInstanceError):
        chunk.content = "new"


def test_error_severity_enum():
    assert "BLOCKING" in ErrorSeverity.__members__
    assert "IMPACTFUL" in ErrorSeverity.__members__
    assert "RECOVERABLE" in ErrorSeverity.__members__
    assert "WARNING" in ErrorSeverity.__members__
