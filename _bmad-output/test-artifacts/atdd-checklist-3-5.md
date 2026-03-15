---
stepsCompleted:
  - step-01-preflight-and-context
  - step-02-generation-mode
  - step-03-test-strategy
  - step-04c-aggregate
  - step-05-validate-and-complete
lastStep: step-05-validate-and-complete
lastSaved: '2026-03-14T19:10:00-04:00'
inputDocuments:
  - _bmad-output/implementation-artifacts/3-5-error-detection-classification.md
  - _bmad/bmm/config.yaml
  - _bmad/tea/config.yaml
  - _bmad/tea/testarch/tea-index.csv
---

# Preflight & Context Loading Summary

## 1. Stack Detection
- **Detected Stack**: `backend` (Auto-detected via `pyproject.toml` and `tests/conftest.py`).

## 2. Prerequisites
- **Status**: ✅ All requirements met.
- Story 3-5 found and loaded.
- Test framework detected (`pytest` structure).
- Development environment available.

## 3. Story Context
- **Story**: 3.5: Error Detection & Classification
- **Key Constraints**: 
  - Subprocess cleanup via `process.kill()` + `await process.wait()`
  - Emit immutable `ErrorOccurred` events for IMPACTFUL errors
  - Structured logging strict format: `✗ [What happened] — [What to do next]`
  - Use `ErrorSeverity` enum instead of `isinstance()` checks

## 4. Framework & Existing Patterns
- Using Python `pytest`. 
- `tea_use_playwright_utils` is enabled, applying API-only profile.
- `tea_pact_mcp` is set to "mcp".

## 5. Knowledge Base Fragments Selected
- **Core**: `data-factories`, `component-tdd`, `test-quality`, `test-healing-patterns`
- **Backend**: `test-levels-framework`, `test-priorities-matrix`, `ci-burn-in`
- **Playwright (API Profile)**: `overview`, `api-request`, `auth-session`, `recurse`
- **Pact/MCP**: `pact-mcp`

## Step 2: Generation Mode
- **Mode Selected:** Default Mode: AI Generation
- **Reasoning:** The detected stack is `backend` and this story relates to core engine exception handling logic without any UI elements. Complex browser recording represents unnecessary overhead, so AI generation from the story requirements and codebase will be used.

## Step 3: Test Strategy

### 1. Acceptance Criteria Mapping & 2. Test Levels
- **Scenario 1:** Rate limit error (HTTP 429 / CLI equivalent) is classified as `RECOVERABLE` + `ProviderTimeoutError`. (Level: **Unit**)
- **Scenario 2:** Subprocess crash is classified as `IMPACTFUL` + `ProviderCrashError`. (Level: **Unit**)
- **Scenario 3:** Engine executes recoverable error -> continuous execution, silent to user, logs with full contextvars. (Level: **Integration**)
- **Scenario 4:** Engine executes impactful error -> process zombie cleanup (`kill` + `wait`), `ErrorOccurred` event emitted (immutable). (Level: **Integration**)
- **Scenario 5:** Structured logging format directly validated for `✗ [What happened] — [What to do next]`, ensuring contextvars are bound and unbound later. (Level: **Unit**)
- **Scenario 6:** System routes and handles exceptions checking `error.severity` enum rather than using `isinstance()`. (Level: **Unit**)

### 3. Prioritization
- **P0:** Impactful error classification and handling (event emission + zombie cleanup). Critical for resilience.
- **P0:** Enum-based severity checking over `isinstance()`. Core abstraction logic.
- **P1:** Recoverable error flow (retry/continue without user alert) and proper structured logging format.

### 4. Confirm Red Phase Requirements
- All specified tests are formulated to test unwritten error classification classes, unwritten `ErrorSeverity` enums, and structured logging teardown changes. They are specifically written to fail initially.

## Step 4C: Aggregation & ATDD Checklist

### TDD Red Phase (Current)
✅ Failing tests generated
- API/Backend Tests: 6 tests (all skipped with `@pytest.mark.skip`)
- E2E Tests: 0 tests (backend project, no browser E2E required)

### Acceptance Criteria Coverage
- Rate limit classified as RECOVERABLE + ProviderTimeoutError ✅
- Subprocess crash classified as IMPACTFUL + ProviderCrashError ✅
- Recoverable error execution continues silently ✅
- Impactful error cleans zombie process and emits ErrorOccurred ✅
- Structured logging format validation ✅
- Exception severity enum check ✅

### Next Steps (TDD Green Phase)
After implementing the feature for `3-5-error-detection-classification`:
1. Remove `@pytest.mark.skip(reason="TDD Red Phase")` from all test functions in `tests/test_error_classification.py`.
2. Run tests: `pytest tests/test_error_classification.py`
3. Verify tests PASS (green phase)
4. If any tests fail:
   - Either fix implementation (feature bug)
   - Or fix test (test bug)
5. Commit passing tests

### Implementation Guidance
Feature modules to implement:
- `bmad_core.errors.ErrorSeverity` (Enum)
- `bmad_core.errors.ErrorClassification` (Immutable dataclass)
- `bmad_core.errors.classify_error`
- `bmad_core.engine.CycleExecutor` updates for zombie cleanup (`asyncio.create_subprocess_shell` cleanup)
- `structlog` formatting updates for exception printing

## Step 5: Validate & Complete

### 1. Validation Run
- **Prerequisites Satisfied:** Yes (backend architecture auto-detected).
- **Test files correctly written:** Yes, `tests/test_error_classification.py` covers 6 tests.
- **TDD Red Phase Compliance:** Yes, all initial scenarios appropriately scoped with `@pytest.mark.skip(reason="TDD Red Phase")` waiting for implementation.
- **E2E Browser Context Clean:** Yes, as a backend Python project, no browser E2E instances were generated.

### 2. Final Output Summary
- **Generated Test Artifacts:** `tests/test_error_classification.py`
- **Output Checklist:** `{test_artifacts}/atdd-checklist-3-5.md`
- **Next Recommended Workflow:** Proceed with **Implementation** (development agent) using `bmad-dev-story` or `bmad-quick-dev` to implement the required `ErrorClassification` engine logic and make the TDD tests pass.
