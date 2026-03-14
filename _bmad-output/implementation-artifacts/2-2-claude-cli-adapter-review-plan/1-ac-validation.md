# 1. AC Validation
- [x] **AC1: Claude CLI Detection** - Verified. `shutil.which` is used.
- [ ] **AC2: Claude Model Listing** - **PARTIAL**. Fallback is implemented, but primary command invocation and error handling for failed/malformed output are missing.
- [x] **AC3: Prompt Execution & Auth** - Verified. `env` dict is passed, no `os.environ` manipulation.
- [x] **AC4: Output Streaming & Metadata** - Verified. `execution_id` is attached by base class. (Note: helper method name differs but intent is met).
- [x] **AC5: Successful Completion** - Verified. `spawn_pty_process` handles exit codes.
- [x] **AC6: Process Termination Context** - Verified. Version info appended to exceptions.
- [x] **AC7: Defensive Parsing** - Verified. HTML and binary checks implemented in first 1KB.
- [x] **AC8: Graceful Cancellation** - Verified. `spawn_pty_process` implements SIGTERM -> SIGKILL with grace period.
