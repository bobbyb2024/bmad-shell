# Requirements Inventory

## Functional Requirements

FR1: User can generate a new orchestrator config file through an interactive wizard
FR2: User can define multiple providers with name, CLI command, and model in the config
FR3: User can define cycles with ordered steps, each specifying a skill, provider, step type (generative/validation), and prompt template
FR3a: User can define the execution order of cycles within a workflow
FR4: User can configure cycle repeat counts to control how many times validation steps re-execute
FR5: User can configure pause durations between steps, cycles, and workflows
FR6: User can configure git commit and push timing (per-step, per-cycle, or end-of-run)
FR7: User can configure error handling behavior (retry settings, max retries, retry delay)
FR8: User can specify config file location via command-line flag or convention-based discovery
FR9: System can resolve prompt template variables (e.g., {next_story_id}, {current_story_file}) from orchestrator state; unresolvable variables halt the step with a clear error identifying the missing variable
FR10: System can detect installed CLI tools (Claude, Gemini, others) on the host machine
FR11: System can query a provider's CLI for available models
FR12a: System can invoke a provider's CLI as a subprocess with a configured prompt
FR12b: System can capture stdout and stderr from a running provider subprocess
FR12c: System can detect provider subprocess completion, timeout, or unexpected termination
FR13: System can normalize provider output and error behavior through a provider adapter interface
FR14: System can operate with a single provider when only one is available (graceful degradation)
FR15: System can execute a cycle's steps in configured order
FR16: System can distinguish generative steps (run only on first cycle) from validation steps (run every cycle)
FR17: System can repeat a cycle's validation steps for the configured number of repetitions
FR18: System can execute multiple cycles in sequence (story → atdd → dev) as a complete workflow
FR19: System can pause for configured durations between steps and cycles to manage rate limits
FR20: System can atomically persist execution state to a JSON state file after each step completion
FR21: System can record which step was last completed, which provider executed it, and the outcome
FR22: User can resume execution from the last completed step after an interruption
FR23: User can choose on resume whether to re-run the last step, continue from next, restart the cycle, or start from scratch
FR24: System can maintain a running log of all state changes across multiple runs
FR25: System can capture per-step logs with timestamps, step identifiers, provider tags, and severity levels
FR26: System can consolidate per-step logs into a single run log file before commit
FR27: User can view current orchestrator state without starting a run (status command)
FR28: System can write structured text logs suitable for both human reading and grep-based debugging
FR29: System can commit orchestrator output and logs to git at configurable intervals
FR30: System can push commits to remote at configurable intervals
FR31: System can perform emergency commit and push when an impactful error occurs before halting
FR32: System can display a two-pane tmux layout showing active model output and command/log pane
FR32a: TUI output pane automatically switches to display the currently active model as the cycle progresses
FR33: System can display a status bar showing current phase, step, provider, and cycle progress
FR34: User can pause execution after the current step completes
FR35: User can skip the current step
FR36: User can abort execution (triggering commit + push + halt)
FR37: User can restart the current step
FR38: User can validate a config file for schema correctness, provider availability, and model existence without executing (validate command)
FR39: System can detect and classify errors as recoverable or impactful
FR40: System can log recoverable errors and continue execution
FR41: System can halt execution on impactful errors after committing state and pushing to remote
FR42: Init wizard can detect installed CLI providers and present them for selection
FR43: Init wizard can query selected providers for available models and present them for selection
FR44: Init wizard can offer sensible default cycle configurations that the user can accept or modify
FR45: Init wizard can generate a valid bmad-orch.yaml config file from user selections
FR46: System can display a playbook summary on start showing all cycles, steps, providers, and prompts that will execute, and prompt the user to proceed or modify
FR47: User can perform a dry run that shows the complete execution plan without invoking any providers (--dry-run flag)
FR48: State file maintains a human-readable run history including all completed steps, providers used, outcomes, timestamps, and errors — serving as both machine-parseable state and human-readable audit trail
FR49: User can send input to the active model's subprocess via the command pane when the model is awaiting a response

## NonFunctional Requirements

