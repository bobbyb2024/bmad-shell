---
status: done
epic: 3
stepsCompleted: []
---

# Story 3.1: Event Emitter & Event Types

## Story

As a **developer**,
I want **a typed event system that decouples the engine from all presentation layers**,
so that **renderers can subscribe to engine events without the engine knowing or caring which renderers exist**.

## Acceptance Criteria

1. **AC1: Event Definitions** — Given the `engine/events.py` module, when I inspect the event types, then it defines frozen dataclasses for all events listed in the **Event Field Specifications** table. All event types inherit from `BaseEvent` (which should be an abstract base class via `abc.ABC`). `BaseEvent` carries a `timestamp: float` field using `field(default_factory=time.time)`.
2. **AC2: Event Immutability** — Given any event dataclass, when I attempt to mutate a field after creation, then it raises `FrozenInstanceError` (using `@dataclass(frozen=True)`).
3. **AC3: Subscription Mechanism** — Given the `EventEmitter` in `engine/emitter.py`, when I call `subscribe(event_type, callback)`, then the callback is registered. The `event_type` must be `BaseEvent` or a subclass of `BaseEvent`; subscribing to other types is a `TypeError`. Callback signature: `Callable[[BaseEvent], None]`. If the same callback (verified by identity `is` for functions/methods) is subscribed to the same event type multiple times, the duplicate is ignored (idempotent subscription).
4. **AC4: Event Emission** — Given an `EventEmitter`, when I call `emit(event)`, then it first validates `event` is an instance of `BaseEvent` (raising `TypeError` otherwise). All subscribers for that specific event type are invoked first (in registration order), followed by all `BaseEvent` catch-all subscribers (in registration order). `emit` is a regular synchronous method.
5. **AC5: Subscriber Isolation** — Given a subscriber that raises an exception, when an event is emitted, then the `EventEmitter` catches the exception, logs a warning including the subscriber name and event type (logger: `bmad_orch.engine.emitter`), and continues to remaining subscribers.
6. **AC6: Engine Decoupling** — Given the `EventEmitter`, when I inspect its imports, then it accepts `Callable` subscribers and never imports from `rendering/`.
7. **AC7: Unsubscribe Mechanism** — Given a registered subscriber, when I call `unsubscribe(event_type, callback)`, then the callback is removed. Attempting to unsubscribe a non-existent callback is a silent no-op. Additionally, `unsubscribe_all(callback)` removes the callback from all event types. Implementation should favor O(1) or O(log N) lookup for `unsubscribe_all` (e.g., via a subscriber-to-types mapping).

## Tasks / Subtasks

- [x] Task 1: Define Event Dataclasses (AC: 1, 2)
  - [x] 1.1: Create `src/bmad_orch/engine/events.py`.
  - [x] 1.2: Implement `BaseEvent` (ABC) and all event types as `@dataclass(frozen=True)`.
  - [x] 1.3: Define Enums as `IntEnum` for `EscalationLevel` (`OK`, `ATTENTION`, `ACTION`) and `LogLevel` (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).
- [x] Task 2: Implement Event Emitter (AC: 3, 4, 5, 6, 7)
  - [x] 2.1: Create `src/bmad_orch/engine/emitter.py`.
  - [x] 2.2: Implement `EventEmitter` with idempotent `subscribe` (using identity checks), `unsubscribe`, `unsubscribe_all`, and `emit`. `subscribe` and `emit` must validate `BaseEvent` types.
  - [x] 2.3: Implement `BaseEvent` catch-all subscription logic in `emit`.
  - [x] 2.4: Implement error isolation with logging in `emit`.
- [x] Task 3: Package Export
  - [x] 3.1: Update `src/bmad_orch/engine/__init__.py` to import and export `EventEmitter`, `BaseEvent`, Enums, and all event types via `__all__`. Use relative imports.
  - [x] 3.2: Create `tests/test_engine/__init__.py`.
- [x] Task 4: Unit Testing (AC: 1-7)
  - [x] 4.1: Create `tests/test_engine/test_events.py` to verify immutability and Enum usage.
  - [x] 4.2: Create `tests/test_engine/test_emitter.py` to verify subscription order, idempotency, `BaseEvent` catch-all ordering, error isolation (including verification of logger name `bmad_orch.engine.emitter` and warning content), `unsubscribe`, `unsubscribe_all`, and `TypeError` on invalid types.

