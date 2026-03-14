---
title: "Story 2.3: Gemini CLI Adapter"
status: done
storyPoints: 5
depends_on:
  - "2.1"
  - "2.2"
stepsCompleted: [1, 2, 3]
---

# Story 2.3: Gemini CLI Adapter

## Story

As a **user**,
I want **the orchestrator to invoke Gemini CLI with my configured prompts**,
so that **Gemini can execute validation steps and provide adversarial review in my workflows**.

## Acceptance Criteria

1. **AC1: Gemini CLI Detection** — `GeminiAdapter.detect()` returns `True` via `shutil.which` if the Gemini CLI (`gemini`) is installed. It returns `False` otherwise. The adapter caches the absolute binary path and `gemini --version` output in class-level attributes for diagnostic use.
2. **AC2: Gemini Model Listing** — `GeminiAdapter.list_models()` invokes the CLI to discover available models and returns a `list[dict[str, Any]]`. If the command fails or returns malformed output, the adapter raises `ProviderError`. **Fallback:** If the subcommand is missing or unavailable, the adapter returns a configurable list of default models (defaulting to latest stable Flash/Pro versions).
3. **AC3: Prompt Execution & Auth** — `GeminiAdapter.execute(prompt, **kwargs)` delegates to `spawn_pty_process`. The adapter MUST raise `ProviderError` if no API key is found in kwargs or adapter config (checking both `GEMINI_API_KEY` and `GOOGLE_API_KEY`). It constructs an `env` dict that preserves `PATH`, `HOME`, and `LANG` while injecting the API key; it MUST NOT modify `os.environ`.
4. **AC4: Output Streaming & Metadata** — The adapter yields the unified PTY stream as `OutputChunk` objects. It creates a `metadata` dict by merging `execution_id`, `model`, `provider`, and CLI `version` into the base dict provided by `_get_base_metadata()`.
5. **AC5: Successful Completion** — On exit code 0, the adapter ensures the iterator yields all remaining PTY buffer content and then yields a final `OutputChunk` with completion status metadata before closing.
6. **AC6: Process Termination Context** — When `spawn_pty_process` raises `ProviderTimeoutError` or `ProviderCrashError`, the adapter calls `process.kill()` + `await process.wait()` for cleanup and appends the cached CLI version info (or "Version Unknown" if missing) to the exception message.
7. **AC7: Defensive Parsing** — The adapter inspects the output stream. It raises `ProviderError` with "Corrupted/Provider Error" if it detects binary data or regex matches (case-insensitive) for `<html>`, `502 Bad Gateway`, `Cloudflare`, `403 Forbidden`, or `PERMISSION_DENIED`. This check MUST persist for the first 2KB and be triggered if these strings appear at any point during the stream.
8. **AC8: Graceful Cancellation** — On `asyncio.CancelledError`, the adapter sends SIGTERM and waits for a grace period (default: 2 seconds; configurable via `GEMINI_TERMINATION_GRACE_PERIOD`) before escalating to SIGKILL.
9. **AC9: Transient Error Handling** — The adapter implements basic retry logic for transient CLI failures (non-zero exit codes associated with network/rate-limiting) using an exponential backoff strategy if configured.

## Tasks / Subtasks

- [x] Task 1: Implement Gemini Adapter (AC: 1, 2, 3, 9)
  - [x] 1.1: Create `src/bmad_orch/providers/gemini.py` inheriting from `ProviderAdapter`.
  - [x] 1.2: Implement `detect()` using `shutil.which`. Cache binary path and `--version` in class attributes `_cli_path` and `_cli_version`.
  - [x] 1.3: Implement `list_models()` with fallback to configurable defaults if the subcommand is missing or returns an error.
  - [x] 1.4: Register `GeminiAdapter` in `ADAPTER_MAP` within `src/bmad_orch/providers/__init__.py`.
