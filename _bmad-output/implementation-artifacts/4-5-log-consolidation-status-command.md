---
status: done
stepsCompleted: []
---

# Story 4.5: Log Consolidation & Status Command

As a **user**,
I want consolidated logs and a quick status check,
so that I can understand what happened in a run and check on current state without starting execution.

## Acceptance Criteria

1. **Given** a workflow with multiple completed steps producing `StepRecord` entries nested within `CycleRecord`s in `RunState.run_history`
   **When** the run completes or an emergency halt triggers a git commit
   **Then** a consolidated run log file is written to `_bmad-output/implementation-artifacts/{run_id}-cycle.log` summarizing all step records (extracted from all `CycleRecord.steps` lists) before the commit. If log consolidation fails, it must log an error to stderr but MUST NOT block the git commit or emergency halt sequence. The file write MUST be atomic (write to a temporary file and rename) to avoid partial reads during active runs.

2. **Given** the consolidated log file
   **When** I inspect its contents
   **Then** entries are ordered chronologically (with cycle index and step index within cycle as secondary sort keys for deterministic ordering of equal timestamps). Timestamps must be formatted in consistent ISO-8601 UTC (if `StepRecord.timestamp` is naive, treat it as UTC; if aware, convert to UTC). The file MUST start with a metadata header containing the `run_id` and initial configuration. The format for step records must consistently include: `[Cycle {cycle_index}] [{timestamp_iso8601_utc}] [{step_id}] [{provider_name or "None"}] {outcome} {error.message if error else ""}`.

3. **Given** a run in any terminal state (COMPLETED, FAILED, HALTED) or an active RUNNING/PENDING state
   **When** I run `bmad-orch status` (optionally with `--run-id <run_id>`)
   **Then** the system displays: run status, last completed step with its provider, cycle progress (completed/total), elapsed time (calculated as `now - start_time` for RUNNING, or `end_time - start_time` for terminal states; for PENDING state, display "not started" instead of elapsed time), and any errors — without starting a new run. If the state file is corrupted or unreadable, the command must gracefully report a corruption error to stderr and exit with code 2. The command should exit with code 0 if the run is in a non-failed state, and exit code 3 if the run is FAILED or HALTED.

4. **Given** no state file exists (or the specific `--run-id` does not exist)
   **When** I run `bmad-orch status`
   **Then** the system reports no previous runs found to stderr (exit code 1).

5. **Given** a state file from a failed or halted run
   **When** I run `bmad-orch status`
   **Then** the output includes `failure_point`, `failure_reason`, and `error_type` from state, and suggests `bmad-orch resume` only if the failure is recoverable. Define a `NON_RECOVERABLE_ERROR_TYPES` constant (set of strings: `{"ConfigError", "SchemaValidationError", "SystemError"}`) in `src/bmad_orch/engine/errors.py` and check `error_type not in NON_RECOVERABLE_ERROR_TYPES`.

6. **Given** the `status` command
   **When** it is invoked with `--json`
   **Then** it outputs the full serialized `RunState` JSON to stdout using Pydantic's `.model_dump_json(indent=2)` for consistent serialization (datetime as ISO-8601 strings, enums as string values). All non-JSON output (like progress bars, warnings, or info messages) MUST be completely suppressed (not just redirected to stderr) so stdout remains purely parsable JSON and stderr does not pollute logs, except for fatal errors which go to stderr.

7. **Given** a log consolidation event
   **When** the output directory `_bmad-output/implementation-artifacts/` does not exist
   **Then** the system must automatically create the necessary parent directories before writing the log file.

8. **Given** a resumed run
   **When** it completes or halts
   **Then** the log consolidation must include all steps from the entire run history, including the steps from before the resume occurred. The log file must be overwritten atomically (not appended) to ensure it always represents the complete run history.

## Technical Notes

- The `status` command already exists as a stub in `src/bmad_orch/cli.py` — implement the existing stub rather than registering a new command. Add a `--run-id` option.
- `StepRecord` fields available for log consolidation: `step_id`, `provider_name`, `outcome`, `timestamp`, `error` (where `error` is `ErrorRecord | None` with fields: `message`, `error_type`, `traceback`). For log lines, use `error.message` as the error summary when `error` is not `None`.
- `RunState.run_history` is `list[CycleRecord]`; each `CycleRecord` contains `steps: list[StepRecord]`. Log consolidation must iterate `run_history` → `cycle.steps` to collect all step records.
- Git commit hook points in `Runner`: `_emergency_halt()` (commit + push) and end of `_run_internal()` (push only if `config.git.push_at == "end"`). Log consolidation must be called in both places. Resume logic lives in `src/bmad_orch/engine/resume.py` (not `Runner._resume()`); log consolidation must also be called at the end of the resume flow in that module.
- Consolidated log output path: `_bmad-output/implementation-artifacts/{run_id}-cycle.log`.

## Tasks / Subtasks

- [x] 1. Implement Log Consolidation Logic (AC: 1, 2, 7, 8)
  - [x] Create `src/bmad_orch/engine/logs.py`
  - [x] Ensure parent directories
  - [x] Iterate `state.run_history`
  - [x] Sort `StepRecord`s
  - [x] Generate a metadata header
  - [x] Format each `StepRecord`
  - [x] Perform atomic write
  - [x] Update `Runner._emergency_halt()` and end-of-run
  - [x] Update the resume flow
  - [x] Wrap the `consolidate_logs` call
- [x] 2. Implement `status` command in CLI (AC: 3, 4, 5, 6)
  - [x] Replace the existing `status` stub
  - [x] Implement Rich-formatted summary
  - [x] Handle all `RunStatus` enum values
  - [x] Handle missing state file
  - [x] Handle corrupted state file
  - [x] Implement `--json` flag
  - [x] Define `NON_RECOVERABLE_ERROR_TYPES`
  - [x] For FAILED/HALTED states: show details
  - [x] For PENDING state: display "not started"
- [x] 3. Verification and Testing (AC: 1-8)
  - [x] Create `tests/test_status.py`
  - [x] Test `--run-id` option
  - [x] Test missing/corrupted state file
  - [x] Test `--json` output
  - [x] Test conditional resume suggestion
  - [x] Create `tests/test_logs.py`
  - [x] Test metadata header generation
  - [x] Test consolidation with empty run history
  - [x] Test log consolidation failure
  - [x] Test log consolidation correctly traverses
  - [x] Test atomic file replacement

## Dev Agent Record

### File List
- `src/bmad_orch/engine/logs.py`
- `src/bmad_orch/engine/resume.py`
- `src/bmad_orch/engine/runner.py`
- `src/bmad_orch/engine/errors.py`
- `src/bmad_orch/cli.py`
- `tests/test_logs.py`
- `tests/test_logs_atdd.py`
- `tests/test_status_atdd.py`

### Change Log
- Implemented `consolidate_logs` in `src/bmad_orch/engine/logs.py` to collect, sort, and write step records.
- Updated `Runner._emergency_halt` and `Runner._run_internal` to call log consolidation.
- Updated `prepare_skip` in `resume.py` to trigger log consolidation.
- Implemented `status` command in `cli.py` with ACs 3, 4, 5, 6 including `--json`.
- Added tests `test_logs.py`, `test_logs_atdd.py`, `test_status_atdd.py`