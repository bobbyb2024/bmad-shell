import time
from dataclasses import FrozenInstanceError

import pytest

from bmad_orch.engine import (
    BaseEvent,
    CycleCompleted,
    CycleStarted,
    ErrorOccurred,
    EscalationChanged,
    EscalationLevel,
    LogEntry,
    LogLevel,
    ProviderOutput,
    ResourceThresholdBreached,
    RunCompleted,
    StepCompleted,
    StepStarted,
)


def test_base_event_is_abc():
    with pytest.raises(TypeError):
        BaseEvent()

def test_event_is_frozen():
    event = StepStarted(step_name="test", step_index=0)
    with pytest.raises(FrozenInstanceError):
        event.step_index = 1

def test_escalation_level_enum():
    assert EscalationLevel.OK == 0
    assert EscalationLevel.ATTENTION == 1
    assert EscalationLevel.ACTION == 2

def test_log_level_enum():
    assert LogLevel.DEBUG == 10
    assert LogLevel.INFO == 20
    assert LogLevel.WARNING == 30
    assert LogLevel.ERROR == 40
    assert LogLevel.CRITICAL == 50


def test_timestamp_auto_generated():
    # AC1: BaseEvent carries a timestamp: float field using field(default_factory=time.time)
    before = time.time()
    event = StepStarted(step_name="test", step_index=0)
    after = time.time()
    assert isinstance(event.timestamp, float)
    assert before <= event.timestamp <= after


def test_escalation_changed_with_optional_none():
    # AC1: EscalationChanged has previous_level: Optional[EscalationLevel]
    event = EscalationChanged(step_name="test", previous_level=None, new_level=EscalationLevel.ATTENTION)
    assert event.previous_level is None
    assert event.new_level == EscalationLevel.ATTENTION


def test_escalation_changed_with_both_levels():
    event = EscalationChanged(
        step_name="test", previous_level=EscalationLevel.ATTENTION, new_level=EscalationLevel.ACTION
    )
    assert event.previous_level == EscalationLevel.ATTENTION
    assert event.new_level == EscalationLevel.ACTION


def test_log_entry_with_enum_level():
    # AC1: LogEntry has level: LogLevel enum field
    event = LogEntry(level=LogLevel.WARNING, message="test msg", source="engine")
    assert event.level == LogLevel.WARNING
    assert event.message == "test msg"
    assert event.source == "engine"


def test_all_event_types_instantiate():
    # AC1: Verify all event types from the Event Field Specifications are constructible
    events = [
        StepStarted(step_name="s", step_index=0),
        StepCompleted(step_name="s", step_index=0, success=True),
        CycleStarted(cycle_number=1, provider_name="p"),
        CycleCompleted(cycle_number=1, provider_name="p", success=True),
        EscalationChanged(step_name="s", previous_level=None, new_level=EscalationLevel.OK),
        LogEntry(level=LogLevel.INFO, message="m", source="s"),
        ProviderOutput(provider_name="p", content="c", is_partial=False),
        RunCompleted(success=True, total_cycles=1, total_step_count=1, elapsed_time=1.0, error_count=0),
        ErrorOccurred(error_type="E", message="m", source="s", recoverable=True),
        ResourceThresholdBreached(resource_name="cpu", current_value=95.0, threshold=90.0),
    ]
    for event in events:
        assert isinstance(event, BaseEvent)
        assert isinstance(event.timestamp, float)
