---
status: done
epic: 4
story: 4.1
title: Git Integration & Configurable Commits
stepsCompleted: []
---

# Story 4.1: Git Integration & Configurable Commits

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **user**,
I want completed work automatically committed and pushed to git at configurable intervals,
so that my artifacts are preserved in version control without manual intervention.

## Acceptance Criteria

1. **Given** the `git.py` module  
   **When** I inspect the `GitClient` class  
   **Then** it provides `add()`, `commit()`, `push()`, `fetch()`, and `status()` methods as hardened subprocess wrappers.

2. **Given** any git operation  
   **When** it is invoked  
   **Then** the subprocess environment sets `GIT_TERMINAL_PROMPT=0`, `GIT_PAGER=cat`, `GIT_EDITOR=true`, `GIT_ASKPASS=echo`, `SSH_ASKPASS=echo`, and `LANG=C` — git never blocks on user input, and fallback environment variables for author name and email are provided if not configured globally.

3. **Given** a config with `git.commit_at: cycle`  
   **When** a cycle completes  
   **Then** the orchestrator commits all orchestrator output and logs to git.

4. **Given** a config with `git.commit_at: step`  
   **When** a step completes  
   **Then** the orchestrator commits after every step.

5. **Given** a config with `git.push_at: end`  
   **When** the entire workflow completes  
   **Then** all commits are pushed to the remote in a single push.

6. **Given** a config with `git.push_at: cycle`  
   **When** a cycle completes  
   **Then** commits are pushed after each cycle.

7. **Given** a git operation that encounters a lock file (`index.lock` or `HEAD.lock`)  
   **When** the error is detected  
   **Then** the system retries up to 10 times with 1-second delays, and if the lock persists, raises `GitError` with a clear message identifying the lock file (it never silently deletes the lock file).

8. **Given** a git push that fails due to network, auth issues, or remote rejection (e.g., non-fast-forward)  
   **When** the error is detected  
   **Then** the system logs the failure with a clear error message identifying the cause rather than failing silently, and does NOT attempt to automatically pull/rebase. The runner catches push errors and logs them as warnings to prevent failing the entire orchestrator run after artifacts are safely committed locally.

9. **Given** a git commit operation  
   **When** there are no staged changes to commit  
   **Then** the commit operation gracefully no-ops instead of throwing an error.

10. **Given** a dynamic output path to be added to git  
    **When** the `GitClient` initializes  
    **Then** the system detects if the output path is outside the git repository root and immediately raises a configuration error (failing fast) instead of waiting until a commit is attempted.

11. **Given** the `add()` operation
    **When** it adds files
    **Then** it strictly respects the project's `.gitignore` by never using `git add --force`, ensuring ignored files are never staged.

12. **Given** `git.enabled: true` in config
    **When** the `GitClient` initializes
    **Then** it verifies the working directory is inside a git repository (via `git rev-parse --is-inside-work-tree`) and raises `GitError` immediately if not, failing fast at startup rather than mid-run.

13. **Given** `git.enabled: false` in config (the default)
    **When** the runner executes steps and cycles
    **Then** no `GitClient` is instantiated and all commit/push operations are skipped entirely.

14. **Given** a git operation that exceeds its timeout (30s for local ops, 60s for push)
    **When** the timeout expires
    **Then** the subprocess is killed, and a `GitError` is raised with a message identifying the operation and timeout duration.

15. **Given** a config with `git.commit_at: never` or `git.push_at: never`
    **When** cycles and steps complete
    **Then** the runner skips the corresponding commit or push operations entirely.

## Tasks / Subtasks

- [x] 1. Create `src/bmad_orch/git.py` with `GitClient` class. (AC: 1, 2, 11)
  - [x] Implement `_run_git` private helper using `asyncio.create_subprocess_exec` with hardened environment variables (including `LANG=C`, `GIT_ASKPASS=echo`), a timeout mechanism, and returning `tuple[int, str, str]` (exit code, stdout, stderr).
  - [x] Define `GitStatus` dataclass (fields: `is_clean: bool`, `branch: str | None`, `ahead: int`, `behind: int`).
  - [x] Implement `add(paths: list[str])`, ensuring it never uses `--force` so `.gitignore` is respected.
  - [x] Implement `fetch()`, `commit(message: str)`, `push(remote: str, branch: str)`, and `status()` returning a parsed `GitStatus` dataclass.
