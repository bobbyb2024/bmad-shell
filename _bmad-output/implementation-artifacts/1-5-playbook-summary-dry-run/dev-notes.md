# Dev Notes

- **Architecture Rules:** Core engine (`engine/runner.py`) must never import from `rendering/` or `Rich` directly (Decision 1).
- **UX Requirements:** Pre-flight summary must be mandatory on first run or when config changes to ensure user awareness of the execution plan.
- **Escalation Colors:** Use `src/bmad_orch/rendering/styles.py` for central style definitions (e.g., `SUCCESS`, `ERROR`, `WARNING`).
- **Path discovery:** Use `bmad_orch.config.discovery.discover_config_path()` and `load_config_file()` established in Story 1.3.
- **Renderer Constraints:** `rendering/summary.py` may import from `bmad_orch.types` and the `rich` library.
- **Exit Code Contract:** 130 = user cancellation at confirmation prompt or editor loop.
- **Non-TTY Handling:** Ensure `Rich` is configured to auto-detect TTY status and fallback to plain text as needed.

## Project Structure Notes

- New files: `src/bmad_orch/rendering/summary.py`, `src/bmad_orch/engine/runner.py`, `tests/test_rendering/test_summary.py`, `tests/test_engine/test_runner.py`, `tests/test_cli_dry_run.py`, `tests/test_cli_preflight.py`
- Modify: `src/bmad_orch/cli.py`, `src/bmad_orch/errors.py`

## References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic-1, Story 1.5, lines 405-430]
- [Source: _bmad-output/planning-artifacts/prd.md — FR46, FR47 Playbook Summary & Dry Run]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — UX-DR5 Pre-flight summary, UX-DR15 Confirmation patterns, UX-DR9 Config editing flow]
- [Source: _bmad-output/planning-artifacts/architecture.md — engine/runner.py Runner orchestration, line 580]
