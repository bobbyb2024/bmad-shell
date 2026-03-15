---
status: ready-for-dev
stepsCompleted: []
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
   **Then** the system loads the state file and displays a resume context screen showing: last run timestamp (`halted_at`), stopped-at point (`failure_point`), failure reason (`failure_reason`), and a summary of completed work (count of completed cycles/steps).

2. **Given** the resume context screen
   **When** it is displayed
   **Then** it presents four numbered options: 
   - [1] **Re-run failed step**: Resumes from the exact failed/halted step.
   - [2] **Skip failed step**: Logs the failed step as skipped and continues from the next step in the cycle.
   - [3] **Restart current cycle**: Restarts the cycle that contains the failure point from its first step.
   - [4] **Start from scratch**: Resets the state and restarts the entire workflow from the first cycle.

3. **Given** the user selects option 1 (re-run)
   **When** execution starts
   **Then** the orchestrator begins at the `failure_point` with the original provider and prompt context preserved.

4. **Given** the user selects option 2 (skip)
   **When** execution starts
   **Then** the `failure_point` step is marked with a "SKIPPED" outcome in the state history, and execution begins at the following step.

5. **Given** the user selects option 3 (restart cycle)
   **When** execution starts
   **Then** the state for the current cycle is cleared/overwritten, and execution begins at step 1 of that cycle.

6. **Given** the user selects option 4 (start fresh)
   **When** execution starts
   **Then** the `RunState` is reset (new `run_id`, empty `run_history`) and execution begins at the first cycle of the playbook.

7. **Given** no state file exists (or it's empty/corrupt and was moved)
   **When** I run `bmad-orch resume`
   **Then** the system exits with a clear error: `✗ No previous run found — use bmad-orch start`.

8. **Given** a run that completed successfully (status is COMPLETED)
   **When** I run `bmad-orch resume`
   **Then** the system reports `✓ Previous run completed successfully` and suggests `bmad-orch start` for a new run.

9. **Given** a run started in headless mode
   **When** I resume in TUI mode (or vice versa)
   **Then** the resume logic works identically because it is driven by the portable `RunState` JSON file.

## Tasks / Subtasks

- [ ] 1. Implement Resume Context Display (AC: 1, 7, 8)
  - [ ] Update `src/bmad_orch/cli.py` to implement the `resume` command.
  - [ ] Load the state file using `StateManager.load()`.
  - [ ] Implement logic to detect and report "No previous run" (AC: 7) or "Run already completed" (AC: 8).
  - [ ] Use `Rich` to render the "Resume Context" screen with `halted_at`, `failure_point`, `failure_reason`, and progress summary.
- [ ] 2. Implement Interactive Resume Menu (AC: 2, 9)
  - [ ] Add an interactive menu to the `resume` command in `src/bmad_orch/cli.py` using `typer.prompt` or a similar mechanism compatible with both TUI and Headless (fallback to default if non-interactive).
  - [ ] Capture user selection (1-4).
- [ ] 3. Implement Resume Logic in Engine (AC: 3, 4, 5, 6)
  - [ ] Create `src/bmad_orch/engine/resume.py` with a `ResumeManager` or helper functions to prepare the `RunState` and `Runner` for the selected option.
  - [ ] **Option 1 (Re-run)**: Prepare `Runner` to start at `failure_point`.
  - [ ] **Option 2 (Skip)**: Record a `SKIPPED` entry in `RunState` for the failure point, then prepare `Runner` to start at the next step.
  - [ ] **Option 3 (Restart Cycle)**: Truncate/reset the current cycle's steps in `RunState`, then prepare `Runner` to start at step 1 of that cycle.
  - [ ] **Option 4 (Start Fresh)**: Reset `RunState` completely.
- [ ] 4. Update Runner and CycleExecutor (AC: 3, 4, 5)
  - [ ] Modify `src/bmad_orch/engine/runner.py` and `src/bmad_orch/engine/cycle.py` to support starting from a specific cycle index and step index.
  - [ ] Ensure `template_context` is correctly loaded/restored when resuming.
- [ ] 5. Verification and Testing (AC: 1-9)
  - [ ] Create `tests/test_resume.py` to verify all 4 resume options using a mocked state and runner.
  - [ ] Test edge cases: state file missing, state file for completed run, config hash mismatch during resume.
  - [ ] Verify that `template_context` is preserved and correctly used upon resume.

## Dev Notes

### Technical Requirements
- **State Portability:** The resume logic must rely strictly on the `bmad-orch-state.json` file.
- **Atomic Writes:** Any modifications to the state during the resume selection process (e.g., marking a step as skipped) must use the `StateManager.save()` atomic write pattern.
- **Prompt Resolution:** When resuming, ensure that the `PromptResolver` correctly uses the accumulated `template_context` from the state file.
- **Headless Mode:** The `resume` command should support a `--non-interactive` flag (or similar) or use reasonable defaults if no TTY is present, though the primary use case is interactive.

### Architecture Compliance
- **Dependency Isolation:** Keep the resume logic in `src/bmad_orch/engine/resume.py` free of TUI-specific imports. Use the event emitter if status updates need to be broadcast.
- **Clean Execution Path:** Resume should ideally reuse the existing `Runner.run()` loop by setting the initial state/offset rather than having a separate "resume loop".

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

### Completion Notes List

### File List
- `src/bmad_orch/cli.py`
- `src/bmad_orch/engine/resume.py`
- `src/bmad_orch/engine/runner.py`
- `src/bmad_orch/engine/cycle.py`
- `tests/test_resume.py`
