---
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-03-13'
inputDocuments:
  - '_bmad-output/implementation-artifacts/1-2-configuration-schema-validation-models.md'
  - '_bmad/tea/config.yaml'
  - '_bmad/tea/testarch/tea-index.csv'
---

# ATDD Checklist — Story 1-2: Configuration Schema & Validation Models

## Step 1: Preflight & Context

### Stack Detection
- **Detected stack:** backend (Python 3.13 + pytest 9.x)
- Auto-detected from: `pyproject.toml` (pydantic, pytest, ruff, pyright)
- No frontend indicators found

### Prerequisites
- Story approved with 6 acceptance criteria: PASS
- Test framework configured (pytest, conftest.py): PASS
- Dev environment available (uv run pytest): PASS

### TEA Config
- test_stack_type: auto → backend
- tea_use_playwright_utils: true (N/A — JS-only)
- tea_use_pactjs_utils: true (N/A — JS-only)
- tea_pact_mcp: mcp (N/A for this story)
- tea_browser_automation: auto (N/A — no UI)

### Knowledge Fragments Loaded
- Core: data-factories, test-quality, test-healing-patterns
- Backend: test-levels-framework, test-priorities-matrix
- Extended: component-tdd

## Step 2: Generation Mode

**Mode: AI Generation**
- Reason: Backend Python project with clear acceptance criteria for Pydantic model validation
- No browser recording needed
- All 6 ACs map to standard validation test patterns

## Step 3: Test Strategy

### AC → Test Scenario Mapping

| AC | Scenario | Level | Priority |
|---|---|---|---|
| AC1 | Valid complete YAML → OrchestratorConfig with all typed sub-models | Unit | P0 |
| AC2 | Missing required section → ConfigError with field name (×3 sections) | Unit | P0 |
| AC3 | Invalid enum value → ConfigError with field, value, valid options (×2 enums) | Unit | P0/P1 |
| AC4 | StepConfig enforces typed fields + rejects wrong types | Unit | P1 |
| AC5 | CycleConfig validates steps, repeat, optional pauses (×4 scenarios) | Unit | P1/P2 |
| AC6 | Cross-field validation, validate_config wrapper, extra keys (×5 scenarios) | Unit | P0/P1 |
| Edge | Numeric boundary validation (max_retries, pauses, empty strings) (×6 scenarios) | Unit | P2 |

- **All Unit level** — pure Pydantic model validation, no I/O
- **P0:** 6 tests | **P1:** 7 tests | **P2:** 5 tests + 5 edge = 10 tests
- **Red phase guaranteed:** `schema.py` does not exist

## Step 4: Test Generation (Aggregated)

### Generated Files
- `tests/test_config/__init__.py` — empty package marker
- `tests/test_config/test_schema.py` — 23 ATDD tests (all `@pytest.mark.skip`)

### TDD Red Phase Compliance
- All 23 tests use `@pytest.mark.skip(reason="TDD RED PHASE: schema.py not implemented")`
- All tests assert expected behavior (no placeholder assertions)
- pytest collection: 23 collected, 23 skipped
- No fixture infrastructure needed (module-level `VALID_CONFIG` dict)

### AC Coverage: 6/6 (100%)

| AC | Tests | Priority |
|---|---|---|
| AC1 | 1 | P0 |
| AC2 | 3 | P0 |
| AC3 | 2 | P0/P1 |
| AC4 | 2 | P1 |
| AC5 | 4 | P1/P2 |
| AC6 | 5 | P0/P1 |
| Edge | 6 | P2 |

## Step 5: Validation & Completion

### Validation Results

| Check | Status |
|---|---|
| Prerequisites (story, pytest, dev env) | PASS |
| Test file created (`tests/test_config/test_schema.py`) | PASS |
| Package marker (`tests/test_config/__init__.py`) | PASS |
| 23 tests collected by pytest | PASS |
| All 23 tests skipped (TDD red phase) | PASS |
| 6/6 acceptance criteria covered | PASS |
| Real assertions (no placeholders) | PASS |
| No orphaned sessions / temp files | PASS |

### Assumptions

- `Timing` enum will be in `src/bmad_orch/types/__init__.py` with values: `step`, `cycle`, `end`
- `validate_config(data: dict) -> OrchestratorConfig` wraps `ValidationError` in `ConfigError`
- All Pydantic models use `ConfigDict(extra="forbid")`

### Next Steps (TDD Green Phase)

1. Implement `src/bmad_orch/config/schema.py` — use `/bmad-dev-story 1-2`
2. Remove `@pytest.mark.skip` from all 23 tests
3. Run: `uv run pytest tests/test_config/`
4. Full checks: `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest`
