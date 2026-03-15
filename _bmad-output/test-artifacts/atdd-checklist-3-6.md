---
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-03-14'
inputDocuments:
  - _bmad-output/implementation-artifacts/3-6-multi-cycle-workflow-orchestration.md
---

# Preflight & Context Loading Summary

## Stack Detection
**Detected Stack:** `backend` (Found `pyproject.toml` and `tests` directory)

## Prerequisites
- **Story Status:** Approved with clear acceptance criteria (Story 3.6).
- **Test Framework:** Present (`tests` folder).
- **Environment:** Available.

## Loaded Context
- Story 3.6: Multi-Cycle Workflow Orchestration
- Acceptance criteria (7 total, including crash resumption and strict error halting).
- TEA Config loaded.
- Knowledge fragments to be referenced for backend testing:
  - `data-factories.md`
  - `component-tdd.md`
  - `test-quality.md`
  - `test-healing-patterns.md`
  - `test-levels-framework.md`
  - `test-priorities-matrix.md`
  - `ci-burn-in.md`

All prerequisites are met. Ready for user confirmation and moving to Generation Mode (step-02).

# Generation Mode Selection

**Mode Chosen:** Default Mode (AI Generation)
**Reason:** The target stack is `backend` (Python/Pytest). Story 3.6 focuses on the Runner engine architecture, orchestration, and state mechanics, requiring programmatic API and behavior tests rather than complex UI browser automation.

# Test Strategy

## 1. Acceptance Criteria Mapping & Test Levels
- **AC1: Execution Order & Fatal Halts**
  - Scenario: Three cycles defined, run in sequence.
  - Scenario: Second cycle throws fatal error, third cycle must not run.
  - Level: Integration
- **AC2: Pauses Between Workflows**
  - Scenario: Engine pauses according to config between components.
  - Level: Unit (Mocked sleep/clock)
- **AC3: Dependency Injection**
  - Scenario: Runner initializes and coordinates subsystems without tight coupling.
  - Level: Unit
- **AC4 & AC7: Atomic File State & Crash Resumption**
  - Scenario: Engine accurately writes progress out to atomic JSON state file with explicit locking.
  - Scenario: Runner initializes, detects interrupted JSON state file, and resumes from incomplete cycle.
  - Level: Integration
- **AC5: Safe Prompt Resolution**
  - Scenario: PromptContext securely evaluates variables.
  - Scenario: PromptContext raises specific Exception gracefully catching missing variables.
  - Level: Unit
- **AC6: RunCompleted Events**
  - Scenario: `RunCompleted` event emits with total step count, error count, elapsed time, and final success boolean.
  - Level: Integration

## 2. Prioritization
- **P0:** AC1 (Execution Order / Halting), AC4 & AC7 (State save/resume), AC5 (Prompt evaluation safety/errors)
- **P1:** AC3 (Dependency Injection), AC6 (Event Metrics / Accuracy)
- **P2:** AC2 (Configured UI/CLI pauses)

## 3. Red Phase Readiness
All tests proposed can and should be written prior to modifying `engine/runner.py` or implementing `PromptContext`. They will mock the required behavior and correctly output RED failures on execution until implementation logic creates the classes.

# ATDD Checklist: Sprint Story 3.6

## TDD Red Phase (Current)

✅ Failing tests generated

- API Tests (Backend Python UI/Integration tests): 7 tests (all skipped with `@pytest.mark.skip`)
- E2E Tests: 0 tests (Not applicable for pure backend stack)

## Acceptance Criteria Coverage

- AC1 Execution Order & Halts: `test_execution_order_and_fatal_halts`
- AC2 Pauses Between Cycles: `test_pauses_between_workflows`
- AC3 Dependency Injection: `test_dependency_injection_coordination` 
- AC4 & AC7 Atomic File State/Resume: `test_atomic_file_state`, `test_crash_resumption`
- AC5 Safe Prompt Resolution: `test_safe_prompt_resolution`
- AC6 Run Completed Metrics: `test_run_completed_events`

## Next Steps (TDD Green Phase)

After implementing the feature `src/bmad_orch/engine/runner.py`:

1. Remove `@pytest.mark.skip(reason="TDD RED PHASE")` from all test functions in `tests/test_runner_atdd.py`.
2. Run tests: `pytest tests/test_runner_atdd.py`
3. Verify tests PASS (green phase)
4. If any tests fail:
   - Either fix implementation (feature bug)
   - Or fix test (test bug)
5. Commit passing tests

## Implementation Guidance

Runner logic to implement:
- Subsystem initialization via constructor injection.
- Ordered run execution mapping string config sequences to internal function dispatches.
- Atomic `json.dump` / file lock system for the internal session config updates on disk.

# Completion Summary
- **Test Files Created:** `tests/test_runner_atdd.py`
- **Output Validation:** Verified backend assumptions matching target platform Pytest.
- **Key Risks:** Ensuring Atomic file locks do not fail cross-platform or deadlock the runner loop. Dependency Injection mapping must be clean. 
- **Next Supported Workflow:** Run implementation workflow (`bmad-quick-dev` or `bmad-dev-story` for story 3-6) using the new FAILING tests.
