---
stepsCompleted:
  - step-01-preflight-and-context
  - step-02-generation-mode
  - step-03-test-strategy
  - step-04c-aggregate
  - step-05-validate-and-complete
lastStep: step-05-validate-and-complete
lastSaved: '2026-03-15'
inputDocuments:
  - _bmad-output/implementation-artifacts/4-2-emergency-error-flow-impactful-error-handling.md
  - src/bmad_orch/state/schema.py
  - src/bmad_orch/state/manager.py
  - src/bmad_orch/engine/runner.py
  - src/bmad_orch/cli.py
  - src/bmad_orch/exceptions.py
  - _bmad/tea/testarch/knowledge-base/data-factories.md
  - _bmad/tea/testarch/knowledge-base/component-tdd.md
  - _bmad/tea/testarch/knowledge-base/test-quality.md
  - _bmad/tea/testarch/knowledge-base/test-healing-patterns.md
  - _bmad/tea/testarch/knowledge-base/test-levels-framework.md
  - _bmad/tea/testarch/knowledge-base/test-priorities-matrix.md
  - _bmad/tea/testarch/knowledge-base/ci-burn-in.md
---

# ATDD Checklist: Story 4.2 — Emergency Error Flow & Impactful Error Handling

## Preflight Summary

- **Stack:** Backend (Python/pytest)
- **Generation Mode:** AI Generation (sequential)
- **Story:** 4.2 — Emergency Error Flow & Impactful Error Handling
- **Framework:** pytest + pytest-asyncio
- **Config Flags:** `test_stack_type: auto` → backend

## TDD Red Phase (Current)

All tests are **skipped** via `@pytest.mark.skip(reason="ATDD red phase: Story 4.2 not implemented")`.

- **Test File:** `tests/test_emergency_flow_atdd.py`
- **Total Tests:** 43 (all skipped)
  - Unit Tests: 19
  - Integration Tests: 24
- **Test Classes:** 12

## Acceptance Criteria Coverage

| AC | Description | Tests | Priority |
|----|-------------|-------|----------|
| AC1 | Emergency flow order: save → commit → push → halt | 4 tests | P0 |
| AC2 | Secondary git failure: log + skip remaining ops | 3 tests | P0 |
| AC3 | State records failure fields (halted_at, failure_point, etc.) | 11 tests | P0/P1 |
| AC4 | Exit codes: 1/2/3/4/130/143 | 7 tests | P1 |
| AC5 | Error headline formatting | 2 tests | P1/P2 |
| AC6 | Signal handling (SIGINT/SIGTERM) | 3 tests | P0/P1 |
| — | Re-entrance guard | 2 tests | P1 |
| — | Subprocess cleanup | 2 tests | P1 |
| — | Partial emergency completion | 2 tests | P1 |
| — | Git commit message format | 1 test | P2 |

## Test Classes Breakdown

| Class | AC | Level | Tests |
|-------|----|-------|-------|
| `TestRunStateFailureFields` | AC3 | Unit | 6 |
| `TestRunStatusEnum` | AC3 | Unit | 5 |
| `TestRecordHalt` | AC3 | Unit | 6 |
| `TestEmergencyFlowOrder` | AC1 | Integration | 4 |
| `TestSecondaryGitFailure` | AC2 | Integration | 3 |
| `TestEmergencyFlowReentrance` | — | Integration | 2 |
| `TestSubprocessCleanup` | — | Unit | 2 |
| `TestExitCodes` | AC4 | Integration | 7 |
| `TestErrorHeadlineFormatting` | AC5 | Unit | 2 |
| `TestSignalHandling` | AC6 | Integration | 3 |
| `TestPartialEmergencyCompletion` | — | Integration | 2 |
| `TestEmergencyGitCommitMessage` | — | Integration | 1 |

## Next Steps (TDD Green Phase)

After implementing Story 4.2:

1. Remove `@pytest.mark.skip` from all tests in `tests/test_emergency_flow_atdd.py`
2. Run tests: `uv run pytest tests/test_emergency_flow_atdd.py -v`
3. Verify tests PASS (green phase)
4. If any tests fail:
   - Fix implementation (feature bug) or fix test (test bug)
5. Commit passing tests

## Implementation Guidance

### Files to Create/Modify

1. **`src/bmad_orch/types/__init__.py`** — Add `RunStatus` enum (PENDING, RUNNING, COMPLETED, FAILED, HALTED)
2. **`src/bmad_orch/state/schema.py`** — Add `status`, `halted_at`, `failure_point`, `failure_reason`, `error_type` to `RunState`
3. **`src/bmad_orch/state/manager.py`** — Add `record_halt()` method
4. **`src/bmad_orch/engine/runner.py`** — Add `_handle_impactful_error()`, `_in_emergency_flow` flag, signal handling
5. **`src/bmad_orch/cli.py`** — Add signal handlers, exit code mapping (3/4/130/143), `format_error_headline()`, `format_abort_headline()`

### Key Patterns

- Atomic state save: write-to-temp-then-rename (same directory)
- Git recursion guard: skip git ops if trigger is `GitError`
- Re-entrance guard: `_in_emergency_flow` flag with try/finally reset
- Subprocess cleanup: `process.kill()` + `await process.wait()` wrapped in `asyncio.shield()`
- Failure point format: `cycle:{n}/step:{step_name}` derived from `run_history`
