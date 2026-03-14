# Definition of Done

- All ACs (1-5) have passing tests in `tests/test_config_discovery.py`.
- `validate` subcommand and `start` pre-flight both invoke provider availability validation.
- Single-provider config runs a full cycle with exit code 0 and no provider-availability warnings.
- Error messages for AC1 and AC4 include actionable provider names and install hints.
