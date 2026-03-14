# Dev Notes

- **Pattern:** Same-filesystem temp + atomic rename is non-negotiable for NFR1 (Reliability).
- **Library:** Use `pydantic` for schema validation and `pathlib` for file operations.
- **Concurrency:** The `StateManager` is not thread-safe; external synchronization is required if multiple threads access the same state file.
- **Dependencies:** See "Dependencies (exact imports)" below.
- **Error Module:** The project's exception hierarchy lives in `bmad_orch.exceptions` (not `errors.py`). Use `StateError` for state-related failures.
- **State File Location:** Default to `bmad-orch-state.json` in CWD unless overridden.
- **Serialization:** Use `model_dump_json(indent=2)` for human-readable state files (as per FR48). Always write with explicit `encoding="utf-8"`.
- **Existing Code:** `state/schema.py` already contains an `OrchestratorState` model with `config_hash`. Fold `config_hash` into `RunState` as an optional field and remove `OrchestratorState` (it was a stub placeholder for this story).
- **StepOutcome:** Defined as `NewType("StepOutcome", str)` in `types/__init__.py` — it is a type alias, not an Enum. Do not treat it as an Enum in schema definitions. Import as `from bmad_orch.types import StepOutcome`.
- **Dependencies (exact imports):** `state/` may import from `bmad_orch.types`, `bmad_orch.exceptions`, and `bmad_orch.config`. It must NOT import from `bmad_orch.engine` or `bmad_orch.providers`.
- **Architecture Deviation:** This story uses UUID-based temp filenames instead of the architecture's fixed `.bmad-orch-state.tmp` to avoid race conditions in concurrent-write scenarios. Also uses `os.replace()` instead of `os.rename()` for cross-platform atomicity.

## Project Structure Notes

- `src/bmad_orch/state/schema.py` (exists — update)
- `src/bmad_orch/state/manager.py` (new)
- `src/bmad_orch/state/__init__.py` (may exist — update or create)
- `tests/test_state/test_schema.py`
- `tests/test_state/test_manager.py`

## References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.2]
- [Source: _bmad-output/planning-artifacts/architecture.md#State & Data Management]
- [Source: _bmad-output/planning-artifacts/prd.md#FR20, FR21, FR48, NFR1]
