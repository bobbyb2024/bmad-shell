# Tasks / Subtasks

- [x] Task 1: Implement State Schema (AC: 1, 2, 6, 9)
  - [x] 1.1: Update existing `src/bmad_orch/state/schema.py` to integrate new models.
  - [x] 1.2: Define `StepRecord`, `CycleRecord`, `ErrorRecord`, and `RunState` as `frozen` Pydantic models. Include `schema_version: int = 1` in `RunState`.
  - [x] 1.3: Import `StepOutcome` from `bmad_orch.types`.
  - [x] 1.4: Fold existing `config_hash` into `RunState` as an optional field (`config_hash: str | None = None`). Remove the standalone `OrchestratorState` model since `RunState` supersedes it.
- [x] Task 2: Implement State Manager (AC: 3, 4, 5, 7, 8, 10, 11)
  - [x] 2.1: Create `src/bmad_orch/state/manager.py`.
  - [x] 2.2: Implement `load(path: Path | None = None) -> RunState`. Handle validation errors by renaming corrupt files to `{path}.corrupt.{timestamp}`. Validate `config_hash` against the current configuration; log a warning on mismatch.
  - [x] 2.3: Implement `save(state: RunState, path: Path)`. Use unique temp files and `os.replace()` for atomic updates. Ensure parent directories are created. Wrap I/O failures in `StateError`.
  - [x] 2.4: Implement `record_step(state: RunState, cycle_id: str, step_record: StepRecord) -> RunState` helper.
  - [x] 2.5: Implement cleanup of stale `.tmp` files on `load()`.
- [x] Task 3: Package Export
  - [x] 3.1: Update `src/bmad_orch/state/__init__.py` to export the public API (`StateManager`, `RunState`, etc.).
- [x] Task 4: Unit Testing (AC: 1-11)
  - [x] 4.1: Create `tests/test_state/test_schema.py` verifying immutability, serialization, and `with_*`/`model_copy` update patterns.
  - [x] 4.2: Create `tests/test_state/test_manager.py` verifying atomic writes, crash safety, timestamped corrupt-file handling, history persistence, save error handling (AC11), and stale temp cleanup.