NFR1: System must maintain consistent state file integrity — a crash or kill at any point must leave the state file in a valid, recoverable condition (atomic writes)
NFR2: System must complete 10+ consecutive story cycles without requiring human intervention for non-content reasons
NFR3: System must detect and recover from transient provider failures (rate limits, timeouts, network interruptions) without corrupting state
NFR4: System must never lose completed work — all successful step outputs must be persisted before the next step begins
NFR5: System must gracefully handle unexpected provider subprocess termination (crash, OOM kill, signal) without entering an unrecoverable state
NFR6: Log files must be complete enough to diagnose any failure without reproducing it — every state transition, provider invocation, and error must be logged with timestamps
NFR7: The orchestrator process plus all spawned CLI subprocesses must not collectively exceed 80% of system CPU usage; the orchestrator must monitor resource consumption continuously
NFR8: The orchestrator must monitor memory usage of itself and spawned subprocesses; if combined usage exceeds 80% of system memory, the orchestrator must kill the offending subprocess and log an impactful error
NFR9: The orchestrator must not leak file handles, subprocess references, or temporary files across step boundaries — each step must clean up fully before the next begins
NFR10: Resource monitoring must be active in both interactive and headless modes
NFR11: When a subprocess is killed for resource violation, the orchestrator must treat it as an impactful error (log, commit, push, halt)
NFR12: Provider adapters must tolerate minor CLI output format changes without breaking — parse defensively, fail explicitly when output is unrecognizable
NFR13: The orchestrator must target current/latest versions of provider CLIs only — no backwards compatibility shims
NFR14: Provider subprocess invocation must be isolated — a hung or misbehaving provider must not block the orchestrator's ability to log, update state, or respond to user commands
NFR15: Git operations must handle common failure cases (lock files, network failures, auth issues) with clear error messages rather than silent failures

## Additional Requirements

- Starter template: `uv init --package bmad-orch` with dependencies (typer, rich, pydantic, pydantic-settings, pyyaml) and dev dependencies (pytest, pytest-cov, pytest-asyncio, pytest-timeout, ruff, pyright, pre-commit)
- Python 3.13 target with `requires-python = ">=3.13"` floor
- Async engine architecture using asyncio as core runtime
- Event emitter pattern (typed frozen dataclass events) for engine-to-presentation decoupling — engine never imports rendering
- PTY-everywhere subprocess I/O: all modes use PTY-based capture; TUI renderer writes captured output to tmux panes
- Provider adapter interface: `async def execute(prompt: str) -> AsyncIterator[OutputChunk]`
- Atomic state writes via temp file + `os.rename()` in same directory
- Structured logging via structlog with `structlog.contextvars` for async-local context propagation
- Hardened git integration: all git calls set `GIT_TERMINAL_PROMPT=0`, `GIT_PAGER=cat`, `GIT_EDITOR=true`
- psutil for resource monitoring via async periodic polling task
- libtmux for tmux interface (lazy import, only when TUI mode activates)
- PyPI distribution via `pipx install bmad-orch` or `uv tool install bmad-orch`
- GitHub Actions CI/CD: PR checks (ruff lint+format, pyright, pytest+coverage, import isolation), release publishes to PyPI on tagged versions
- Exception hierarchy: `BmadOrchError` base with `ConfigError`, `ProviderError` (NotFound/Timeout/Crash), `StateError`, `GitError`, `ResourceError`, `WizardError` — each carries `ErrorSeverity`
- Import isolation enforcement: runtime test asserting core engine modules don't pull in Rich or libtmux
- Dependency graph must be acyclic: types/errors ← config ← state ← providers ← engine ← rendering
- Feature-based module organization with specific directory structure (config/, engine/, providers/, state/, rendering/)
- pre-commit hooks running Ruff + pyright on every commit
- Subprocess lifecycle pattern: try/finally with explicit `process.kill()` + `await process.wait()` on every error path
- All public functions fully type-annotated (pyright strict mode)
- Pydantic models for data crossing module boundaries; frozen dataclasses for events and internal value objects
- Test structure mirrors source structure; test naming: `test_<unit>_<behavior>`

## UX Design Requirements