- [x] Task 2: Implement Execution Logic (AC: 3, 4, 5, 6, 7, 8)
  - [x] 2.1: Implement `execute()`; merge `execution_id`, `model`, `provider`, and `version` into the metadata of each `OutputChunk`.
  - [x] 2.2: Pass API key via `env` parameter with `PATH`, `HOME`, and `LANG` preserved; check both `GEMINI_API_KEY` and `GOOGLE_API_KEY`.
  - [x] 2.3: Implement buffer check for binary/HTML (`<html>`, `502`, etc.) using case-insensitive regex for the first 2KB and continuous monitoring.
  - [x] 2.4: Implement SIGTERM -> Configurable Wait -> SIGKILL flow.
  - [x] 2.5: Yield final `OutputChunk` with completion status metadata after buffer flush on exit code 0 (AC5).
- [x] Task 3: Write tests (AC: 1-9)
  - [x] 3.1: Create `tests/test_providers/test_gemini.py`.
  - [x] 3.2: Mock `shutil.which` and `spawn_pty_process`.
  - [x] 3.3: Test streaming, metadata presence (`execution_id`, `model`, `provider`, `version`), timeouts, and crashes.
  - [x] 3.4: Test auth propagation (both key names) and missing-key error.
  - [x] 3.5: Test `list_models()` success path and fallback path.
  - [x] 3.6: Test defensive parsing with various HTML/Proxy error payloads.
  - [x] 3.7: Test retry logic for transient failures.

## Dev Notes

- **Gemini CLI:** Target the `gemini` command (ensure compatibility with standard community wrappers if an official binary is not present).
- **PTY:** Use `spawn_pty_process` from `src/bmad_orch/providers/utils.py`.
- **OutputChunk:** Use `_get_base_metadata()` from the base class.
- **Exceptions:** Use `ProviderError`, `ProviderCrashError`, `ProviderTimeoutError`.
- **Dependency:** Requires Story 2.1 (base class) and Story 2.2 (PTY utils).

### Project Structure Notes

- New file: `src/bmad_orch/providers/gemini.py`.
- Update: `src/bmad_orch/providers/__init__.py`.
- New file: `tests/test_providers/test_gemini.py`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic-2, Story 2.3]
- [Source: _bmad-output/planning-artifacts/prd.md — FR12a, FR12b, FR12c]

## Dev Agent Record

### Agent Model Used

Gemini 2.0 Flash

### Completion Notes List

- Implemented `GeminiAdapter` with support for both `GEMINI_API_KEY` and `GOOGLE_API_KEY`.
- Added defensive parsing for HTML errors, proxy errors, and binary data (AC7) for the full stream (first 2KB accumulated + per-chunk thereafter).
- Implemented exponential backoff retry logic (AC9) configurable via environment variables.
- Added final completion `OutputChunk` with status metadata (AC5).
- Achieved 100% test coverage for the new adapter.

### File List

- `src/bmad_orch/providers/gemini.py` (new)
- `src/bmad_orch/providers/__init__.py` (updated)
- `tests/test_providers/test_gemini.py` (new)

### Change Log

- Initial implementation of Gemini CLI Adapter.
- Added comprehensive unit tests with coverage reporting.
- Registered Gemini adapter in the provider registry.
- **Code Review (2026-03-14):** Fixed AC7 defensive parsing to check corruption patterns beyond 2KB (was only first 2KB). Added `# noqa: S603` to subprocess calls for linting consistency. Fixed `import os` placement and test isolation in `test_execute_auth_propagation_google_key`. Added 2 new tests for beyond-2KB defensive parsing. Fixed regex escape warning.
- **Code Review Fixes (2026-03-14):** Fixed High Severity issue where `execution_id` was unstable across retries. Refactored metadata merging to be more efficient and consistent with the base class. Verified fixes with 25 unit tests (100% coverage for `gemini.py`).
- **Code Review #3 (2026-03-14):** Fixed `GeminiAdapter.__init__` to accept configuration arguments (preventing `TypeError` on instantiation). Implemented configurable fallback models via adapter config (`default_models`). Refined `list_models` to raise `ProviderError` on genuine CLI failures while maintaining fallback for missing subcommands. Hardened `AC7` defensive parsing with a sliding window to prevent split-chunk misses. Updated all retry and grace period logic to prefer adapter configuration over environment variables. Verified with 31 unit tests (100% coverage for `gemini.py`).
