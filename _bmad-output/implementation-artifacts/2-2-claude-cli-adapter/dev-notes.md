# Dev Notes

- **Claude CLI:** Target the official Anthropic `claude` command.
- **PTY:** Use `spawn_pty_process` from `src/bmad_orch/providers/utils.py`. This utility MUST be updated to support environment passing.
- **OutputChunk:** Use `_get_base_metadata()` from the base class to ensure `execution_id` is present.
- **Exceptions:** Use `ProviderError`, `ProviderCrashError`, `ProviderTimeoutError`. Use `ProviderError` for output corruption with a specific "Corrupted Provider Output" prefix.
- **Async:** Entire execution path must be non-blocking.
- **Dependency:** This story requires Story 2.1 to be complete.

## Project Structure Notes

- New file: `src/bmad_orch/providers/claude.py`.
- Update: `src/bmad_orch/providers/__init__.py` — register adapter.
- **Update:** `src/bmad_orch/providers/utils.py` — add `env` support to `spawn_pty_process`.
- New file: `tests/test_providers/test_claude.py`.

## References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic-2, Story 2.2]
- [Source: _bmad-output/planning-artifacts/prd.md — FR12a, FR12b, FR12c]