UX-DR1: Three operational modes (TUI, Lite, Headless) with auto-detection logic — check $TERM, tmux binary, $TMUX env var; auto-select mode based on environment; support `--mode tui|lite|headless` override flag
UX-DR2: Three-pane tmux layout (Model A ~40% height, Model B ~40% height, Command/Status ~20% / 5-6 lines) for TUI mode; model panes show raw unmodified provider output
UX-DR3: Status bar component with segment format: `[cycle_type step/total] step N/M | provider | cycle R/T | progress_bar | elapsed | state` — responsive truncation right-to-left at 120/100/80/<80 column widths
UX-DR4: Pane header component via tmux `pane-border-format` with format `─── [icon] Provider | model | step description ─── STATE ───` — states: ACTIVE (bold), Waiting for next step ··· (dim+breathing dots), COMPLETE (green), ERROR (red+bold); border color matches escalation state
UX-DR5: Pre-flight summary as Rich table showing all cycles, steps, providers, models, and prompt templates — mandatory with confirmation on first run of a config, auto-dismiss (3s) or skippable on subsequent runs
UX-DR6: Command pane log component — rolling buffer of 2-3 most recent events with timestamps; newest at top; error events in escalation color; never scrolls the command pane
UX-DR7: Completion report component replacing status bar at end-of-run — shows cycle counts, story counts, commit counts, push status, timing, error count; first-ever run gets one milestone line "First automated run complete."
UX-DR8: Resume context screen showing last run timestamp, failure point, failure reason, completed work summary, and numbered options: [1] Re-run failed step, [2] Skip failed step, [3] Restart current cycle, [4] Start from scratch
UX-DR9: Init wizard with conversational tone (not form-like), progressive disclosure, smart defaults accepted with Enter, tmux detection before provider detection, single-provider framed positively, back navigation with `b`/`back`, quit with `q`/Ctrl+C
UX-DR10: Error headline format: `✗ [What happened] — [What to do next]` — every error message ends with guidance; recoverable errors invisible to user unless checking logs; impactful errors always commit state before halting
UX-DR11: Escalation state architecture — single state object (ok/attention/action/complete/idle) drives all rendering across all three modes atomically; one function updates both tmux border color AND Rich status color simultaneously
UX-DR12: Semantic color tokens using ANSI 16 base colors only — brand (blue), ok (green), attention (yellow), action (red), content (terminal default), secondary (dim), emphasis (bold); max 2 colors visible per status bar; no background colors applied; NO_COLOR env var respected
UX-DR13: Keyboard shortcuts — Ctrl+P (pause toggle, no confirmation), Ctrl+S (skip, y/n confirm), Ctrl+A (abort, y/n confirm), Ctrl+R (restart step, y/n confirm), Ctrl+D (detach tmux); shown once per session then hidden
UX-DR14: Three input contexts with consistent patterns — init wizard (conversational question + default in brackets, numbered list selection), command pane mid-run (> prompt, routes to active model stdin when yellow state, /status /log /help special commands), resume choice (numbered options with default)
UX-DR15: Confirmation patterns — destructive actions (skip, abort, restart, config overwrite) always require y/n single-keystroke confirmation defaulting to safe option; non-destructive (pause, detach) act immediately; confirmations timeout after 30s to safe default
UX-DR16: Breathing dot animation (···) at 1-second intervals for idle pane states — decorative only, text label "Waiting" carries the meaning
UX-DR17: Terminal size adaptation — TUI minimum 120x30 (falls back to Lite with warning), Lite minimum 80x24 (truncates segments), pane headers truncate step description first then model name; SIGWINCH handling for mid-run resize
UX-DR18: Accessibility — all escalation states conveyed by both color AND text symbols (✓/⚠/✗), ANSI 16 colors for theme compatibility, graceful degradation (truecolor→256→16→monochrome), screen-reader-friendly structured text, keyboard-only operation throughout
UX-DR19: Command pane special commands: `/status` (show current state summary), `/log` (show last 20 log entries), `/help` (show available commands and shortcuts)
UX-DR20: Lite mode — Rich-formatted single-stream experience when tmux unavailable; model output streams sequentially between Rich-formatted headers; styled status bars, colored escalation, formatted tables; one-time suggestion to install tmux
UX-DR21: Exit code contract for headless/CI mode — 0 (success), 1 (usage error), 2 (config error), 3 (runtime error), 4 (provider error); structured log format: `[ISO-8601] [SEVERITY] [cycle/step] [provider/model] Message`

