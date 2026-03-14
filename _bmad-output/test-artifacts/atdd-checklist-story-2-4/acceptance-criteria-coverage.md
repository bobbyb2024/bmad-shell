# Acceptance Criteria Coverage

| AC | Description | Unit Tests | Integration Tests | Priority |
|----|-------------|-----------|-------------------|----------|
| AC1 | Missing Provider Warning | 3 tests (error raised, guidance text, adapter named) | 2 tests (validate exit 2, start exit 2) | P0 |
| AC2 | Single-Provider Validation | 2 tests (passes, no warnings) | 1 test (validate exit 0) | P0 |
| AC3 | Execution with Single Provider | — | 1 test (dry-run no warnings, exit 0) | P0 |
| AC4 | No Provider Error | 3 tests (error raised, lists adapters, message text) | 2 tests (validate exit 2, install hints) | P0 |
| AC5 | Detection Failure Handling | 4 tests (unavailable, WARNING stderr, continues, referenced raises) | — | P1 |
