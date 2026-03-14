# Dev Notes

- **Gemini CLI:** Target the `gemini` command (ensure compatibility with standard community wrappers if an official binary is not present).
- **PTY:** Use `spawn_pty_process` from `src/bmad_orch/providers/utils.py`.
- **OutputChunk:** Use `_get_base_metadata()` from the base class.
- **Exceptions:** Use `ProviderError`, `ProviderCrashError`, `ProviderTimeoutError`.
- **Dependency:** Requires Story 2.1 (base class) and Story 2.2 (PTY utils).

## Project Structure Notes

- New file: `src/bmad_orch/providers/gemini.py`.
- Update: `src/bmad_orch/providers/__init__.py`.
- New file: `tests/test_providers/test_gemini.py`.

## References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic-2, Story 2.3]
- [Source: _bmad-output/planning-artifacts/prd.md — FR12a, FR12b, FR12c]
