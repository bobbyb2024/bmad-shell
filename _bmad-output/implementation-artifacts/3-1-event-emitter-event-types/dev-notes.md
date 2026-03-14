# Dev Notes

- **Architecture Pattern:** Engine-to-presentation decoupling via observer pattern.
- **Async Safety:** `emit` is a plain `def` (not `async def`) — synchronous to ensure deterministic ordering. Subscribers must not perform blocking I/O; if they need to, they should schedule a task via `asyncio.get_event_loop().create_task()`. Concurrency safety relies on single-threaded async confinement (no locks needed as long as `emit` is only called from the event loop thread).
- **Dependency Isolation:** `src/bmad_orch/engine/` must NEVER import from `src/bmad_orch/rendering/`.
- **BaseEvent:** Abstract base class for all events. Subscribing to `BaseEvent` acts as a "global" listener. Invocation order: type-specific subscribers fire first (registration order), then `BaseEvent` catch-all subscribers (registration order).
- **Callback Signature:** `Callable[[Any], None]` may be used internally to satisfy type checkers when subscribers expect specific subclasses, but the public API should specify `BaseEvent`.
- **Test Naming:** Use descriptive behavior names (`test_emit_delivers_to_type_specific_subscribers`) consistent with the existing codebase. Map tests to ACs via comments, not function name prefixes.

## Event Field Specifications

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

## Project Structure Notes

- New File: `src/bmad_orch/engine/events.py`
- New File: `src/bmad_orch/engine/emitter.py`
- Update: `src/bmad_orch/engine/__init__.py` (currently empty — needs exports added)
- New File: `tests/test_engine/__init__.py` (empty package init)
- New File: `tests/test_engine/test_events.py`
- New File: `tests/test_engine/test_emitter.py`

## Previous Story Intelligence

- **From Story 2.4:**
  - Use `BmadOrchError` hierarchy where applicable.
  - Use descriptive behavior-based test names (e.g., `test_subscribe_rejects_non_event_type`). Map to ACs via docstrings or comments, not name prefixes. This aligns with existing test conventions in `tests/test_providers/`.

## References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Engine Architecture]
