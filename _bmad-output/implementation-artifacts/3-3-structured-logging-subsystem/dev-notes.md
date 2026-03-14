# Dev Notes

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

## Project Structure Notes

- New File: `src/bmad_orch/logging.py`
- New File: `tests/test_logging.py`

## References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.3]
- [Source: _bmad-output/planning-artifacts/architecture.md#Cross-Cutting Concerns, #Architectural Decision Records]
- [Source: _bmad-output/planning-artifacts/prd.md#FR25, FR28, NFR6]
- [Source: _bmad-output/implementation-artifacts/3-1-event-emitter-event-types.md] (for LogLevel/LogEntry)
