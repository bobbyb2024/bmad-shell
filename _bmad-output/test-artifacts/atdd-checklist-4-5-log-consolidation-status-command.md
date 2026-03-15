---
stepsCompleted:
  - step-01-preflight-and-context
  - step-02-generation-mode
  - step-03-test-strategy
  - step-04-generate-tests
lastStep: step-04-generate-tests
lastSaved: '2026-03-15'
inputDocuments:
  - _bmad-output/implementation-artifacts/4-5-log-consolidation-status-command.md
  - tests/conftest.py
  - tests/test_emergency_flow_atdd.py
---

# ATDD Checklist — Story 4.5: Log Consolidation & Status Command

## Preflight

- **Stack**: Backend (Python/pytest)
- **Story**: 4-5-log-consolidation-status-command
- **Framework**: pytest >= 9.0.2, pytest-asyncio, typer CliRunner
- **Generation Mode**: AI Generation (backend — no browser recording)

## Test Strategy

| AC | Test Level | Priority | Scenarios |
|----|-----------|----------|-----------|
| AC1 | Unit + Integration | P0 | Log file written on completion/halt, failure isolation, atomic write |
| AC2 | Unit | P0 | Chronological ordering, ISO-8601 UTC, metadata header, line format |
| AC3 | Integration (CLI) | P0 | Status display all RunStatus values, elapsed time, exit codes 0/3 |
| AC4 | Integration (CLI) | P1 | Missing state → exit 1, --run-id not found |
| AC5 | Integration (CLI) | P1 | Failure details, conditional resume suggestion, NON_RECOVERABLE constant |
| AC6 | Integration (CLI) | P1 | --json valid JSON, schema match, suppressed Rich output |
| AC7 | Unit | P2 | Auto-create parent directories |
| AC8 | Unit | P1 | Resumed run full history, atomic overwrite |

## Generated Test Files

### `tests/test_logs_atdd.py` — Log Consolidation (AC 1, 2, 7, 8)

| # | Class | Test | AC | Priority |
|---|-------|------|----|----------|
| 1 | TestConsolidateLogsExists | test_consolidate_logs_importable | AC1 | P0 |
| 2 | TestConsolidateLogsExists | test_consolidate_logs_signature | AC1 | P0 |
| 3 | TestConsolidateLogsOutput | test_log_file_written_to_expected_path | AC1 | P0 |
| 4 | TestConsolidateLogsOutput | test_log_file_not_empty | AC1 | P0 |
| 5 | TestAtomicWrite | test_no_partial_file_on_completion | AC1 | P0 |
| 6 | TestAtomicWrite | test_atomic_overwrite_on_repeated_consolidation | AC8 | P1 |
| 7 | TestLogConsolidationFailureIsolation | test_consolidation_io_error_does_not_raise | AC1 | P0 |
| 8 | TestLogConsolidationFailureIsolation | test_consolidation_failure_logs_to_stderr | AC1 | P0 |
| 9 | TestLogMetadataHeader | test_header_contains_run_id | AC2 | P0 |
| 10 | TestLogMetadataHeader | test_header_contains_config_info | AC2 | P0 |
| 11 | TestLogLineFormat | test_log_line_contains_cycle_index | AC2 | P0 |
| 12 | TestLogLineFormat | test_log_line_contains_step_id | AC2 | P0 |
| 13 | TestLogLineFormat | test_log_line_contains_provider_name | AC2 | P0 |
| 14 | TestLogLineFormat | test_log_line_contains_outcome | AC2 | P0 |
| 15 | TestLogLineFormat | test_log_line_includes_error_message_when_present | AC2 | P0 |
| 16 | TestLogLineFormat | test_log_line_no_error_when_none | AC2 | P1 |
| 17 | TestLogLineFormat | test_log_line_provider_none_shown_as_none | AC2 | P2 |
| 18 | TestLogTimestampFormatting | test_timestamp_is_iso8601_utc | AC2 | P0 |
| 19 | TestLogTimestampFormatting | test_naive_timestamp_treated_as_utc | AC2 | P0 |
| 20 | TestLogTimestampFormatting | test_aware_timestamp_converted_to_utc | AC2 | P1 |
| 21 | TestLogChronologicalOrdering | test_steps_ordered_by_timestamp | AC2 | P0 |
| 22 | TestLogChronologicalOrdering | test_tiebreaker_cycle_index_then_step_index | AC2 | P0 |
| 23 | TestAutoCreateDirectories | test_creates_missing_parent_directories | AC7 | P2 |
| 24 | TestResumedRunHistory | test_includes_pre_resume_steps | AC8 | P1 |
| 25 | TestEdgeCases | test_empty_run_history | AC1 | P2 |
| 26 | TestEdgeCases | test_cycle_with_no_steps | AC1 | P2 |
| 27 | TestRunnerCallsConsolidateLogs | test_emergency_halt_calls_consolidate_logs | AC1 | P0 |
| 28 | TestRunnerCallsConsolidateLogs | test_run_completion_calls_consolidate_logs | AC1 | P0 |
| 29 | TestResumeCallsConsolidateLogs | test_resume_flow_calls_consolidate_logs | AC8 | P1 |

