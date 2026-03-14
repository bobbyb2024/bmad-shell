# Story 2.2: Claude CLI Adapter

Status: ready-for-dev

## Story

As a **user**,
I want **the orchestrator to invoke Claude CLI with my configured prompts**,
so that **Claude can execute generative and validation steps in my workflows**.

## Acceptance Criteria

1. **AC1: Claude CLI Detection** — Given the Claude CLI is installed on the host, when `ClaudeAdapter.detect()` is called, then it returns `True`.
2. **AC2: Claude Model Listing** — Given a detected Claude CLI, when `ClaudeAdapter.list_models()` is called, then it returns the list of available models from the Claude CLI (e.g., by running `claude models` or equivalent).
3. **AC3: Prompt Execution** — Given a valid prompt and model configuration, when `ClaudeAdapter.execute(prompt)` is called, then the Claude CLI is invoked as an async subprocess via PTY with the configured model and prompt.
4. **AC4: Output Streaming** — Given a running Claude subprocess, then stdout is streamed as `OutputChunk` objects via `AsyncIterator` in real-time.
5. **AC5: Successful Completion** — Given a running Claude subprocess, when it completes successfully, then the adapter detects completion and yields a final `OutputChunk` with completion status.
6. **AC6: Failure Handling** — Given a running Claude subprocess, when it times out or terminates unexpectedly (crash, OOM, signal), then the adapter detects the failure, calls `process.kill()` + `await process.wait()`, and raises `ProviderCrashError` or `ProviderTimeoutError` with exit code context.
7. **AC7: Defensive Parsing** — Given a running Claude subprocess, when the CLI output format is unrecognizable, then the adapter parses defensively and raises an explicit error rather than silently producing garbage output.

## Tasks / Subtasks

- [ ] Task 1: Implement Claude Adapter (AC: 1, 2, 3)
  - [ ] 1.1: Create `src/bmad_orch/providers/claude.py` inheriting from `ProviderAdapter`.
  - [ ] 1.2: Implement `detect()` using `shutil.which`.
  - [ ] 1.3: Implement `list_models()` by querying the CLI.
- [ ] Task 2: Implement Execution Logic (AC: 4, 5, 6, 7)
  - [ ] 2.1: Implement `execute(prompt: str)` using the PTY utility.
  - [ ] 2.2: Handle subprocess lifecycle: ensure `process.kill()` on error/timeout.
  - [ ] 2.3: Map subprocess exit codes to `ProviderError` subclasses.
- [ ] Task 3: Write comprehensive tests (AC: 1-7)
  - [ ] 3.1: Create `tests/test_providers/test_claude.py`.
  - [ ] 3.2: Mock Claude CLI binary to test detection and model listing.
  - [ ] 3.3: Mock subprocess execution to test streaming, success, and failure paths.

## Dev Notes

- **Claude CLI:** Target the official Anthropic Claude CLI.
- **PTY:** Use the `read_pty_output` utility established in Story 2.1.
- **Async:** Entire execution path must be non-blocking.

### Project Structure Notes

- New file: `src/bmad_orch/providers/claude.py`.
- Update: `src/bmad_orch/providers/__init__.py` to register `ClaudeAdapter`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic-2, Story 2.2]
- [Source: _bmad-output/planning-artifacts/prd.md — FR12a, FR12b, FR12c]

## Dev Agent Record

### Agent Model Used

Gemini 2.0 Flash

### Debug Log References

### Completion Notes List

### File List

- `src/bmad_orch/providers/claude.py`
- `src/bmad_orch/providers/__init__.py` (updated)
- `tests/test_providers/test_claude.py`
