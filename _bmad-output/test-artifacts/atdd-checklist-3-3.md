---
stepsCompleted:
  - step-01-preflight-and-context
  - step-02-generation-mode
  - step-03-test-strategy
  - step-04c-aggregate
lastStep: step-04c-aggregate
lastSaved: '2026-03-14'
storyFile: _bmad-output/implementation-artifacts/3-3-structured-logging-subsystem.md
detectedStack: backend
generationMode: ai-generation
executionMode: sequential
inputDocuments:
  - _bmad-output/implementation-artifacts/3-3-structured-logging-subsystem.md
  - src/bmad_orch/engine/events.py
  - tests/conftest.py
  - pyproject.toml
---

# ATDD Checklist: Story 3.3 — Structured Logging Subsystem

## TDD Red Phase (Current)

All tests are marked with `pytest.mark.skip(reason="ATDD red phase")` because
`src/bmad_orch/logging.py` does not exist yet.

- **Unit Tests:** 20 tests (all skipped)
- **Integration Tests:** 4 tests (all skipped)
- **Total:** 24 tests across 10 test classes

## Acceptance Criteria Coverage

| AC | Description | Test Class | Tests | Priority | Level |
|----|-------------|-----------|-------|----------|-------|
| AC1 | Human-Readable Logging | `TestAC1HumanReadableLogging` | 4 | P0 | Unit |
| AC2 | Machine-Readable Logging | `TestAC2MachineReadableLogging` | 4 | P0 | Unit |
| AC3 | Async Context Propagation | `TestAC3AsyncContextPropagation` | 2 | P0 | Integration |
| AC4 | Context Isolation & Cleanup | `TestAC4ContextIsolationAndCleanup` | 2 | P0 | Integration |
| AC5 | Per-Step Log Capture | `TestAC5PerStepLogCapture` | 4 | P1 | Unit |
| AC6 | Grep-Friendly Consistency | `TestAC6GrepFriendlyConsistency` | 3 | P0 | Unit |
| AC7 | File-Based Log Persistence | `TestAC7FileBasedLogPersistence` | 3 | P1 | Integration |
| AC8 | Log Consolidation | `TestAC8LogConsolidation` | 2 | P2 | Unit |
| AC9 | Stdlib Logging Bridge | `TestAC9StdlibLoggingBridge` | 2 | P1 | Integration |
| Edge | Negative & Boundary Cases | `TestEdgeCases` | 2 | P1 | Unit |

## Priority Distribution

- **P0 (Critical):** 13 tests — AC1, AC2, AC3, AC4, AC6
- **P1 (High):** 9 tests — AC5, AC7, AC9, Edge Cases
- **P2 (Medium):** 2 tests — AC8

## Test File

- `tests/test_logging.py` — All 24 acceptance tests (skipped)

## Next Steps (TDD Green Phase)

After implementing `src/bmad_orch/logging.py`:

1. Remove `pytest.mark.skip` from each test class as its AC is implemented
2. Run tests: `pytest tests/test_logging.py -v`
3. Verify tests PASS (green phase)
4. If any tests fail:
   - Fix implementation (feature bug) OR
   - Fix test (test bug — update helper capture functions)
5. Commit passing tests

## Implementation Guidance

### Public API to implement in `src/bmad_orch/logging.py`:

- `configure_logging(mode: str, level: str = "INFO") -> None`
- `get_step_logs(step_id: str) -> list[dict[str, str]]`
- `consolidate_step_logs(step_id: str) -> str`
- `async_task_wrapper()` — async context manager for contextvars cleanup

### Key constraints:

- Import `LogLevel` from `engine/events.py` — no duplicate constants
- Use `structlog.contextvars` for async context propagation
- Machine mode: structured plain text, NOT JSON
- File output: always machine-mode format via `RotatingFileHandler` (10MB, 5 backups)
- Buffer: 50,000 global entry cap with LRU eviction
- Stdlib bridge: `structlog.stdlib.ProcessorFormatter`
