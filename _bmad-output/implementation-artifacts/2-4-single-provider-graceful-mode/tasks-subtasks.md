# Tasks / Subtasks

- [x] Task 1: Add Provider Availability Validation to Config Loader (AC: 1, 2, 4, 5)
  - [x] 1.1: In `src/bmad_orch/config/discovery.py`, add a `validate_provider_availability()` function that iterates over providers referenced in the config and calls each adapter's `detect()` method.
  - [x] 1.2: Wrap each `detect()` call in exception handling — on failure, print warning to stderr and mark the provider as unavailable (AC5).
  - [x] 1.3: Implement `ConfigError` raise for "missing but referenced" providers (AC1) with a message naming each missing adapter, its install hint, and the "update your config" guidance.
  - [x] 1.4: Implement `ConfigError` raise for "zero providers detected" (AC4) listing all registered adapters with install hints.
  - [x] 1.5: Ensure single-provider configs pass validation without warnings (AC2).
- [x] Task 2: Integrate Validation into CLI Entry Points (AC: 1, 3, 4)
  - [x] 2.1: In `src/bmad_orch/cli.py`, call `validate_provider_availability()` during the `validate` subcommand and as a pre-flight check in the `start` command.
  - [x] 2.2: Confirm that after successful validation, cycle execution emits no provider-availability warnings (AC3).
- [x] Task 3: Write Tests (AC: 1-5)
  - [x] 3.1: Create `tests/test_config_discovery.py` with fixtures for mocked adapter `detect()` results.
  - [x] 3.2: Test AC1: config references two providers, only one detected — assert `ConfigError` raised and message names the missing provider with install hint and guidance.
  - [x] 3.3: Test AC2: config references one provider, it is detected — assert validation passes.
  - [x] 3.4: Test AC4: no providers detected — assert `ConfigError` raised and message contains install hints for all registered adapters.
  - [x] 3.5: Test AC5: `detect()` raises an exception — assert provider treated as unavailable and warning printed to stderr.
  - [x] 3.6: Test AC3: Integration test running a single-provider cycle to ensure zero warnings and exit code 0.
