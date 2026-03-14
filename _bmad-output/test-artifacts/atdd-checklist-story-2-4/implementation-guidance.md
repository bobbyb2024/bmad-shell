# Implementation Guidance

## Functions Under Test

- `bmad_orch.config.discovery.validate_provider_availability(config)` — core validation logic
- `bmad_orch.cli.validate` command — surfaces errors with exit code 2
- `bmad_orch.cli.start` command — calls validation as pre-flight check

## Key Behaviors to Verify

- `ConfigError` raised for missing referenced providers (AC1) and zero providers (AC4)
- Error messages include adapter names and `install_hint` values
- `detect()` exceptions caught gracefully with WARNING to stderr (AC5)
- Single-provider configs pass without warnings (AC2, AC3)
