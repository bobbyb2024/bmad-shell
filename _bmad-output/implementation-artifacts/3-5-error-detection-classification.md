# Story 3.5: Error Detection & Classification

Status: ready-for-dev

## Story

As a user,
I want errors automatically classified and handled appropriately,
so that transient issues are retried silently while serious failures are surfaced clearly.

## Acceptance Criteria

1. **Given** a provider returns a rate limit error (HTTP 429 or equivalent CLI error)
   **When** the error classification system evaluates it
   **Then** it is classified as `RECOVERABLE` with severity `ProviderTimeoutError`

2. **Given** a recoverable error during step execution
   **When** the error handling logic processes it
   **Then** the error is logged with full context and execution continues to the next retry or step
   **And** the user sees nothing unless they inspect logs

3. **Given** a provider subprocess crash (unexpected termination, OOM kill)
   **When** the error classification system evaluates it
   **Then** it is classified as `IMPACTFUL` with severity `ProviderCrashError`

4. **Given** an impactful error
   **When** the error handling logic processes it
   **Then** an `ErrorOccurred` event is emitted with the error details, classification, and suggested next action

5. **Given** an error with structured context
   **When** it is logged
   **Then** the log entry follows the format `✗ [What happened] — [What to do next]` and includes the error classification, provider name, step identifier, and timestamp

6. **Given** the error classification system
   **When** I inspect the implementation
   **Then** the engine checks `error.severity` (the `ErrorSeverity` enum), not `isinstance()` checks against exception subclasses

## Dev Notes

- **Architecture Rules:** Ensure zombie process cleanup is adhered to! Every error path, cancellation path, and timeout handler must explicitly call `process.kill()` + `await process.wait()`. No subprocess reference may be discarded without cleanup.
- **Events:** All event dataclasses must be immutable (`@dataclass(frozen=True)`). Emit `ErrorOccurred` event properly with required details on impactful errors.
- **Logging Subsystem:** Using structlog. Ensure the log format strictly follows `✗ [What happened] — [What to do next]`. Use `structlog.contextvars` to attach the context, like error classification, provider name, step identifier, and timestamp.
- **Error Checking:** The system should inspect `error.severity` (using `ErrorSeverity` enum) to classify the error, rather than using `isinstance()` checks against specific error subclasses. This enforces abstraction over standard exception types.

### Previous Story Intelligence

- **Logging Teardown:** Remember that when logging within step blocks, use `unbind_contextvars("step_name", "provider_name")` in the inner `finally` block.
- **Cycle Execution:** The `CycleExecutor` was introduced in Story 3.4. Update it or ensure it integrates tightly with this new error classification subsystem when checking for step success or failure. Error detection should likely be hooked into or called by the step execution placeholder in `CycleExecutor`.

### References

- [Source: Epic 3 - Core Cycle Engine]
- [Source: Core Architectural Decisions - Zombie process cleanup]
- [Source: Core Architectural Decisions - Structured Logging]

## Dev Agent Record

### Agent Model Used



### Debug Log References

### Completion Notes List

### File List
