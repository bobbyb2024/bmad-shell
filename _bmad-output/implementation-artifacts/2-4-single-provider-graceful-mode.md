# Story 2.4: Single-Provider Graceful Mode

Status: ready-for-dev

## Story

As a **user with only one AI CLI installed**,
I want **the orchestrator to operate fully with a single provider**,
so that **I can run automated cycles without needing to install a second CLI**.

## Acceptance Criteria

1. **AC1: Missing Provider Warning** — Given a config file that references two providers but only one is detected on the host, when the orchestrator validates the config, then it reports which providers are missing and exits with a clear error suggesting the user update their config or install the missing CLI.
2. **AC2: Single-Provider Validation** — Given a config file that references only one provider for all steps, when the orchestrator validates the config, then validation passes — single-provider configs are fully valid.
3. **AC3: Execution with Single Provider** — Given a single-provider config, when cycles execute, then all steps run against the single provider with no errors or warnings about missing adversarial validation during execution (validation should have happened at startup).
4. **AC4: No Provider Error** — Given the provider detection framework, when no CLI providers are detected at all, then the system exits with a clear error message and helpful install links for supported CLIs.

## Tasks / Subtasks

- [ ] Task 1: Update Config Validation (AC: 1, 2, 4)
  - [ ] 1.1: Update `src/bmad_orch/config/loader.py` (or wherever validation lives) to check provider availability via `detect()`.
  - [ ] 1.2: Implement logic to distinguish between "missing but required" (AC1) and "not found at all" (AC4).
- [ ] Task 2: Ensure Graceful Operation (AC: 3)
  - [ ] 2.1: Verify that the engine handles single-provider configs without overhead or warnings.
- [ ] Task 3: Write comprehensive tests (AC: 1-4)
  - [ ] 3.1: Create `tests/test_cli_discovery.py` or similar to test discovery logic.
  - [ ] 3.2: Test AC1: mismatched config and environment.
  - [ ] 3.3: Test AC2: valid single-provider config.
  - [ ] 3.4: Test AC4: zero providers found.

## Dev Notes

- **Validation:** This logic should probably be integrated into the `validate` subcommand and the pre-flight check in the `start` command.
- **Provider Registry:** Use the `ProviderAdapter.detect()` method from each registered adapter.

### Project Structure Notes

- Update: `src/bmad_orch/config/loader.py` (or similar).
- Update: `src/bmad_orch/cli.py` to call detection during validation.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic-2, Story 2.4]
- [Source: _bmad-output/planning-artifacts/prd.md — FR14]

## Dev Agent Record

### Agent Model Used

Gemini 2.0 Flash

### Debug Log References

### Completion Notes List

### File List

- `src/bmad_orch/config/loader.py` (updated)
- `src/bmad_orch/cli.py` (updated)
- `tests/test_cli_discovery.py`
