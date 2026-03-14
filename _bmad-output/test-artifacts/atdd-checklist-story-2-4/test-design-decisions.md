# Test Design Decisions

- **Backend stack** — no E2E/browser tests; unit + CLI integration levels only
- **Mock adapters** — `DetectedAdapter`, `UndetectedAdapter`, `ExplodingAdapter` stubs isolate provider detection logic
- **Config factory** — `_make_config()` builds minimal `OrchestratorConfig` objects for each scenario
- **CLI tests use `CliRunner`** — consistent with existing ATDD patterns (`test_cli_discovery_atdd.py`)
- **AC3 uses `--dry-run`** — validates provider availability without requiring full cycle execution infrastructure
- **AC5 covers four scenarios** — exception as unavailable, WARNING to stderr, continues checking others, referenced exploding provider raises
