# Epic 4: Reliable Unattended Execution

User runs `bmad-orch start --headless` and returns to completed, committed, auditable work — with git integration, resume capability, resource monitoring, emergency error handling, structured headless output, and CI/CD exit code contract.

## Story 4.1: Git Integration & Configurable Commits

As a **user**,
I want completed work automatically committed and pushed to git at configurable intervals,
So that my artifacts are preserved in version control without manual intervention.

**Acceptance Criteria:**

**Given** the `git.py` module
**When** I inspect the `GitClient` class
**Then** it provides `add()`, `commit()`, `push()`, and `status()` methods as hardened subprocess wrappers

**Given** any git operation
**When** it is invoked
**Then** the subprocess environment sets `GIT_TERMINAL_PROMPT=0`, `GIT_PAGER=cat`, and `GIT_EDITOR=true` — git never blocks on user input

**Given** a config with `git.commit_at: cycle`
**When** a cycle completes
**Then** the orchestrator commits all orchestrator output and logs to git

**Given** a config with `git.commit_at: step`
**When** a step completes
**Then** the orchestrator commits after every step

**Given** a config with `git.push_at: end`
**When** the entire workflow completes
**Then** all commits are pushed to the remote in a single push

**Given** a config with `git.push_at: cycle`
**When** a cycle completes
**Then** commits are pushed after each cycle

**Given** a git operation that encounters a lock file (`index.lock`)
**When** the error is detected
**Then** the system reports the lock file contention with a clear error message — it does not silently delete the lock file

**Given** a git push that fails due to network or auth issues
**When** the error is detected
**Then** the system logs the failure with a clear error message identifying the cause (network, auth, remote rejection) rather than failing silently

## Story 4.2: Emergency Error Flow & Impactful Error Handling

As a **user**,
I want the orchestrator to preserve all completed work when a serious error occurs,
So that I never lose progress and can resume from a known good state.

**Acceptance Criteria:**

**Given** an impactful error occurs during step execution (provider crash, resource violation)
**When** the impactful error flow triggers
**Then** the orchestrator executes in order: update state file atomically → commit to git → push to remote → halt execution

**Given** the emergency commit + push sequence
**When** a step in the sequence fails (e.g., push fails due to network)
**Then** the orchestrator logs the secondary failure and continues the halt sequence — it does not retry the emergency sequence indefinitely

**Given** an impactful error
**When** execution halts
**Then** the state file records the failure point, the error details, the last successfully completed step, and a timestamp

**Given** an impactful error in headless mode
**When** execution halts
**Then** the process exits with exit code 3 (runtime error) or 4 (provider error) as appropriate

**Given** an impactful error in any mode
**When** the error is surfaced
**Then** the error follows the headline format: `✗ [What happened] — run bmad-orch resume`

**Given** a user abort (Ctrl+C or Ctrl+A in TUI)
**When** the abort is processed
**Then** it follows the same emergency flow: commit state + push + clean exit — treated as intentional halt, not error

## Story 4.3: Resource Monitoring

As a **user**,
I want the orchestrator to prevent runaway processes from consuming all system resources,
So that my machine remains responsive even when AI CLI subprocesses misbehave.

**Acceptance Criteria:**

**Given** the `resources.py` module
**When** the resource monitor starts
**Then** it launches an async periodic polling task using psutil at a configurable interval (default 5 seconds)

**Given** the resource monitor is active
**When** it polls
**Then** it tracks CPU and memory usage for the orchestrator process and all spawned subprocess PIDs

**Given** combined CPU usage exceeds 80% of system capacity
**When** the threshold is breached
**Then** the resource monitor identifies the offending subprocess, calls `process.kill()` + `await process.wait()`, and emits a `ResourceThresholdBreached` event

**Given** combined memory usage exceeds 80% of system memory
**When** the threshold is breached
**Then** the resource monitor kills the offending subprocess and emits a `ResourceThresholdBreached` event

**Given** a `ResourceThresholdBreached` event
**When** it is processed by the engine
**Then** the engine treats it as an impactful error — triggering emergency commit + push + halt

**Given** the resource monitor
**When** it is active
**Then** it runs in both interactive and headless modes with identical behavior