### `tests/test_status_atdd.py` — Status Command (AC 3, 4, 5, 6)

| # | Class | Test | AC | Priority |
|---|-------|------|----|----------|
| 1 | TestStatusDisplayCompleted | test_completed_run_shows_status | AC3 | P0 |
| 2 | TestStatusDisplayCompleted | test_completed_run_shows_last_step | AC3 | P0 |
| 3 | TestStatusDisplayCompleted | test_completed_run_shows_cycle_progress | AC3 | P0 |
| 4 | TestStatusDisplayCompleted | test_completed_run_shows_elapsed_time | AC3 | P0 |
| 5 | TestStatusDisplayCompleted | test_completed_run_exit_code_0 | AC3 | P0 |
| 6 | TestStatusDisplayRunning | test_running_shows_elapsed_since_start | AC3 | P0 |
| 7 | TestStatusDisplayRunning | test_running_exit_code_0 | AC3 | P0 |
| 8 | TestStatusDisplayPending | test_pending_shows_not_started | AC3 | P0 |
| 9 | TestStatusDisplayFailed | test_failed_run_exit_code_3 | AC3 | P0 |
| 10 | TestStatusDisplayFailed | test_failed_shows_failure_point | AC5 | P1 |
| 11 | TestStatusDisplayFailed | test_failed_shows_failure_reason | AC5 | P1 |
| 12 | TestStatusDisplayFailed | test_failed_shows_error_type | AC5 | P1 |
| 13 | TestStatusDisplayFailed | test_failed_suggests_resume_for_recoverable | AC5 | P1 |
| 14 | TestStatusDisplayFailed | test_failed_no_resume_for_config_error | AC5 | P1 |
| 15 | TestStatusDisplayFailed | test_failed_no_resume_for_schema_validation_error | AC5 | P1 |
| 16 | TestStatusDisplayFailed | test_failed_no_resume_for_system_error | AC5 | P1 |
| 17 | TestStatusDisplayHalted | test_halted_run_exit_code_3 | AC3 | P0 |
| 18 | TestStatusDisplayHalted | test_halted_suggests_resume | AC5 | P1 |
| 19 | TestStatusMissingState | test_no_state_file_exit_code_1 | AC4 | P1 |
| 20 | TestStatusMissingState | test_no_state_file_reports_to_stderr | AC4 | P1 |
| 21 | TestStatusMissingState | test_specific_run_id_not_found_exit_code_1 | AC4 | P1 |
| 22 | TestStatusCorruptedState | test_corrupted_json_exit_code_2 | AC3 | P1 |
| 23 | TestStatusCorruptedState | test_invalid_schema_exit_code_2 | AC3 | P1 |
| 24 | TestStatusCorruptedState | test_corrupted_reports_to_stderr | AC3 | P1 |
| 25 | TestNonRecoverableErrorTypes | test_constant_exists | AC5 | P1 |
| 26 | TestNonRecoverableErrorTypes | test_constant_contains_required_types | AC5 | P1 |
| 27 | TestNonRecoverableErrorTypes | test_constant_is_set_of_strings | AC5 | P2 |
| 28 | TestStatusJsonOutput | test_json_flag_outputs_valid_json | AC6 | P1 |
| 29 | TestStatusJsonOutput | test_json_output_matches_run_state_schema | AC6 | P1 |
| 30 | TestStatusJsonOutput | test_json_output_has_iso8601_datetimes | AC6 | P1 |
| 31 | TestStatusJsonOutput | test_json_output_has_enum_as_string | AC6 | P1 |
| 32 | TestStatusJsonOutput | test_json_flag_suppresses_rich_output | AC6 | P0 |
| 33 | TestStatusJsonOutput | test_json_uses_model_dump_json_indent_2 | AC6 | P2 |
| 34 | TestStatusRunIdOption | test_run_id_option_accepted | AC3 | P1 |
| 35 | TestStatusRunIdOption | test_run_id_loads_correct_state | AC3 | P1 |
| 36 | TestStatusDoesNotStartRun | test_status_does_not_invoke_runner | AC3 | P0 |

## TDD Red Phase Compliance

- All 65 tests use `@pytest.mark.skip(reason="ATDD red phase: Story 4.5 not implemented")`
- All tests assert EXPECTED behavior that does not exist yet
- No test will pass until implementation is complete
- Tests follow existing ATDD patterns from `test_emergency_flow_atdd.py`

## AC Coverage Matrix

| AC | Tests | Status |
|----|-------|--------|
| AC1 | 10 tests (consolidation output, atomic write, failure isolation, runner wiring) | Covered |
| AC2 | 13 tests (format, timestamps, ordering, metadata header) | Covered |
| AC3 | 14 tests (status display all states, exit codes, --run-id, corrupted) | Covered |
| AC4 | 3 tests (missing state, specific run-id not found) | Covered |
| AC5 | 10 tests (failure details, resume suggestion, NON_RECOVERABLE constant) | Covered |
| AC6 | 6 tests (--json valid JSON, schema, formatting, suppression) | Covered |
| AC7 | 1 test (auto-create directories) | Covered |
| AC8 | 3 tests (full history, atomic overwrite, resume wiring) | Covered |
