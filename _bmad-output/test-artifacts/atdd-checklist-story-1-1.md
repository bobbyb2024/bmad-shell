---
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-03-13'
storyId: 'story-1-1'
storyName: 'Project Scaffolding & Tooling Setup'
detectedStack: 'backend'
generationMode: 'ai-generation'
executionMode: 'subagent'
inputDocuments:
  - '_bmad-output/implementation-artifacts/1-1-project-scaffolding-setup.md'
  - '_bmad-output/planning-artifacts/epics.md'
  - '_bmad/tea/config.yaml'
---

# ATDD Checklist — Story 1.1: Project Scaffolding & Tooling Setup

## TDD Red Phase (Current)

✅ **Failing tests generated**

- **Smoke Tests:** 10 tests (all skipped) in `tests/test_smoke.py`
- **Unit Tests:** 26 tests (all skipped) in `tests/test_types.py`, `tests/test_errors.py`
- **Integration/CLI Tests:** 14 tests (all skipped) in `tests/test_cli.py`, `tests/test_tooling.py`, `tests/test_layer_packages.py`
- **Structural Tests:** 44 tests (all skipped) in `tests/test_project_structure.py`, `tests/test_dependencies.py`, `tests/test_config_sections.py`, `tests/test_ci_workflows.py`, `tests/test_gitignore.py`

## Acceptance Criteria Coverage

| AC | Scenario | Test File | Status |
|----|----------|-----------|--------|
| AC1 | Project structure (`src/bmad_orch/`, etc.) | `tests/test_project_structure.py` | 🔴 RED (skipped) |
| AC2 | `.python-version` pins 3.13 | `tests/test_project_structure.py` | 🔴 RED (skipped) |
| AC3 | `uv.lock` exists | `tests/test_project_structure.py` | 🔴 RED (skipped) |
| AC4 | Dependencies in `pyproject.toml` | `tests/test_dependencies.py` | 🔴 RED (skipped) |
| AC5 | Dev dependencies in `pyproject.toml` | `tests/test_dependencies.py` | 🔴 RED (skipped) |
| AC6 | Core types instantiation | `tests/test_types.py` | 🔴 RED (skipped) |
| AC7 | Error hierarchy instantiation | `tests/test_errors.py` | 🔴 RED (skipped) |
| AC8 | CLI help and subcommands | `tests/test_cli.py`, `tests/test_smoke.py` | 🔴 RED (skipped) |
| AC9 | `--init` callback behavior | `tests/test_cli.py` | 🔴 RED (skipped) |
| AC10 | Linters and Pyright configuration | `tests/test_tooling.py`, `tests/test_config_sections.py` | 🔴 RED (skipped) |
| AC11 | Layer packages and stubs | `tests/test_layer_packages.py` | 🔴 RED (skipped) |
| AC12 | Import Linter enforcement | `tests/test_tooling.py`, `tests/test_config_sections.py` | 🔴 RED (skipped) |
| AC13 | Pre-commit configuration | `tests/test_ci_workflows.py` | 🔴 RED (skipped) |
| AC14 | CI workflow definitions | `tests/test_ci_workflows.py` | 🔴 RED (skipped) |
| AC15 | Lazy imports for rich/libtmux | `tests/test_smoke.py`, `tests/test_tooling.py` | 🔴 RED (skipped) |

## Next Steps (TDD Green Phase)

After implementing Story 1.1:

1. Remove `@pytest.mark.skip(reason="TDD red phase - not yet implemented")` from all test files.
2. Run tests: `uv run pytest`.
3. Verify tests PASS (green phase).
4. If any tests fail:
   - Either fix implementation (feature bug)
   - Or fix test (test bug)
5. Commit passing tests.

## Implementation Guidance

### Core Files to Implement:
- `src/bmad_orch/types.py`
- `src/bmad_orch/errors.py`
- `src/bmad_orch/cli.py`
- Layered package structure under `src/bmad_orch/`

### Tools to Configure:
- `pyproject.toml` sections for ruff, pyright, pytest, importlinter
- `.pre-commit-config.yaml`
- `.github/workflows/ci.yml`

## Completion Summary

- **Status:** TDD Red Phase Complete
- **Tests Created:** 94 test cases across 12 files
- **Verification:** All tests collect and skip successfully
- **Artifacts:** Story file and ATDD checklist created
- **Recommendation:** Proceed to `bmad-dev-story` for implementation
