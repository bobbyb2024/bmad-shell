# Story 3.6: Multi-Cycle Workflow Orchestration

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want to run a complete workflow (story → atdd → dev) as a single command,
so that multiple cycle types execute in sequence without manual intervention.

## Acceptance Criteria

1. **Given** a config (loaded from a primary YAML configuration file or overridden by environment variables) with three cycle types defined (story, atdd, dev) in a specific order
   **When** the runner executes the workflow
   **Then** cycle types execute in the configured order: story cycle completes fully, then atdd cycle, then dev cycle. If a cycle type's outcome is failure (as determined by CycleExecutor), the runner must halt immediately and not proceed to subsequent cycle types.

2. **Given** a configured `pause_between_cycle_types` duration (distinct from the existing `pause_between_cycles` which governs repetitions within a single cycle type)
   **When** one cycle type completes successfully and the next cycle type begins
   **Then** the runner pauses for the configured `pause_between_cycle_types` duration before starting the next cycle type

3. **Given** the runner module in `engine/runner.py`
   **When** it orchestrates a workflow
   **Then** it coordinates the cycle engine, provider adapters, state manager, event emitter, and logging subsystem via dependency injection (avoiding tight coupling)

4. **Given** a multi-cycle workflow executing
   **When** each cycle type completes
   **Then** the state file (saved via the existing atomic rename pattern in StateManager — temp file + `os.replace()`) reflects the completed cycle type and the next cycle type to execute

5. **Given** template variables in step prompts
   **When** a dedicated PromptResolver component prepares a step for execution
   **Then** it resolves all template variables safely (using a whitelist-based resolver that only substitutes known keys — no recursive resolution, no `str.format()` or `str.Template` — and raises `TemplateVariableError` on missing required variables) from a cumulative template context that the Runner builds by merging base config variables with output variables registered by each completed cycle type (e.g., after the story cycle completes, `{current_story_file}` becomes available to the atdd and dev cycles)

6. **Given** a `RunCompleted` event
   **When** the entire workflow finishes (or terminates due to a fatal error)
   **Then** the event includes `total_step_count` (sum of all steps across all cycle types), `total_cycles` (number of cycle type executions attempted), `elapsed_time` (float seconds from runner start to end), `error_count` (count of steps with failure outcome across run_history), `success` (bool), and `timestamp`

7. **Given** an interrupted or crashed multi-cycle workflow
   **When** the runner is restarted
   **Then** it reads the atomic JSON state file and resumes from the start of the current, incomplete cycle.

## Tasks / Subtasks

- [x] 1. Update `RunState` and models to track multi-cycle execution progress and atomic JSON stringification. (AC: 4, 7)
- [x] 2. Update `RunCompleted` dataclass in `events.py` to add missing fields: `total_step_count` (int), `elapsed_time` (float). Then update Runner to emit `RunCompleted` at end of `run()`, computing all fields from `run_history`. (AC: 6)
- [x] 3. Implement a dedicated `PromptResolver` component for safe variable resolution using whitelist-based key substitution (no `str.format()`/`str.Template`/recursive resolution). Raise `TemplateVariableError` on missing required variables. (AC: 5)
- [x] 4. Add `pause_between_cycle_types` config field (distinct from existing `pause_between_cycles`) and implement the pause in Runner between sequential cycle type executions. (AC: 1, 2)
- [x] 5. Update the existing `Runner` class in `engine/runner.py` (already has basic cycle loop). (AC: 3)
  - [x] Wire subsystems using dependency injection (emitter, state_manager, prompt_resolver, config).
  - [x] Add elapsed time tracking (record start time at beginning of `run()`).
  - [x] Build cumulative template context: after each cycle type completes, merge its output variables into the shared context passed to subsequent cycle types.
  - [x] Ensure cycle-type failure halts the run (existing abort logic, verify against CycleExecutor outcome).
  - [x] Implement crash-resumption: on restart, infer next cycle type from `run_history` tail (incomplete = no outcome or outcome is None).