**Given** a step completes normally
**When** the next step has not yet started
**Then** the resource monitor does not leak tracking of previously completed subprocess PIDs — each step cleans up fully

## Story 4.4: Resume Flow & Recovery

As a **user**,
I want to resume from any failure point with clear context about what happened,
So that I can make an informed decision about how to continue without investigating logs.

**Acceptance Criteria:**

**Given** a previous run that failed
**When** I run `bmad-orch resume`
**Then** the system loads the state file and displays a resume context screen showing: last run timestamp, stopped-at point (cycle type, step number, provider), failure reason, and completed work summary

**Given** the resume context screen
**When** it is displayed
**Then** it presents four numbered options: [1] Re-run failed step, [2] Skip failed step and continue to next, [3] Restart current cycle from step 1, [4] Start from scratch

**Given** the resume options
**When** the user selects option 1 (re-run)
**Then** execution resumes from the exact failed step with the same provider and prompt

**Given** the resume options
**When** the user selects option 2 (skip)
**Then** the failed step is logged as skipped and execution continues to the next step

**Given** the resume options
**When** the user selects option 3 (restart cycle)
**Then** the current cycle restarts from its first step

**Given** the resume options
**When** the user selects option 4 (start fresh)
**Then** the entire workflow restarts from the beginning (state file is reset)

**Given** no previous run exists (no state file)
**When** I run `bmad-orch resume`
**Then** the system exits with a clear message: `✗ No previous run found — use bmad-orch start`

**Given** a run that completed successfully (no failure)
**When** I run `bmad-orch resume`
**Then** the system reports the previous run completed successfully and suggests `bmad-orch start` for a new run

**Given** a run started in headless mode
**When** I resume in TUI mode (or vice versa)
**Then** the resume works correctly — the state file is portable across modes

## Story 4.5: Log Consolidation & Status Command

As a **user**,
I want consolidated logs and a quick status check,
So that I can understand what happened in a run and check on current state without starting execution.

**Acceptance Criteria:**

**Given** a workflow with multiple completed steps each producing per-step log entries
**When** a git commit is triggered (per config timing)
**Then** all per-step logs are consolidated into a single run log file before the commit

**Given** the consolidated log file
**When** I inspect its contents
**Then** entries are ordered chronologically with consistent formatting: timestamps, step identifiers, provider tags, and severity levels across all steps

**Given** a running or completed orchestrator run
**When** I run `bmad-orch status`
**Then** the system displays: current/last run state, which step is active or was last completed, provider used, cycle progress, and any errors — without starting a new run

**Given** no state file exists
**When** I run `bmad-orch status`
**Then** the system reports no previous runs found

**Given** a state file from a failed run
**When** I run `bmad-orch status`
**Then** the output includes the failure point, failure reason, and suggests `bmad-orch resume`

## Story 4.6: Headless Renderer & Exit Code Contract

As a **CI/CD pipeline operator**,
I want zero-interaction execution with structured output and meaningful exit codes,
So that the orchestrator integrates cleanly into automated pipelines.

**Acceptance Criteria:**

**Given** the `rendering/headless.py` module
**When** it receives engine events
**Then** it produces structured plain text output with zero ANSI escape codes

**Given** headless mode
**When** operational output is produced
**Then** it is written to stdout

**Given** headless mode
**When** errors occur
**Then** error output is written to stderr

**Given** headless mode structured log output
**When** I inspect the format
**Then** each line follows: `[ISO-8601 timestamp] [SEVERITY] [cycle/step] [provider/model] Message`

**Given** a successful headless run
**When** the workflow completes
**Then** stdout shows a summary line: `Run complete. N stories, M commits, E errors, Tm elapsed`
**And** the process exits with code 0

**Given** a headless run with a usage error (bad flags, missing args)
**When** the error is detected
**Then** the process exits with code 1

**Given** a headless run with a config error
**When** the error is detected
**Then** the process exits with code 2

**Given** a headless run with a runtime error (impactful failure during execution)
**When** execution halts
**Then** the process exits with code 3

**Given** a headless run where all retries are exhausted for a provider
**When** execution halts
**Then** the process exits with code 4

**Given** the headless renderer
**When** I inspect its imports
**Then** it has no dependency on Rich or libtmux — only structlog and standard library
