# Story 2.3: Gemini CLI Adapter

Status: ready-for-dev

## Story

As a **user**,
I want **the orchestrator to invoke Gemini CLI with my configured prompts**,
so that **Gemini can execute validation steps and provide adversarial review in my workflows**.

## Acceptance Criteria

1. **AC1: Gemini CLI Detection** — Given the Gemini CLI is installed on the host, when `GeminiAdapter.detect()` is called, then it returns `True`.
2. **AC2: Gemini Model Listing** — Given a detected Gemini CLI, when `GeminiAdapter.list_models()` is called, then it returns the list of available models from the Gemini CLI.
3. **AC3: Prompt Execution** — Given a valid prompt and model configuration, when `GeminiAdapter.execute(prompt)` is called, then the Gemini CLI is invoked as an async subprocess via PTY with the configured model and prompt.
4. **AC4: Output Streaming** — Given a running Gemini subprocess, stdout is streamed as `OutputChunk` objects via `AsyncIterator` in real-time.
5. **AC5: Successful Completion** — Given a running Gemini subprocess, when it completes successfully, then the adapter detects completion and yields a final `OutputChunk` with completion status.
6. **AC6: Failure Handling** — Given a running Gemini subprocess, when it times out or terminates unexpectedly, then the adapter detects the failure, calls `process.kill()` + `await process.wait()`, and raises the appropriate `ProviderError` subclass.
7. **AC7: Defensive Parsing** — Given a running Gemini subprocess, when the CLI output format is unrecognizable, then the adapter parses defensively and raises an explicit error.

## Tasks / Subtasks

- [ ] Task 1: Implement Gemini Adapter (AC: 1, 2, 3)
  - [ ] 1.1: Create `src/bmad_orch/providers/gemini.py` inheriting from `ProviderAdapter`.
  - [ ] 1.2: Implement `detect()` and `list_models()`.
- [ ] Task 2: Implement Execution Logic (AC: 4, 5, 6, 7)
  - [ ] 2.1: Implement `execute(prompt: str)` using the PTY utility.
  - [ ] 2.2: Handle subprocess lifecycle and map exit codes.
- [ ] Task 3: Write comprehensive tests (AC: 1-7)
  - [ ] 3.1: Create `tests/test_providers/test_gemini.py`.
  - [ ] 3.2: Mock Gemini CLI binary and execution.

## Dev Notes

- **Gemini CLI:** Target the official Google Gemini CLI.
- **PTY:** Use the `read_pty_output` utility established in Story 2.1.

### Project Structure Notes

- New file: `src/bmad_orch/providers/gemini.py`.
- Update: `src/bmad_orch/providers/__init__.py` to register `GeminiAdapter`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic-2, Story 2.3]
- [Source: _bmad-output/planning-artifacts/prd.md — FR12a, FR12b, FR12c]

## Dev Agent Record

### Agent Model Used

Gemini 2.0 Flash

### Debug Log References

### Completion Notes List

### File List

- `src/bmad_orch/providers/gemini.py`
- `src/bmad_orch/providers/__init__.py` (updated)
- `tests/test_providers/test_gemini.py`
