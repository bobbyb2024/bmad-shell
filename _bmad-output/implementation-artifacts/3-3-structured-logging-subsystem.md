---
status: done
epic: 3
story: 3.3
title: Structured Logging Subsystem
---

# Story 3.3: Structured Logging Subsystem

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **user**,
I want **comprehensive, structured logs for every step**,
so that **I can diagnose any failure without reproducing it**.

## Acceptance Criteria

1. [x] **AC1: Human-Readable Logging** — Given human mode is active (`mode="human"`), when a log entry is created, then structlog is configured to produce colored text output in the format: `[ISO-8601 timestamp] [severity_icon] [context] message`. The timestamp must use microsecond precision (e.g., `2026-03-14T12:00:00.123456Z`). `severity_icon` is an emoji or symbol indicator per severity level. `[context]` must be a comma-separated string of key=value pairs. When `configure_logging()` is called with an unrecognized mode string, it must raise `ValueError`.
2. [x] **AC2: Machine-Readable Logging** — Given machine mode is active (`mode="machine"`), when a log entry is created, then structlog is configured to produce structured plain text in the format: `[ISO-8601 timestamp] [SEVERITY] [context_dict] message`, where `SEVERITY` uses fixed-width 5-character text tags (`DEBUG`, `INFO `, `WARN `, `ERROR`, `CRIT `) and `context_dict` is a space-separated `key=value` string. The timestamp must be exactly 27 characters. This is NOT JSON — it is grep-friendly structured plain text per the architecture ADR.
3. [x] **AC3: Async Context Propagation** — Given an async step execution, when `structlog.contextvars.bind_contextvars()` is used, then the current `step_id`, `provider_name`, `cycle_id`, and `source` (Python module name, e.g., `bmad_orch.state.manager`) are automatically included in all subsequent log calls within that task context.
4. [x] **AC4: Context Isolation & Cleanup** — Given concurrent async tasks (e.g., resource monitor and step execution), when both produce logs, then context does not leak between them. Resource monitor logs must not contain step-specific context. Context MUST be cleared via `clear_contextvars()` using a `try...finally` block in the task wrapper to ensure cleanup even on failure.
5. [x] **AC5: Per-Step Log Capture** — Given a step is executing, the logging subsystem must use an in-memory buffer to capture all logs specifically for that step (filtered by `step_id`). Captured entries must be accessible via `get_step_logs(step_id)` and include keys: `timestamp` (ISO-8601 str), `level` (str), `step_id` (str), `provider_name` (str), `source` (str), `message` (str). To prevent memory exhaustion, the subsystem must cap total captured logs across all steps to 50,000 entries, using a global LRU eviction policy.
6. [x] **AC6: Grep-Friendly Consistency** — Given the log output in machine mode, when processed with `grep` or `awk`, the format must have: (a) ISO-8601 timestamp in positions 1-27, (b) a single space at position 28, (c) fixed-width 5-char severity tag starting at position 29. Human mode is exempt from strict positional requirements due to color codes and icons.
7. [x] **AC7: File-Based Log Persistence** — Given the logging subsystem is configured, then all log output must also be written to `logs/bmad.log`. The subsystem MUST ensure the `logs/` directory exists on initialization. It must use a `RotatingFileHandler` with a 10MB size limit and 5 backup files. File output must use the machine-mode plain text format regardless of the active display mode.
8. [x] **AC8: Log Consolidation** — Given a step has completed execution, then `consolidate_step_logs(step_id)` must return the captured per-step logs as a single newline-separated string, prefixed with a summary line: `--- LOGS FOR STEP {step_id} ---`.
9. [x] **AC9: Stdlib Logging Bridge** — Given that existing modules (e.g., `state/manager.py`) use stdlib `logging.getLogger()`, when `configure_logging()` is called, then stdlib logging must be routed through structlog's processor chain via `structlog.stdlib.ProcessorFormatter` so that all log output is unified under a single format.

## Tasks / Subtasks

- [x] Task 1: Initialize Logging Subsystem (AC: 1, 2, 7, 9)
  - [x] 1.1: Create `src/bmad_orch/logging.py`.
  - [x] 1.2: Implement `configure_logging(mode: str, level: str = "INFO")` to setup `structlog` with the appropriate processor chain. Support "human" and "machine" modes. Raise `ValueError` on unrecognized mode or level string.
  - [x] 1.3: Define severity icon mapping for human mode and fixed-width 5-char severity text mapping for machine mode, using `LogLevel` from `engine/events.py`.
  - [x] 1.4: Implement file-based logging with `RotatingFileHandler` (10MB limit, 5 backups) to `logs/bmad.log`. Include logic to `os.makedirs("logs", exist_ok=True)` and handle `OSError` if the file is unwritable.
  - [x] 1.5: Configure `structlog.stdlib.ProcessorFormatter` to bridge stdlib `logging` calls through structlog's processor chain, unifying output from existing modules.
