# Tasks / Subtasks

- [x] Task 1: Implement Claude Adapter (AC: 1, 2, 3)
  - [x] 1.1: Create `src/bmad_orch/providers/claude.py` inheriting from `ProviderAdapter`.
  - [x] 1.2: Implement `detect()` using `shutil.which("claude")`. Cache the output of `claude --version` for AC6.
  - [x] 1.3: Implement `list_models()` with error handling for non-zero exit codes and empty/malformed output. Implement fallback list: `["claude-3-5-sonnet-latest", "claude-3-opus-latest"]`.
  - [x] 1.4: Register `ClaudeAdapter` in `src/bmad_orch/providers/__init__.py`.
- [x] Task 2: Implement Execution Logic (AC: 3, 4, 5, 6, 7, 8)
  - [x] 2.1: Implement `execute(prompt: str, **kwargs) -> AsyncIterator[OutputChunk]` delegating to `spawn_pty_process`.
  - [x] 2.2: **Mandatory:** Extend `spawn_pty_process` in `src/bmad_orch/providers/utils.py` to accept an `env: dict[str, str]` parameter if it does not already exist.
  - [x] 2.3: Pass `ANTHROPIC_API_KEY` through the `env` parameter (do NOT use `os.environ`).
  - [x] 2.4: Implement defensive output validation: check the initial stream buffer for binary or HTML markers using regex; raise `ProviderError` on detection.
  - [x] 2.5: Implement graceful cancellation: catch `asyncio.CancelledError`, send SIGTERM, wait for grace period (env-configurable), then SIGKILL.
- [x] Task 3: Write tests (AC: 1-8)
  - [x] 3.1: Create `tests/test_providers/test_claude.py`.
  - [x] 3.2: Mock `shutil.which` and `spawn_pty_process` to simulate CLI presence and execution.
  - [x] 3.3: Test streaming (verify `OutputChunk` fields and `execution_id` presence in metadata), timeout, crash, and cancellation paths.
  - [x] 3.4: Test auth propagation (verify `env` dict).
  - [x] 3.5: Test `list_models()` fallback and error paths for malformed output.