## FR Coverage Map

FR1: Epic 1 - Config generation through interactive wizard (also Epic 6 for wizard UX)
FR2: Epic 1 - Define multiple providers in config
FR3: Epic 1 - Define cycles with steps, skills, providers, step types, prompts
FR3a: Epic 1 - Define execution order of cycles within a workflow
FR4: Epic 1 - Configure cycle repeat counts
FR5: Epic 1 - Configure pause durations between steps, cycles, workflows
FR6: Epic 1 - Configure git commit and push timing
FR7: Epic 1 - Configure error handling behavior
FR8: Epic 1 - Specify config file location via flag or convention
FR9: Epic 3 - Resolve prompt template variables from orchestrator state
FR10: Epic 2 - Detect installed CLI tools on host machine
FR11: Epic 2 - Query provider CLI for available models
FR12a: Epic 2 - Invoke provider CLI as subprocess with configured prompt
FR12b: Epic 2 - Capture stdout and stderr from running provider subprocess
FR12c: Epic 2 - Detect provider subprocess completion, timeout, or unexpected termination
FR13: Epic 2 - Normalize provider output through adapter interface
FR14: Epic 2 - Operate with single provider (graceful degradation)
FR15: Epic 3 - Execute cycle steps in configured order
FR16: Epic 3 - Distinguish generative steps from validation steps
FR17: Epic 3 - Repeat validation steps for configured repetitions
FR18: Epic 3 - Execute multiple cycles in sequence as complete workflow
FR19: Epic 3 - Pause for configured durations between steps and cycles
FR20: Epic 3 - Atomically persist execution state to JSON state file
FR21: Epic 3 - Record last completed step, provider, and outcome
FR22: Epic 4 - Resume execution from last completed step after interruption
FR23: Epic 4 - Choose on resume: re-run, continue, restart cycle, or start fresh
FR24: Epic 3 - Maintain running log of all state changes across runs
FR25: Epic 3 - Capture per-step logs with timestamps, identifiers, provider tags, severity
FR26: Epic 4 - Consolidate per-step logs into single run log before commit
FR27: Epic 4 - View current orchestrator state without starting a run (status command)
FR28: Epic 3 - Write structured text logs for human reading and grep debugging
FR29: Epic 4 - Commit orchestrator output and logs to git at configurable intervals
FR30: Epic 4 - Push commits to remote at configurable intervals
FR31: Epic 4 - Emergency commit and push on impactful error before halting
FR32: Epic 5 - Display three-pane tmux layout (Model A, Model B, Command/Status)
FR32a: Epic 5 - TUI output pane switches to display currently active model
FR33: Epic 5 - Display status bar with phase, step, provider, cycle progress
FR34: Epic 5 - Pause execution after current step completes
FR35: Epic 5 - Skip current step
FR36: Epic 5 - Abort execution (commit + push + halt)
FR37: Epic 5 - Restart current step
FR38: Epic 1 - Validate config for schema, provider availability, model existence
FR39: Epic 3 - Detect and classify errors as recoverable or impactful
FR40: Epic 3 - Log recoverable errors and continue execution
FR41: Epic 4 - Halt on impactful errors after committing state and pushing
FR42: Epic 6 - Detect installed CLI providers and present for selection
FR43: Epic 6 - Query selected providers for models and present for selection
FR44: Epic 6 - Offer sensible default cycle configurations
FR45: Epic 6 - Generate valid bmad-orch.yaml from user selections
FR46: Epic 1 - Display playbook summary on start with proceed/modify prompt
FR47: Epic 1 - Dry run showing execution plan without invoking providers
FR48: Epic 4 - State file as human-readable audit trail
FR49: Epic 5 - Send input to active model subprocess via command pane
