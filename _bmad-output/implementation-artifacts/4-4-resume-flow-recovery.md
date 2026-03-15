---
status: done
stepsCompleted: [1, 2, 3, 4, 5]
---

# Story 4.4: Resume Flow & Recovery

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **user**,
I want to resume from any failure point with clear context about what happened,
so that I can make an informed decision about how to continue without investigating logs.

## Acceptance Criteria

1. **Given** a previous run that failed or was halted (status is FAILED or HALTED)
   **When** I run `bmad-orch resume`
   **Then** the system loads the state file and displays a resume context screen showing: last run timestamp (`halted_at` — set by the engine when transitioning to FAILED/HALTED status), stopped-at point (`failure_point`), failure reason (`failure_reason`), error type (`error_type`), and a summary of completed work (count of completed cycles/steps). Missing metadata fields (e.g., if the engine crashed before recording) must fallback gracefully to `[Unknown]`. If `failure_point` is missing entirely, Options 1 and 2 must be disabled with a clear error message.

2. **Given** the resume context screen
   **When** it is displayed
   **Then** it presents five numbered options:
   - [1] **Re-run failed step**: Resumes from the exact failed/halted step (disabled if `failure_point` is unknown).
   - [2] **Skip failed step**: Logs the failed step as skipped and continues from the next step (disabled if `failure_point` is unknown).
   - [3] **Restart current cycle**: Restarts the cycle that contains the failure point from its first step.
   - [4] **Start from scratch**: Backs up the old state and restarts the entire workflow from the first cycle.
   - [5] **Cancel**: Exits the resume flow without taking any action (exit code 0).

3. **Given** the user selects option 1 (re-run)
   **When** execution starts
   **Then** the orchestrator begins at the `failure_point` with the accumulated `template_context` from the state file restored and passed to `PromptResolver`.

4. **Given** the user selects option 2 (skip)
   **When** execution starts
   **Then** the system warns the user: `⚠ Skipping this step may cause subsequent steps to fail if they depend on its output context.` (requires confirmation, or `--force` in headless). The `failure_point` step is marked with a `SKIPPED` outcome in the state history. Any expected outputs from this step are omitted from the context. If the skipped step is the last step in the cycle, the cycle completes normally and execution begins at the first step of the following cycle. Otherwise, it begins at the following step in the current cycle.

5. **Given** the user selects option 3 (restart cycle)
   **When** execution starts
   **Then** the `CycleRecord` for the current cycle is replaced with a new empty record in `run_history`, the `template_context` is restored to a `context_snapshot` taken at the start of that cycle, and execution begins at step 1 of that cycle. A disclaimer must note that external side-effects (e.g. written files) from the failed run are not rolled back.

6. **Given** the user selects option 4 (start fresh)
   **When** execution starts
   **Then** the system renames the existing state file to `bmad-orch-state-[timestamp].json.bak` to prevent data loss or destructive overwrites. The `RunState` is fully reset (new `run_id`, empty `run_history`, empty `template_context`, cleared failure fields) and execution begins at the first cycle of the playbook.

7. **Given** no state file exists, or it is empty/corrupt
   **When** I run `bmad-orch resume`
   **Then** the system exits with a clear error: `✗ No previous run found — use bmad-orch start` and a non-zero exit code (e.g. 1). If the file exists but is corrupt, it is renamed to `bmad-orch-state-[timestamp].json.bak` before exiting.

8. **Given** a run that completed successfully (status is COMPLETED)
   **When** I run `bmad-orch resume`
   **Then** the system reports `✓ Previous run completed successfully` and suggests `bmad-orch start` for a new run, exiting with code 0.

9. **Given** a run that is currently in progress (status is RUNNING or IN_PROGRESS)
   **When** I run `bmad-orch resume`
   **Then** the system immediately aborts with an error `✗ A run is currently in progress` and exits with code 1. A `--force-unlock` flag must be provided to allow breaking the lock in case of a zombie process crash.

10. **Given** a run started in headless mode
    **When** I resume in TUI mode (or vice versa)
    **Then** the resume logic works identically. In non-interactive/headless mode, the `--resume-option` CLI flag (1-5) must be provided; if omitted, the command exits with code 1. If `--resume-option` is passed in interactive mode, it bypasses the prompt and uses the provided option. Option 5 (Cancel) is a valid selection and results in a clean code 0 exit.

