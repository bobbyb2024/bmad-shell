# Dev Notes

- **Architecture Rules:** Provider subprocess invocation must be isolated — a hung or misbehaving provider must not block the orchestrator. The PTY path uses `os.openpty()` with `asyncio` loop monitoring (e.g., `add_reader`) for non-blocking reads. This avoids the thread-safety and fork-safety issues associated with `pty.fork()`.
- **PTY Capture:** The `spawn_pty_process` utility must handle the full lifecycle to avoid "input is not a TTY" errors from CLIs like `gh` or `gcloud`. It should use `os.openpty()` and correctly set up the slave FD as the subprocess's terminal.
- **PTY stdout/stderr merging:** A PTY combines stdout and stderr into a single stream on the master fd. `OutputChunk` therefore does **not** carry a `stream_type` field — all output is treated as a unified terminal stream.
- **Timeout & Crash Detection:** `spawn_pty_process` handles timeout enforcement by sending `SIGTERM` (and `SIGKILL` if necessary) to the subprocess group. It raises `ProviderTimeoutError` on timeout and `ProviderCrashError` on non-zero exit codes.
- **Error Severity:** Every exception must be catchable by its severity level to allow for different UI responses (e.g., BLOCKING shows a modal, RECOVERABLE shows a toast, WARNING shows a non-intrusive notification).
- **Dependency isolation:** `providers` should never import from `engine`.
- **Deferred:** Concrete `ClaudeAdapter` and `GeminiAdapter` implementations are in Stories 2.2 and 2.3.
- **PTY ↔ execute() integration:** The `spawn_pty_process` utility is a helper; concrete adapters (Stories 2.2/2.3) will call it from their `execute()` implementations. Each adapter is responsible for converting a `prompt: str` into a `cmd: list[str]` before calling `spawn_pty_process`.
- **Singleton Pattern:** The registry manages adapters as singletons by default to avoid redundant resource allocation, but supports passing configuration during initial instantiation.

## Project Structure Notes

- Naming: `snake_case` for files and variables, `PascalCase` for classes.
- Location: All provider logic stays within `src/bmad_orch/providers/`.

## FR Traceability

| AC | Functional Requirements |
|----|------------------------|
| AC1 | FR10 (provider interface) |
| AC2 | FR11 (CLI detection) |
| AC3 | FR12a (model listing) |
| AC4 | FR12b (adapter registry) |
| AC5 | FR12b (adapter registry — uniqueness), FR13 (ProviderNotFoundError) |
| AC6 | FR10 (PTY output capture — supporting infrastructure) |
| AC7 | FR13 (error handling — exception hierarchy & severity) |

## References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic-2, Story 2.1]
- [Source: _bmad-output/planning-artifacts/prd.md — FR10, FR11, FR12a, FR12b, FR13]
- [Source: _bmad-output/planning-artifacts/architecture.md — Section "Provider Detection & Execution"]