- [x] 6. Write tests for PromptResolver (whitelist resolution, missing variable exception, injection resistance) and Runner (multi-cycle sequencing, pause between cycle types, RunCompleted emission, cross-cycle template propagation, crash resume). (AC: 1-7)

## Dev Notes

- **Architecture Rules:** The `Runner` orchestrates cycle type sequencing; process management stays in `CycleExecutor` (already implemented in 3.4). Use Dependency Injection in `Runner` construction to avoid God Object anti-patterns. The Runner already exists with basic cycle looping — extend it, don't rewrite.
- **State Management:** Use the established atomic persistence pattern (temp file + `os.replace()` in same directory) via `StateManager`. No file locking needed — the atomic rename is the concurrency-safe mechanism. Crash recovery: infer next cycle type from `run_history` tail (last `CycleRecord` with `outcome=None` or missing = incomplete).
- **Events:** All event dataclasses must be immutable (`@dataclass(frozen=True)`). The `RunCompleted` dataclass needs `total_step_count` (int) and `elapsed_time` (float) added to its existing fields before emission.
- **Template Variables:** Implement `PromptResolver` using whitelist-based key substitution: iterate known keys and replace `{key}` occurrences. Do NOT use `str.format()`, `str.Template`, or recursive resolution — these are injection vectors. Raise `TemplateVariableError` on missing required variables. The Runner must maintain a cumulative `template_context: dict[str, str]` that grows as cycle types complete (each cycle type can register output variables).
- **Terminology:** "Cycle type" = one of story/atdd/dev. "Cycle" = a single execution of a cycle type (may repeat per config). `pause_between_cycles` = existing config for repeats within a type. `pause_between_cycle_types` = new config for pauses between sequential types in a workflow.

### Project Structure Notes

- Alignment with unified project structure: The `Runner` sits in `src/bmad_orch/engine/runner.py`.
- Event definitions live in `src/bmad_orch/engine/events.py`.
- The `CycleExecutor` (Story 3.4) likely lives in `src/bmad_orch/engine/cycle.py`. The runner acts as its caller.

### Previous Story Intelligence

- **Story 3.5 Learnings:** We now have a robust error classification system that emits `ErrorOccurred` inside the `CycleExecutor`. The overall `Runner` should catch or aggregate these results across multiple cycles and reflect them in `RunCompleted`.

### References

- [Source: Epic 3 - Core Cycle Engine]
- [Source: Core Architectural Decisions - Engine Architecture]
- [Source: Core Architectural Decisions - Structured Logging]

## Dev Agent Record

### Agent Model Used
Antigravity
### Debug Log References

### Completion Notes List
✅ Implemented multi-cycle parsing and Runner pause between cycle types
✅ Added PromptResolver for safe variable injection and TemplateVariableError
✅ Ensured cycle failures abort the whole workflow plan
✅ RunCompleted now reports total steps, error count, elapsed time
✅ Handled crash recovery gracefully by skipping successful cycle types on restarts

### File List
- src/bmad_orch/config/schema.py
- src/bmad_orch/state/schema.py
- src/bmad_orch/engine/events.py
- src/bmad_orch/engine/cycle.py
- src/bmad_orch/engine/runner.py
- src/bmad_orch/engine/prompt_resolver.py
- src/bmad_orch/exceptions.py
- tests/test_engine/test_events.py
- tests/test_engine/test_cycle.py
- tests/test_engine/test_runner.py
- tests/test_engine/test_prompt_resolver.py
- src/bmad_orch/cli.py
- tests/test_cli_discovery_atdd.py
- tests/test_cli_preflight.py
- tests/test_config/test_discovery_atdd.py
- tests/test_config_discovery.py
- tests/test_error_classification.py
- tests/test_runner_atdd.py

### Change Log
- Added pause_between_cycle_types to OrchestratorConfig
- Tracked template_context incrementally in RunState
- Added total_step_count and elapsed_time to RunCompleted
- Created whitelist-based PromptResolver component
- Updated Runner workflow orchestrator to sequence multiple cycle types and resume properly
- Fixed crash-resumption logic in CycleExecutor to skip duplicate already-successful repetitions.
- Implemented file path output variable extraction in CycleExecutor for template context.