11. **Given** the playbook config has changed since the failed run (logical schema hash mismatch, ignoring purely whitespace changes)
    **When** I run `bmad-orch resume`
    **Then** the system displays a warning: `⚠ Playbook config has changed since the failed run` and prompts for confirmation. In non-interactive mode, the resume aborts with code 1 unless `--force` is passed. Even with `--force`, if the target `failure_point` step index no longer exists in the updated playbook schema, the resume must abort with a fatal error (code 1).

12. **Given** the interactive menu is displayed
    **When** the user sends an interrupt signal (e.g., Ctrl+C)
    **Then** the system gracefully catches the interrupt, treats it as Option 5 (Cancel), and exits cleanly with code 0 without modifying the state.

## Tasks / Subtasks

- [x] 1. Implement Resume Context Display & CLI Core (AC: 1, 7, 8, 9, 10, 11)
  - [x] Update `src/bmad_orch/cli.py` to implement the `resume` command (replace existing stub).
  - [x] Add strict schema validation when loading the state file using `StateManager.load()` to prevent crashes on tampered files.
  - [x] Implement logic to detect and report "No previous run" (AC: 7), renaming corrupt files to timestamped `.bak` with exit code 1.
  - [x] Implement logic for "Run already completed" (AC: 8), exit code 0.
  - [x] Implement logic to reject resuming a `RUNNING` state (AC: 9) and add `--force-unlock` to override zombie states.
  - [x] Add logical hash checking for config mismatch and warn/abort (AC: 11), ignoring whitespace differences.
  - [x] Add pre-flight bounds check to ensure the target `failure_point` exists in the playbook schema. Disable options 1 and 2 if `failure_point` is missing.
  - [x] Use `Rich` to render the "Resume Context" screen with fallbacks for missing `error_type` (AC: 1).
- [x] 2. Update Runner and CycleExecutor Schema & State Snapshot (AC: 3, 4, 5)
  - [x] Add `SKIPPED` to `StepOutcome` enum in `src/bmad_orch/state/schema.py` if not already present.
  - [x] Update `CycleRecord` schema in `src/bmad_orch/state/schema.py` to include an optional `context_snapshot` dict.
  - [x] Modify `src/bmad_orch/engine/cycle.py` `CycleExecutor.execute_cycle()` to snapshot the `template_context` into `CycleRecord.context_snapshot` when a cycle starts.
  - [x] Extend the existing cycle-skip logic in `src/bmad_orch/engine/runner.py` to support starting from a specific step index within a cycle.
  - [x] Modify `CycleExecutor.execute_cycle()` to accept an optional `start_step_index` parameter.
- [x] 3. Implement Interactive Resume Menu (AC: 2, 4, 10, 12)
  - [x] Add an interactive menu to the `resume` command in `src/bmad_orch/cli.py` using `typer.prompt` for interactive mode.
  - [x] Add graceful SIGINT (Ctrl+C) and SIGTERM handling to trigger Cancel (AC: 12) with exit code 0.
  - [x] Add `--resume-option` flag (int, 1-5); require it in non-interactive mode, or bypass prompt if provided in interactive mode.
  - [x] Add `--force` flag to bypass config hash mismatch warning and the skip warning in non-interactive mode.
  - [x] Capture user selection (1-5, including Cancel) and prompt for confirmation on Skip (Option 2). In non-interactive mode, `--force` bypasses the skip confirmation.
- [x] 4. Implement Resume Logic in Engine (AC: 3, 4, 5, 6)
  - [x] Create `src/bmad_orch/engine/resume.py` with helper functions to prepare the `RunState` and configure `Runner` offsets.
  - [x] **Option 1 (Re-run)**: Set `Runner` start offset to `failure_point` with `template_context` restored from state.
  - [x] **Option 2 (Skip)**: Record a `SKIPPED` entry in `RunState` for the failure point. Omit expected outputs from the context. Set `Runner` to start at the next appropriate step/cycle.
  - [x] **Option 3 (Restart Cycle)**: Replace the current cycle's `CycleRecord` with a new empty one, restore `template_context` from the cycle's `context_snapshot`, print side-effects warning, then set `Runner` to start at step 1.
  - [x] **Option 4 (Start Fresh)**: Rename existing state file to timestamped `.bak`. Fully reset `RunState` (new `run_id`, empty `run_history`, empty `template_context`, cleared failure fields).
  - [x] **Option 5 (Cancel)**: No state changes; exit cleanly with code 0.
