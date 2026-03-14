# Tasks / Subtasks

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
