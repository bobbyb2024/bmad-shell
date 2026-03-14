from dataclasses import dataclass
from enum import Enum
from typing import NewType

ProviderName = NewType("ProviderName", str)
StepOutcome = NewType("StepOutcome", str)


class StepType(Enum):
    GENERATIVE = "generative"
    VALIDATION = "validation"


class Timing(Enum):
    STEP = "step"
    CYCLE = "cycle"
    END = "end"


class EscalationState(Enum):
    OK = "ok"
    ATTENTION = "attention"
    ACTION = "action"
    COMPLETE = "complete"
    IDLE = "idle"


@dataclass(frozen=True)
class OutputChunk:
    content: str
    is_stderr: bool = False
    is_complete: bool = False