- [x] 2. Implement error detection in `GitClient`. (AC: 7, 8, 9)
  - [x] Detect lock contention (`index.lock`, `HEAD.lock`), retry up to 10 times with 1-second delays, then raise `GitError`.
  - [x] Detect push failures (network/auth/rejected) and log/raise appropriate errors without auto-rebase.
  - [x] Gracefully handle 'nothing to commit' scenarios.
  - [x] Check for global git config during initialization (`git config --get user.name`) to determine if fallbacks are needed. Ensure git commit doesn't crash on unconfigured user.name/user.email by providing fallbacks, and log a warning when fallbacks are used.
- [x] 3. Update `config/schema.py` with git configuration Pydantic models. (AC: 3, 4, 5, 6, 13, 15)
  - [x] Add `GitConfig` model with `enabled: bool` (default `False`), `commit_at: Literal["step", "cycle", "never"]` (default `"cycle"`), `push_at: Literal["cycle", "end", "never"]` (default `"end"`), `remote: str` (default `"origin"`), `branch: str | None` (default `None` = current HEAD branch), and `commit_message_template: str | None` (default `None`; uses Python `string.Template` with keys: `$granularity`, `$status`, `$name`).
  - [x] Add Pydantic model validation to ensure `push_at` is `never` if `commit_at` is `never`.
  - [x] Integrate `GitConfig` into the root config model.
- [x] 4. Update `engine/runner.py` to integrate `GitClient`. (AC: 3, 4, 5, 6, 10, 12, 13, 14, 15)
  - [x] Ensure `GitClient` is injected into `Runner` (skip injection if `git.enabled` is `false`).
  - [x] Implement commit logic based on `git.commit_at` (STEP or CYCLE).
  - [x] Implement push logic based on `git.push_at` (CYCLE or END).
  - [x] Runner validates dynamic configured output paths are within the git repo at startup before executing.
  - [x] Include step/cycle outcome (success/fail) in the commit message, utilizing `commit_message_template` if provided (rendered via `string.Template` with `$granularity`, `$status`, `$name`).
  - [x] Initialize `GitClient` with repo validation (AC 12) only when `git.enabled: true`; skip entirely when `false` (AC 13).
- [x] 5. Create `tests/test_git.py` for verification. (AC: 1-15)
  - [x] Mock git subprocess calls to verify environment variables, timeouts, and error handling.
  - [x] Test `GitClient` methods in isolation, including out-of-bounds path handling at init and lock detection.
  - [x] Test `Runner` integration via integration tests.
  - [x] Test `git.enabled: false` results in no git operations.
  - [x] Test timeout kills subprocess and raises `GitError`.
  - [x] Test `commit_at: never` and `push_at: never` skip operations.
  - [x] Test non-git-repo initialization raises `GitError` immediately.

## Dev Notes

### Technical Requirements
- **Module Location:** `src/bmad_orch/git.py`
- **Class Name:** `GitClient`
- **Hardening:** Environment variables `GIT_TERMINAL_PROMPT=0`, `GIT_PAGER=cat`, `GIT_EDITOR=true`, `GIT_ASKPASS=echo`, `SSH_ASKPASS=echo`, and `LANG=C` must be set for all git calls. Check global git config at startup; fallbacks like `GIT_AUTHOR_NAME="bmad-orch[bot]"`, `GIT_AUTHOR_EMAIL="bmad-orch@localhost"`, `GIT_COMMITTER_NAME="bmad-orch[bot]"`, `GIT_COMMITTER_EMAIL="bmad-orch@localhost"` should be applied if the user lacks global git config.
- **Async Pattern:** Use `asyncio.create_subprocess_exec` for all git operations. Follow the subprocess lifecycle pattern (try/finally with kill/wait). Wrap git calls in `asyncio.wait_for` (e.g., 30s for local ops, 60s for push) to prevent hanging the orchestrator.
- **Error Handling:** Extend `GitError` from `errors.py`. Severity should be standard `ERROR` or `FATAL` for most git failures.
- **Logging:** Use `structlog`. Follow sentence case, no trailing period, and context binding. Log a warning when default git author identity fallbacks are used.

