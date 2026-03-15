# 3. Challenges & Friction Points

## pytest Not Installed (Critical — Biggest Friction Point)

The development environment did not have pytest installed during story implementation. This was the single most impactful process failure in the epic:

- **Tests were written blind** — dev agents authored tests without being able to run them
- **Broken imports survived until review** — e.g., `from tests.conftest import VALID_CONFIG_DATA` caused `ModuleNotFoundError` but wasn't caught during development
- **Type errors persisted** — `GeminiAdapter.__init__` not accepting config arguments caused `TypeError` that only surfaced during review
- **Review round inflation** — Story 2-3 needed 3 rounds (vs target of 2) largely because issues that a test run would have caught instantly were discovered iteratively in review

**Impact**: This gap potentially affects Epics 1 and 2 — any story developed without a functional test runner may have latent test failures. A full test suite audit is required.

## PTY Complexity Underestimated

The PTY-based process execution in Story 2-1 revealed several non-obvious challenges:

- **`EIO` error handling**: PTY reading requires catching `OSError` with `errno.EIO` specifically — a non-obvious failure mode
- **Merged stdout/stderr**: PTY merges both streams, forcing the design decision to drop `stream_type` from `OutputChunk`
- **Process group termination**: Initial implementation killed only the direct process; fix required `os.killpg()` to terminate child processes spawned by CLIs
- **`pty.fork()` rejected**: For async safety and fork-safety concerns, `os.openpty()` was chosen instead — adding complexity but gaining correctness

## UTF-8 Decoding Edge Case Missed

The initial PTY implementation was vulnerable to buffer overflows from invalid UTF-8 sequences. This was caught in code review, not during development. The fix (switching to `codecs.getincrementaldecoder` with `errors="replace"`) was straightforward but highlights that boundary-condition testing at the byte level needs more attention.

## Story 2-3 Scope Larger Than Estimated

The Gemini CLI adapter required 3 review rounds — the most of any story — due to inherently more complex requirements:

- Dual API key support (`GEMINI_API_KEY` and `GOOGLE_API_KEY`)
- Retry logic with exponential backoff (AC9) — absent from Claude adapter
- Configurable fallback models
- Sliding window for defensive parsing
- `execution_id` instability across retries (HIGH severity, found in Round 1)

The scope gap between 2-2 (Claude) and 2-3 (Gemini) suggests that adapter stories should be sized based on provider-specific complexity, not assumed to be uniform.

## Rename Ripple Effects

The `errors.py` to `exceptions.py` rename in Story 2-1 touched 10+ files across the project. The dev agent initially failed to document all affected imports, requiring the review round to catch missing updates. Future renames of widely-imported modules should include a systematic grep-and-update step as part of the task definition.

## Defensive Parsing Inconsistency

Claude adapter checks the first 1KB of output for errors; Gemini adapter checks the first 2KB plus continuous monitoring with a sliding window. Both check for HTML errors, binary data, and proxy errors, but Gemini also checks for `403 Forbidden` and `PERMISSION_DENIED`. This inconsistency could lead to different failure behaviors for the same type of corrupted output.

## Weak Test Assertions (Recurring Pattern)

Multiple stories had test assertions that were too loose:

- `or` fallback assertions in 3 test locations that could mask real failures (Story 2-4)
- `"Missing" in msg` instead of checking the actual AC guidance string (Story 2-4)
- `test_list_models_fallback` didn't mock `shutil.which` and could pass for the wrong reason (Story 2-2)
- Class-level `MagicMock` patching that only worked because MagicMock silently ignores implicit `self` (Story 2-4)
