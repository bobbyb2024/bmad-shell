import time
from abc import ABC
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional

class EscalationLevel(IntEnum):
    OK = 0
    ATTENTION = 1
    ACTION = 2

class LogLevel(IntEnum):
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

@dataclass(frozen=True, kw_only=True)
class BaseEvent(ABC):
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if type(self) is BaseEvent:
            raise TypeError("BaseEvent is an abstract class and cannot be instantiated directly")

@dataclass(frozen=True, kw_only=True)
class StepStarted(BaseEvent):
    step_name: str
    step_index: int

@dataclass(frozen=True, kw_only=True)
class StepCompleted(BaseEvent):
    step_name: str
    step_index: int
    success: bool

@dataclass(frozen=True, kw_only=True)
class CycleStarted(BaseEvent):
    cycle_number: int
    provider_name: str

@dataclass(frozen=True, kw_only=True)
class CycleCompleted(BaseEvent):
    cycle_number: int
    provider_name: str
    success: bool

@dataclass(frozen=True, kw_only=True)
class EscalationChanged(BaseEvent):
    previous_level: Optional[EscalationLevel]
    new_level: EscalationLevel

@dataclass(frozen=True, kw_only=True)
class LogEntry(BaseEvent):
    level: LogLevel
    message: str
    source: str

@dataclass(frozen=True, kw_only=True)
class ProviderOutput(BaseEvent):
    provider_name: str
    content: str
    is_partial: bool

@dataclass(frozen=True, kw_only=True)
class RunCompleted(BaseEvent):
    success: bool
    total_cycles: int
    error_count: int

@dataclass(frozen=True, kw_only=True)
class ErrorOccurred(BaseEvent):
    error_type: str
    message: str
    source: str
    recoverable: bool

@dataclass(frozen=True, kw_only=True)
class ResourceThresholdBreached(BaseEvent):
    resource_name: str
    current_value: float
    threshold: float
