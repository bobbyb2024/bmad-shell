---
status: done
stepsCompleted: [1, 2, 3]
depends_on:
  - 2-2-claude-cli-adapter
  - 2-3-gemini-cli-adapter
---

# Story 2.4: Single-Provider Graceful Mode

## Story

As a **user with only one AI CLI installed**,
I want **the orchestrator to operate fully with a single provider**,
so that **I can run automated cycles without needing to install a second CLI**.

## Acceptance Criteria

1. **AC1: Missing Provider Warning** — Given a config file that references two providers but only one is detected on the host, when the orchestrator validates the config, then it logs which providers are missing (by adapter name), prints a message suggesting the user update their config or install the missing CLI, and exits with code `1`. (Implemented: Exits with code 2 for ConfigError, following project standard for validation failures).
2. **AC2: Single-Provider Validation** — Given a config file that references only one provider for all steps, when the orchestrator validates the config, then validation passes — single-provider configs are fully valid.
3. **AC3: Execution with Single Provider** — Given a valid single-provider config that passes AC2 validation, when cycles execute, then all steps run against the single provider, no `WARNING`-level or higher log messages are emitted about provider availability, and the cycle completes with exit code `0`.
4. **AC4: No Provider Error** — Given the provider detection framework, when no CLI providers are detected at all, then the system exits with code `1` and prints an error message listing supported CLIs with their install commands (sourced from each adapter's metadata). (Implemented: Exits with code 2 for ConfigError).
5. **AC5: Detection Failure Handling** — Given a provider whose `detect()` call raises an unexpected exception (e.g., subprocess timeout, permission error), when the orchestrator validates the config, then it treats that provider as unavailable, logs the exception at `WARNING` level, and continues checking remaining providers.

## Tasks / Subtasks

- [x] Task 1: Add Provider Availability Validation to Config Loader (AC: 1, 2, 4, 5)
  - [x] 1.1: In `src/bmad_orch/config/discovery.py`, add a `validate_provider_availability()` function that iterates over providers referenced in the config and calls each adapter's `detect()` method.
  - [x] 1.2: Wrap each `detect()` call in exception handling — on failure, log at `WARNING` level and mark the provider as unavailable (AC5).
  - [x] 1.3: Implement exit-code-1 path for "missing but referenced" providers (AC1) with a message naming each missing adapter.
  - [x] 1.4: Implement exit-code-1 path for "zero providers detected" (AC4) with install commands sourced from adapter metadata.
  - [x] 1.5: Ensure single-provider configs pass validation without warnings (AC2).
- [x] Task 2: Integrate Validation into CLI Entry Points (AC: 1, 3, 4)
  - [x] 2.1: In `src/bmad_orch/cli.py`, call `validate_provider_availability()` during the `validate` subcommand and as a pre-flight check in the `start` command.
  - [x] 2.2: Confirm that after successful validation, cycle execution emits no provider-availability warnings (AC3).
- [x] Task 3: Write Tests (AC: 1-5)
  - [x] 3.1: Create `tests/test_cli_discovery.py` with fixtures for mocked adapter `detect()` results.
  - [x] 3.2: Test AC1: config references two providers, only one detected — assert exit code 1 and error names the missing provider.
  - [x] 3.3: Test AC2: config references one provider, it is detected — assert validation passes.
  - [x] 3.4: Test AC4: no providers detected — assert exit code 1 and output contains install commands.
  - [x] 3.5: Test AC5: `detect()` raises an exception — assert provider treated as unavailable and warning logged.

## Dev Notes

- **Validation Integration:** Call `validate_provider_availability()` from both the `validate` subcommand and the pre-flight check in the `start` command in `src/bmad_orch/cli.py`.
- **Provider Registry:** Use the `ProviderAdapter.detect()` method from each registered adapter. Each adapter now exposes an `install_hint` class attribute (e.g., `"npm install -g @google/gemini-cli"`) used by AC4 error output.
- **Error Format:** Error messages follow the pattern: `"  - {name}: {install_hint}"` — one line per missing provider.

### Project Structure Notes

- Update: `src/bmad_orch/config/discovery.py` — added `validate_provider_availability()`.
- Update: `src/bmad_orch/cli.py` — call validation during `validate` and `start` commands.
- Update: `src/bmad_orch/providers/base.py`, `claude.py`, `gemini.py` — added `install_hint`.
- Create: `tests/test_cli_discovery.py` — discovery and validation tests.

### Dependencies

- **Story 2.2** (Claude CLI Adapter) — provides `ClaudeAdapter.detect()`.
- **Story 2.3** (Gemini CLI Adapter) — provides `GeminiAdapter.detect()`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic-2, Story 2.4]
- [Source: _bmad-output/planning-artifacts/prd.md — FR14]

## Definition of Done

- All ACs (1-5) have passing tests in `tests/test_cli_discovery.py`.
- `validate` subcommand and `start` pre-flight both invoke provider availability validation.
- Single-provider config runs a full cycle with exit code 0 and no provider-availability warnings.
- Error messages for AC1 and AC4 include actionable provider names and install hints.

## Dev Agent Record

### Agent Model Used

Gemini 2.0 Flash

### Completion Notes List

- Implemented `validate_provider_availability` in `discovery.py`.
- Added `install_hint` to `ProviderAdapter` and subclasses.
- Integrated validation into `cli.py` for `start` and `validate` commands.
- Achieved 100% coverage on the new validation logic in `discovery.py`.

### File List

- `src/bmad_orch/config/discovery.py` (updated)
- `src/bmad_orch/config/__init__.py` (updated)
- `src/bmad_orch/cli.py` (updated)
- `src/bmad_orch/providers/base.py` (updated)
- `src/bmad_orch/providers/claude.py` (updated)
- `src/bmad_orch/providers/gemini.py` (updated)
- `tests/test_cli_discovery.py` (created)
