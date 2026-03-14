---
stepsCompleted:
  - step-01-preflight-and-context
  - step-02-generation-mode
  - step-03-test-strategy
  - step-04c-aggregate
lastStep: step-04c-aggregate
lastSaved: '2026-03-14'
inputDocuments:
  - _bmad-output/implementation-artifacts/2-4-single-provider-graceful-mode.md
  - src/bmad_orch/config/discovery.py
  - src/bmad_orch/cli.py
  - src/bmad_orch/providers/base.py
  - src/bmad_orch/providers/claude.py
  - src/bmad_orch/providers/gemini.py
  - src/bmad_orch/exceptions.py
  - tests/conftest.py
---

# ATDD Checklist: Story 2.4 — Single-Provider Graceful Mode

## TDD Red Phase (Current)

All tests generated with `@pytest.mark.skip` — remove skip after verifying implementation.

### Test Files

| File | Level | Tests | ACs Covered |
|------|-------|-------|-------------|
| `tests/test_provider_availability_atdd.py` | Unit | 12 | AC1, AC2, AC4, AC5 |
| `tests/test_cli_provider_validation_atdd.py` | Integration (CLI) | 6 | AC1, AC2, AC3, AC4 |
| **Total** | | **18** | **AC1–AC5** |

## Acceptance Criteria Coverage

| AC | Description | Unit Tests | Integration Tests | Priority |
|----|-------------|-----------|-------------------|----------|
| AC1 | Missing Provider Warning | 3 tests (error raised, guidance text, adapter named) | 2 tests (validate exit 2, start exit 2) | P0 |
| AC2 | Single-Provider Validation | 2 tests (passes, no warnings) | 1 test (validate exit 0) | P0 |
| AC3 | Execution with Single Provider | — | 1 test (dry-run no warnings, exit 0) | P0 |
| AC4 | No Provider Error | 3 tests (error raised, lists adapters, message text) | 2 tests (validate exit 2, install hints) | P0 |
| AC5 | Detection Failure Handling | 4 tests (unavailable, WARNING stderr, continues, referenced raises) | — | P1 |

## Test Design Decisions

- **Backend stack** — no E2E/browser tests; unit + CLI integration levels only
- **Mock adapters** — `DetectedAdapter`, `UndetectedAdapter`, `ExplodingAdapter` stubs isolate provider detection logic
- **Config factory** — `_make_config()` builds minimal `OrchestratorConfig` objects for each scenario
- **CLI tests use `CliRunner`** — consistent with existing ATDD patterns (`test_cli_discovery_atdd.py`)
- **AC3 uses `--dry-run`** — validates provider availability without requiring full cycle execution infrastructure
- **AC5 covers four scenarios** — exception as unavailable, WARNING to stderr, continues checking others, referenced exploding provider raises

## Next Steps (TDD Green Phase)

After confirming implementation is complete:

1. Remove `@pytest.mark.skip(reason="RED PHASE: ...")` from all 18 tests
2. Run: `uv run pytest tests/test_provider_availability_atdd.py tests/test_cli_provider_validation_atdd.py -v --no-cov`
3. Verify all 18 tests **PASS** (green phase)
4. If any tests fail:
   - Either fix implementation (feature bug)
   - Or fix test (test bug — assertion doesn't match actual behavior)
5. Commit passing tests

## Implementation Guidance

### Functions Under Test

- `bmad_orch.config.discovery.validate_provider_availability(config)` — core validation logic
- `bmad_orch.cli.validate` command — surfaces errors with exit code 2
- `bmad_orch.cli.start` command — calls validation as pre-flight check

### Key Behaviors to Verify

- `ConfigError` raised for missing referenced providers (AC1) and zero providers (AC4)
- Error messages include adapter names and `install_hint` values
- `detect()` exceptions caught gracefully with WARNING to stderr (AC5)
- Single-provider configs pass without warnings (AC2, AC3)
