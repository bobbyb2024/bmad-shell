# Code Review Plan - Story 2.2: Claude CLI Adapter

## 1. AC Validation
- [x] **AC1: Claude CLI Detection** - Verified. `shutil.which` is used.
- [ ] **AC2: Claude Model Listing** - **PARTIAL**. Fallback is implemented, but primary command invocation and error handling for failed/malformed output are missing.
- [x] **AC3: Prompt Execution & Auth** - Verified. `env` dict is passed, no `os.environ` manipulation.
- [x] **AC4: Output Streaming & Metadata** - Verified. `execution_id` is attached by base class. (Note: helper method name differs but intent is met).
- [x] **AC5: Successful Completion** - Verified. `spawn_pty_process` handles exit codes.
- [x] **AC6: Process Termination Context** - Verified. Version info appended to exceptions.
- [x] **AC7: Defensive Parsing** - Verified. HTML and binary checks implemented in first 1KB.
- [x] **AC8: Graceful Cancellation** - Verified. `spawn_pty_process` implements SIGTERM -> SIGKILL with grace period.

## 2. Task Audit
- [x] Task 1.1: Create `src/bmad_orch/providers/claude.py` - Done.
- [x] Task 1.2: Implement `detect()` with caching - Done (but can be improved to use `path`).
- [ ] Task 1.3: Implement `list_models()` with error handling - **NOT DONE**. Only fallback is implemented.
- [x] Task 1.4: Register `ClaudeAdapter` - Done.
- [x] Task 2.1: Implement `execute()` delegating to `spawn_pty_process` - Done.
- [x] Task 2.2: Extend `spawn_pty_process` for `env` - Done.
- [x] Task 2.3: Pass `ANTHROPIC_API_KEY` via `env` - Done.
- [x] Task 2.4: Defensive output validation - Done.
- [x] Task 2.5: Graceful cancellation - Done.
- [x] Task 3.1-3.5: Write tests - Done (but missing binary check and grace period test).

## 3. Code Quality & Security
- **Security**: Environment variables are handled correctly. No sensitive data logged.
- **Performance**: Defensive parsing limited to first 1KB. PTY capture is efficient.
- **Error Handling**: `grace_period` conversion in `ClaudeAdapter` needs to be safer.
- **Maintainability**: Code is well-structured and follows patterns.

## 4. Test Quality
- Missing test for binary detection in AC7.
- Missing test for `CLAUDE_TERMINATION_GRACE_PERIOD` override.
- `detect()` test doesn't verify the `path` usage.

## 5. Planned Fixes
1. Update `ClaudeAdapter.list_models()` to attempt CLI command first.
2. Update `ClaudeAdapter.detect()` to use absolute path for version check.
3. Add safety to `grace_period` conversion.
4. Enhance tests in `tests/test_providers/test_claude.py`.