## Dev Notes

- **Architecture Pattern:** Engine-to-presentation decoupling via observer pattern.
- **Async Safety:** `emit` is a plain `def` (not `async def`) — synchronous to ensure deterministic ordering. Subscribers must not perform blocking I/O; if they need to, they should schedule a task via `asyncio.get_event_loop().create_task()`. Concurrency safety relies on single-threaded async confinement (no locks needed as long as `emit` is only called from the event loop thread).
- **Dependency Isolation:** `src/bmad_orch/engine/` must NEVER import from `src/bmad_orch/rendering/`.
- **BaseEvent:** Abstract base class for all events. Subscribing to `BaseEvent` acts as a "global" listener. Invocation order: type-specific subscribers fire first (registration order), then `BaseEvent` catch-all subscribers (registration order).
- **Callback Signature:** `Callable[[Any], None]` may be used internally to satisfy type checkers when subscribers expect specific subclasses, but the public API should specify `BaseEvent`.
- **Test Naming:** Use descriptive behavior names (`test_emit_delivers_to_type_specific_subscribers`) consistent with the existing codebase. Map tests to ACs via comments, not function name prefixes.

### Event Field Specifications

| Event Type | Fields (in addition to `timestamp: float`) |
|---|---|
| `BaseEvent` | `timestamp: float` (Defined in base) |
| `StepStarted` | `step_name: str`, `step_index: int` |
| `StepCompleted` | `step_name: str`, `step_index: int`, `success: bool` |
| `CycleStarted` | `cycle_number: int`, `provider_name: str` |
| `CycleCompleted` | `cycle_number: int`, `provider_name: str`, `success: bool` |
| `EscalationChanged` | `previous_level: Optional[EscalationLevel]`, `new_level: EscalationLevel` |
| `LogEntry` | `level: LogLevel`, `message: str`, `source: str` |
| `ProviderOutput` | `provider_name: str`, `content: str`, `is_partial: bool` (True = streaming chunk, False = complete response) |
| `RunCompleted` | `success: bool`, `total_cycles: int`, `error_count: int` |
| `ErrorOccurred` | `error_type: str`, `message: str`, `source: str`, `recoverable: bool` |
| `ResourceThresholdBreached` | `resource_name: str`, `current_value: float`, `threshold: float` |

### Project Structure Notes

- New File: `src/bmad_orch/engine/events.py`
- New File: `src/bmad_orch/engine/emitter.py`
- Update: `src/bmad_orch/engine/__init__.py` (currently empty — needs exports added)
- New File: `tests/test_engine/__init__.py` (empty package init)
- New File: `tests/test_engine/test_events.py`
- New File: `tests/test_engine/test_emitter.py`

### Previous Story Intelligence

- **From Story 2.4:**
  - Use `BmadOrchError` hierarchy where applicable.
  - Use descriptive behavior-based test names (e.g., `test_subscribe_rejects_non_event_type`). Map to ACs via docstrings or comments, not name prefixes. This aligns with existing test conventions in `tests/test_providers/`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Engine Architecture]

## Dev Agent Record

### Agent Model Used

Gemini 2.0 Flash

### Debug Log References

- [2026-03-14] Starting implementation of Story 3.1.

### Completion Notes List

- Implemented typed event system using `BaseEvent` (ABC) and frozen dataclasses.
- Implemented `EventEmitter` with idempotent subscription, prioritized emission, and error isolation.
- Exported all engine components via `src/bmad_orch/engine/__init__.py`.
- Added comprehensive unit tests in `tests/test_engine/`.
- [AI-Review] Deduplicated subscribers in `emit` to prevent double-notification when subscribed to multiple matching types.
- [AI-Review] Enhanced subscriber error logging with full traceback support.
- [AI-Review] Refactored tests to verify public API exports in `src/bmad_orch/engine/__init__.py`.

### File List

- `src/bmad_orch/engine/events.py`
- `src/bmad_orch/engine/emitter.py`
- `src/bmad_orch/engine/__init__.py`
- `tests/test_engine/__init__.py`
- `tests/test_engine/test_events.py`
- `tests/test_engine/test_emitter.py`

## Change Log

- [2026-03-14] Initial implementation of Story 3.1: Event Emitter & Event Types.
- [2026-03-14] Code Review: Added deduplication, enhanced logging, and refactored tests for public API verification.