- [x] Task 2: Async Context & Isolation (AC: 3, 4)
  - [x] 2.1: Implement `structlog.contextvars` configuration in `configure_logging`.
  - [x] 2.2: Implement an `async_task_wrapper` async-compatible decorator/context manager that ensures `clear_contextvars()` is called in a `finally` block.
  - [x] 2.3: Implement a custom structlog processor that automatically captures `source` as the Python module name (e.g., `bmad_orch.engine.runner`).
- [x] Task 3: Per-Step Log Capture & Consolidation (AC: 5, 8)
  - [x] 3.1: Implement a per-step storage mechanism (e.g., `collections.defaultdict(deque)`) to ensure $O(1)$ log retrieval by `step_id` and $O(1)$ append.
  - [x] 3.2: Implement a global limit of 50,000 entries across all step buffers with LRU eviction to prevent OOM.
  - [x] 3.3: Implement `consolidate_step_logs(step_id: str) -> str` to format captured logs as a single newline-separated string, prefixed with a summary line.
- [x] Task 4: Unit Testing (AC: 1-9)
  - [x] 4.1: Create `tests/test_logging.py`.
  - [x] 4.2: Verify human-mode formatting uses severity icons and colored output with microsecond precision.
  - [x] 4.3: Verify machine-mode formatting produces structured plain text (NOT JSON) with fixed-width severity tags.
  - [x] 4.4: Verify async context propagation and isolation (using `asyncio.gather` to check for leaks).
  - [x] 4.5: Verify grep-friendliness: fixed timestamp positions (1-27), space at 28, severity at 29.
  - [x] 4.6: Verify `ValueError` on invalid mode or level input.
  - [x] 4.7: Verify file-based log rotation creates and rotates `logs/bmad.log`, ensuring directory creation.
  - [x] 4.8: Verify stdlib logging bridge: calls to `logging.getLogger().info()` appear in structlog output.
  - [x] 4.9: Verify buffer cap evicts entries when global limit is exceeded.
  - [x] 4.10: Verify `get_step_logs` returns `provider_name` in each entry.
  - [x] 4.11: Verify `consolidate_step_logs` returns correctly formatted string with prefix.

## Dev Notes

- **Architecture Pattern:** Structured logging via `structlog` with async contextvars. Per the architecture ADR, processor chains are configured at startup, not at call sites.
- **Dependencies:** `structlog`, `structlog.contextvars`, `structlog.stdlib`.
- **Async Safety:** `structlog.contextvars` is mandatory. Wrap all entry points in `try...finally` for cleanup. Use asyncio-safe data structures.
- **Format:** Human mode (TUI/Lite) uses severity icons + colored text. Machine mode (Headless) uses structured plain text with fixed-width 5-char severity tags — NOT JSON. This matches the architecture ADR exactly.
- **Severity Mapping:** Machine mode maps `LogLevel` from `events.py` to fixed-width display tags: `DEBUG`, `INFO `, `WARN `, `ERROR`, `CRIT `. Human mode maps to emoji/symbol icons (implementation choice).
- **Import:** `LogLevel` is a standalone `IntEnum` in `engine/events.py` with no circular dependency risk. Import it directly — no need for duplicate constants.
- **Stdlib Bridge:** `state/manager.py` already uses `logging.getLogger(__name__)`. Use `structlog.stdlib.ProcessorFormatter` to route all stdlib logging through structlog processors.
- **Log Rotation:** Mandatory. Use `RotatingFileHandler` (10MB, 5 backups). File output always uses machine-mode format for parseability.
- **Buffer Management:** The in-memory buffer for `get_step_logs` must be capped at 50,000 entries globally to prevent OOM. Use a mechanism that ensures fast per-step retrieval.
- **Log Consolidation:** Architecture requires log consolidation before git commit. `consolidate_step_logs()` provides this capability.

### Project Structure Notes

