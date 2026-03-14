# Implementation Guidance

## Public API to implement in `src/bmad_orch/logging.py`:

- `configure_logging(mode: str, level: str = "INFO") -> None`
- `get_step_logs(step_id: str) -> list[dict[str, str]]`
- `consolidate_step_logs(step_id: str) -> str`
- `async_task_wrapper()` — async context manager for contextvars cleanup

## Key constraints:

- Import `LogLevel` from `engine/events.py` — no duplicate constants
- Use `structlog.contextvars` for async context propagation
- Machine mode: structured plain text, NOT JSON
- File output: always machine-mode format via `RotatingFileHandler` (10MB, 5 backups)
- Buffer: 50,000 global entry cap with LRU eviction
- Stdlib bridge: `structlog.stdlib.ProcessorFormatter`
