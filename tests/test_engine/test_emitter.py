import logging
import pytest
from bmad_orch.engine import BaseEvent, StepStarted, StepCompleted, EventEmitter


def test_subscribe_and_emit():
    emitter = EventEmitter()
    received = []
    
    def callback(event: StepStarted):
        received.append(event)
        
    emitter.subscribe(StepStarted, callback)
    event = StepStarted(step_name="test", step_index=1)
    emitter.emit(event)
    
    assert len(received) == 1
    assert received[0] == event

def test_idempotent_subscription():
    emitter = EventEmitter()
    received = []
    
    def callback(event: StepStarted):
        received.append(event)
        
    emitter.subscribe(StepStarted, callback)
    emitter.subscribe(StepStarted, callback) # Duplicate
    
    emitter.emit(StepStarted(step_name="test", step_index=1))
    assert len(received) == 1

def test_base_event_catch_all():
    emitter = EventEmitter()
    received_specific = []
    received_base = []
    
    def specific_callback(event: StepStarted):
        received_specific.append("specific")
        
    def base_callback(event: BaseEvent):
        received_base.append("base")
        
    emitter.subscribe(StepStarted, specific_callback)
    emitter.subscribe(BaseEvent, base_callback)
    
    emitter.emit(StepStarted(step_name="test", step_index=1))
    
    assert received_specific == ["specific"]
    assert received_base == ["base"]
    # AC4: All subscribers for that specific event type are invoked first, followed by all BaseEvent catch-all subscribers.
    # We can't easily check order without a shared list.
    
    received_all = []
    def specific_callback_ordered(event: StepStarted): received_all.append("specific")
    def base_callback_ordered(event: BaseEvent): received_all.append("base")
    
    emitter = EventEmitter()
    emitter.subscribe(StepStarted, specific_callback_ordered)
    emitter.subscribe(BaseEvent, base_callback_ordered)
    emitter.emit(StepStarted(step_name="test", step_index=1))
    assert received_all == ["specific", "base"]

def test_deduplicate_subscribers_across_types():
    # If a callback is in BOTH specific and catch-all, it should be called only once
    emitter = EventEmitter()
    received = []
    def callback(event: StepStarted): received.append("called")
    
    emitter.subscribe(StepStarted, callback)
    emitter.subscribe(BaseEvent, callback)
    
    emitter.emit(StepStarted(step_name="test", step_index=1))
    assert received == ["called"]

def test_unsubscribe():
    emitter = EventEmitter()
    received = []
    def callback(event: StepStarted): received.append(event)
    
    emitter.subscribe(StepStarted, callback)
    emitter.unsubscribe(StepStarted, callback)
    emitter.emit(StepStarted(step_name="test", step_index=1))
    assert len(received) == 0

def test_unsubscribe_all():
    emitter = EventEmitter()
    received = []
    def callback(event: BaseEvent): received.append(event)
    
    emitter.subscribe(StepStarted, callback)
    emitter.subscribe(StepCompleted, callback)
    emitter.unsubscribe_all(callback)
    
    emitter.emit(StepStarted(step_name="test", step_index=1))
    emitter.emit(StepCompleted(step_name="test", step_index=1, success=True))
    assert len(received) == 0

def test_invalid_event_type_subscription():
    emitter = EventEmitter()
    with pytest.raises(TypeError):
        emitter.subscribe(str, lambda x: None) # type: ignore


def test_subscribe_rejects_non_class_event_type():
    # Passing a non-class value should raise TypeError with a clear message
    emitter = EventEmitter()
    with pytest.raises(TypeError, match="must be BaseEvent or a subclass"):
        emitter.subscribe(42, lambda x: None)  # type: ignore

def test_invalid_event_emission():
    emitter = EventEmitter()
    with pytest.raises(TypeError):
        emitter.emit("not an event") # type: ignore

def test_subscriber_isolation(caplog):
    emitter = EventEmitter()
    def failing_callback(event: StepStarted):
        raise ValueError("Boom")
        
    received = []
    def working_callback(event: StepStarted):
        received.append(event)
        
    emitter.subscribe(StepStarted, failing_callback)
    emitter.subscribe(StepStarted, working_callback)
    
    with caplog.at_level(logging.WARNING):
        emitter.emit(StepStarted(step_name="test", step_index=1))
        
    assert len(received) == 1
    assert "failing_callback" in caplog.text
    assert "StepStarted" in caplog.text
    assert "bmad_orch.engine.emitter" in caplog.records[0].name


def test_unsubscribe_nonexistent_is_silent_noop():
    # AC7: Attempting to unsubscribe a non-existent callback is a silent no-op
    emitter = EventEmitter()
    def callback(event: StepStarted): pass
    # Should not raise
    emitter.unsubscribe(StepStarted, callback)