### Architecture Compliance
- **Dependency Isolation:** `git.py` should only depend on `asyncio`, `os`, `pathlib`, `structlog`, and internal `errors.py`/`types.py`.
- **Imports:** Use absolute imports for cross-package dependencies (e.g., `from bmad_orch.errors import GitError`).
- **Typing:** Fully annotate all public methods. Use `py.typed` marker. Define a `GitStatus` dataclass for the return type of `status()`.
- **__all__:** Include `__all__ = ["GitClient", "GitStatus"]` in `src/bmad_orch/git.py`.

### Commit Message & Staging
- **Commit message format:** `chore(bmad-orch): auto-commit after $granularity ($status) — $name` (default, overrideable via `commit_message_template` using Python `string.Template` with keys `granularity` ("step"|"cycle"), `status` ("success"|"failure"), `name` (step or cycle identifier)).
- **Staged paths:** Only dynamic output directories based on the orchestrator's configuration (e.g. `config.output_dir`) and orchestrator log files. Never stage user source code or unrelated files.
- **Default remote/branch:** `push()` defaults to `origin` and the current HEAD branch unless overridden by `git.remote` and `git.branch` config keys.

### Edge Cases
- **Non-git-repo:** On initialization, `GitClient` must verify the working directory is a git repository using `git rev-parse --is-inside-work-tree` (do not just check for a `.git` directory to support worktrees). If not, raise `GitError` with a clear message. If `git.enabled: true` but no repo exists, fail fast at startup — do not fail silently mid-run.
- **`git.enabled: false`:** Disables all git operations. Runner skips commit/push entirely. This is the escape hatch for users who don't want git integration.
- **`status()` method:** Returns the current working tree status (clean/dirty, branch name, ahead/behind counts) via `GitStatus`. Used by the `bmad-orch status` command (Story 4.5) and by the runner to skip no-op commits when the tree is clean. Getting an accurate `behind` count requires calling `fetch()` first.
- **Push granularity asymmetry:** `push_at` intentionally does not support `step` — pushing after every step would generate excessive network traffic and remote churn. This is by design per the epic.

### Project Structure Notes
- **Source:** `src/bmad_orch/git.py`
- **Tests:** `tests/test_git.py`

### References
- [Source: _bmad-output/planning-artifacts/epics/epic-4-reliable-unattended-execution.md#Story 4.1]
- [Source: _bmad-output/planning-artifacts/architecture/implementation-patterns-consistency-rules.md]
- [Source: _bmad-output/planning-artifacts/architecture/core-architectural-decisions.md#Git Integration]

## Dev Agent Record

### Agent Model Used
Gemini 2.0 Flash

### Debug Log References
- Successfully implemented GitClient with subprocess hardening.
- Integrated GitClient into Runner and CycleExecutor.
- Updated config schema with GitConfig and validation logic.
- Verified with comprehensive tests and ran existing test suite.

### Completion Notes List
- Implemented `GitClient` in `src/bmad_orch/git.py` with full AC compliance.
- Added identity fallbacks for unconfigured git environments.
- Integrated commit/push logic into `CycleExecutor` for step/cycle granularity.
- Integrated push logic into `Runner` for end-of-run synchronization.
- Updated `OrchestratorConfig` to include `GitConfig`.

### File List
- src/bmad_orch/git.py
- src/bmad_orch/exceptions.py (existing, used GitError)
- src/bmad_orch/config/schema.py
- src/bmad_orch/engine/runner.py
- src/bmad_orch/engine/cycle.py
- src/bmad_orch/types/__init__.py
- tests/test_git.py
- tests/test_runner_atdd.py (updated)
- tests/test_config/test_schema.py (updated)

## Change Log
- 2026-03-14: Initial implementation of Git Integration & Configurable Commits.
- 2026-03-14: Code review fixes applied — path validation hardened (AC10), log file staging added, test coverage expanded (6 new tests), RuntimeWarning fixed.
- 2026-03-15: Code review #2 fixes — fixed broken timeout assertion in test_git_push_timeout_uses_60s (would pass for any non-zero timeout), added missing AC15 tests for commit_at/push_at never, removed dead Timing enum from types/__init__.py.

## Status
done