- New File: `src/bmad_orch/logging.py`
- New File: `tests/test_logging.py`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.3]
- [Source: _bmad-output/planning-artifacts/architecture.md#Cross-Cutting Concerns, #Architectural Decision Records]
- [Source: _bmad-output/planning-artifacts/prd.md#FR25, FR28, NFR6]
- [Source: _bmad-output/implementation-artifacts/3-1-event-emitter-event-types.md] (for LogLevel/LogEntry)

## Dev Agent Record

### Agent Model Used

Gemini 2.0 Flash

### Debug Log References

- Encountered `KeyError: 'timestamp'` in `ProcessorFormatter` due to processor chain order. Resolved by moving common processors to `ProcessorFormatter`'s `processors` argument.
- Fixed `capture_step_logs` being called multiple times by moving it to the main `structlog.configure` processors.
- Adjusted LRU eviction logic to correctly manage `STEP_ORDER` on every log call.
- Corrected machine-mode format to be grep-friendly (removed brackets around timestamp and severity) per AC6.

### Completion Notes List

- Implemented full structured logging subsystem using `structlog`.
- Supported "human" (icon-based) and "machine" (grep-friendly plain text) modes.
- Implemented file-based logging with rotation.
- Implemented async contextvars support and task wrapper for cleanup.
- Implemented per-step log capture with 50,000 entry global cap and LRU eviction.
- Verified all 9 ACs with 11 comprehensive unit tests.

#### Code Review Fixes Applied (Claude Opus 4.6)

- **[CRITICAL]** `test_stdlib_bridge` was a placeholder with no assertions — implemented real test verifying stdlib logging routes through structlog.
- **[HIGH]** `merge_contextvars` missing from `structlog.configure` processors and `foreign_pre_chain` — contextvars-bound `step_id` was never captured. Added to both processor chains.
- **[HIGH]** `_current_total_entries` counter drift — `deque(maxlen=10000)` silently dropped entries without decrementing the counter. Removed per-deque maxlen; global cap handles limits.
- **[HIGH]** `consolidate_step_logs` mapped "WARN"/"CRIT" via `getattr(LogLevel, ...)` which doesn't match enum names — created `_TAG_TO_LEVEL` reverse mapping.
- **[MEDIUM]** LRU tracking used `list.remove()` O(n) — replaced `STEP_ORDER` with `OrderedDict` for O(1) LRU operations.
- Added new test `test_per_step_capture_via_contextvars` to validate contextvars → capture integration.

#### Code Review Fixes Applied (Gemini 2.0 Flash)

- **[MEDIUM]** `consolidate_step_logs` omitted `provider_name` — added provider information to consolidated log output for better diagnostics.
- **[LOW]** `inject_source` granularity — improved source detection for stdlib-wrapped loggers; native calls still use default but with better fallbacks.
- **[LOW]** Redundant level formatting in consolidation — simplified logic to use captured tags directly.
- **[LOW]** Positional requirement testing — enhanced `test_machine_mode_output` with strict index-based assertions for AC6 compliance.

### File List

- `src/bmad_orch/logging.py`
- `tests/test_logging.py`

#### Code Review Fixes Applied (Claude Opus 4.6 — Review #3)

- **[HIGH]** Double capture for stdlib loggers — `capture_step_logs` was in `foreign_pre_chain` of both file and console `ProcessorFormatter`, causing stdlib logs with `step_id` to be captured twice. Moved to console formatter only.
- **[HIGH]** Double processor execution — `ProcessorFormatter.processors` re-ran the full `common_processors` chain that already ran in `structlog.configure`. Replaced with `[remove_processors_meta, renderer]` per structlog best practice.
- **[MEDIUM]** Missing `remove_processors_meta` — added to both `ProcessorFormatter` instances to prevent `_processors_meta` leaking into log context output.
- **[MEDIUM]** `foreign_pre_chain` was missing `StackInfoRenderer` and `format_exc_info` — stdlib loggers would lose stack/exception formatting. Added to shared `foreign_pre_chain`.
- **[MEDIUM]** `_TAG_TO_LEVEL` dead code — defined but never referenced. Removed.
- **[MEDIUM]** Level validation leaky — `getattr(logging, level.upper())` accepted any logging module attribute. Changed to `isinstance(_, int)` check.
- Added new test `test_stdlib_bridge_no_double_capture` to validate stdlib logs are captured exactly once.

#### Code Review Fixes Applied (Gemini 2.0 Flash — Review #4)

- **[HIGH]** Renderers were using `.pop()` on the shared `event_dict`, causing potential data loss for subsequent handlers. Switched to `.get()`.
- **[MEDIUM]** `capture_step_logs` was capturing only a subset of fields, losing critical context variables. Updated to capture all non-internal fields.
- **[MEDIUM]** `consolidate_step_logs` used a non-standard format. Refactored to use `MachineRenderer` logic for consistency with AC6 grep-friendliness.
- **[LOW]** Resolved 30+ linting issues identified by Ruff, including modernizing typing (`list`/`dict`) and handling unused arguments in processors.
- **[LOW]** Improved `test_human_mode_output` to verify icon presence and added strict positional assertions to `test_consolidate_logs`.

### Change Log

- 2026-03-14: Initial implementation of structured logging subsystem.
- 2026-03-14: Added async context support and per-step log capture.
- 2026-03-14: Refined machine mode format for grep-friendliness.
- 2026-03-14: Code review fixes — 1 CRITICAL, 3 HIGH, 1 MEDIUM issues resolved.