- [x] 5. Verification and Testing (AC: 1-12)
  - [x] Create `tests/test_resume.py` to verify all 5 resume options using a mocked state and runner.
  - [x] Test edge cases: state file missing, corrupt state file (verify timestamped `.bak`), state file for completed run, RUNNING status rejection & `--force-unlock`.
  - [x] Test logical config hash mismatch: with and without `--force`, and verify out-of-bounds `failure_point` aborts (exit code 1).
  - [x] Test non-interactive mode: verify `--resume-option` behavior and required status.
  - [x] Verify that `template_context` is preserved correctly for options 1-2, restored from snapshot in option 3, and reset in option 4.
  - [x] Test Ctrl+C and SIGTERM interruption during menu selection.
  - [x] Test appropriate POSIX exit codes (0 for success/cancel, 1 for errors).

## Dev Notes

### Technical Requirements
- **State Portability:** The resume logic must rely strictly on the `bmad-orch-state.json` file.
- **Atomic Writes:** Any modifications to the state during the resume selection process must use the `StateManager.save()` atomic write pattern.
- **Prompt Resolution:** When resuming, ensure that the `PromptResolver` correctly uses the accumulated `template_context` from the state file.
- **Headless Mode:** The `resume` command requires `--resume-option <1-5>` when no TTY is present. Add `--force` to bypass warnings and `--force-unlock` for zombies.
- **Graceful Degradation:** The UI must handle missing `failure_point` or `error_type` fields gracefully, disabling dependent options.

### Architecture Compliance
- **Dependency Isolation:** Keep the resume logic in `src/bmad_orch/engine/resume.py` free of TUI-specific imports.
- **Prompt Ownership Boundary:** All user-facing prompts and confirmations live in `cli.py`. The `resume.py` module only mutates state.
- **Clean Execution Path:** Resume must reuse the existing `Runner.run()` loop. Do NOT create a separate "resume loop."
- **Context Immutability (Conceptual):** Rely entirely on the `context_snapshot` captured at the start of the cycle for Option 3.

### Project Structure Notes
- **CLI Command:** `src/bmad_orch/cli.py` -> `app.command() def resume(...)`
- **Resume Logic:** `src/bmad_orch/engine/resume.py` (New)
- **Runner Updates:** `src/bmad_orch/engine/runner.py`
- **Cycle Engine Updates:** `src/bmad_orch/engine/cycle.py`

### References
- [Source: _bmad-output/planning-artifacts/epics/epic-4-reliable-unattended-execution.md#Story 4.4]
- [Source: src/bmad_orch/state/manager.py]
- [Source: src/bmad_orch/state/schema.py]
- [Source: src/bmad_orch/engine/runner.py]

## Dev Agent Record

### Agent Model Used
Gemini 2.0 Flash

### Debug Log References
- Fixed `StepOutcome` to be a `StrEnum` for consistency with Pydantic and Task requirements.
- Updated `StateManager.start_cycle` to handle `context_snapshot`.
- Implemented `current_start_step` logic in `CycleExecutor` to ensure resumed cycles skip already completed steps on the first repetition only.
- Fixed `cli.py` to correctly handle `pathlib.Path` objects when calling `get_config`.
- Verified all 5 resume options via comprehensive unit tests in `tests/test_resume.py`.

### Completion Notes List
- Implemented `bmad-orch resume` command with all requested options.
- Added `context_snapshot` to `CycleRecord` for reliable cycle restarts.
- Enabled headless mode support with `--resume-option` and `--force`.
- Guaranteed atomic state writes and graceful degradation for missing metadata.
- Ensured zero-regression by verifying existing and new tests pass.

### File List
- `src/bmad_orch/types/__init__.py`
- `src/bmad_orch/state/schema.py`
- `src/bmad_orch/state/manager.py`
- `src/bmad_orch/state/__init__.py`
- `src/bmad_orch/engine/cycle.py`
- `src/bmad_orch/engine/runner.py`
- `src/bmad_orch/engine/resume.py`
- `src/bmad_orch/cli.py`
- `tests/test_resume.py`

### Change Log
- 2026-03-15: Initial implementation of Story 4.4: Resume Flow & Recovery.
- 2026-03-15: Added comprehensive tests and verified all ACs.

### Status
review
