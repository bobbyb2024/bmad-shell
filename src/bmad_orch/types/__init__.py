from dataclasses import dataclass, field
from enum import Enum, StrEnum
from typing import Any, NewType

ProviderName = NewType("ProviderName", str)


class StepOutcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"


class ErrorSeverity(Enum):
    BLOCKING = "BLOCKING"
    IMPACTFUL = "IMPACTFUL"
    RECOVERABLE = "RECOVERABLE"
    WARNING = "WARNING"


class StepType(Enum):
    GENERATIVE = "generative"
    VALIDATION = "validation"


class EscalationState(Enum):
    OK = "ok"
    ATTENTION = "attention"
    ACTION = "action"
    COMPLETE = "complete"
    IDLE = "idle"


@dataclass(frozen=True)
class OutputChunk:
    content: str
    timestamp: float
    metadata: dict[str, Any] = field(default_factory=lambda: {})
