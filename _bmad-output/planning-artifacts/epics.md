---
stepsCompleted: [step-01-validate-prerequisites, step-02-design-epics]
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
---

# BMAD Orchestrator - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for BMAD Orchestrator, decomposing the requirements from the PRD, UX Design, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

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

### NonFunctional Requirements

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

### Additional Requirements

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

### UX Design Requirements

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

### FR Coverage Map

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

## Epic List

### Epic 1: Project Foundation & Configuration
User can install the tool and define, validate, and preview orchestrator configurations — seeing exactly what will execute before spending API credits.
**FRs covered:** FR1-FR8, FR38, FR46, FR47

### Epic 2: Provider Detection & Execution
The orchestrator detects installed AI CLIs (Claude, Gemini), queries their available models, and executes prompts with full streaming output capture via PTY.
**FRs covered:** FR10-FR14

### Epic 3: Core Cycle Engine
User runs the orchestrator and it executes multi-step, multi-cycle workflows — distinguishing generative from validation steps, repeating cycles as configured, pausing between steps, tracking state atomically, logging comprehensively, and handling errors as they occur.
**FRs covered:** FR9, FR15-FR21, FR24-FR25, FR28, FR39, FR40

### Epic 4: Reliable Unattended Execution
User runs `bmad-orch start --headless` and returns to completed, committed, auditable work — with git integration, resume capability, resource monitoring, emergency error handling, structured headless output, and CI/CD exit code contract.
**FRs covered:** FR22-FR23, FR26-FR27, FR29-FR31, FR41, FR48
**NFRs addressed:** NFR1-NFR15

### Epic 5: Interactive TUI *(parallel with Epics 6 & 7)*
User observes and controls live execution in a three-pane tmux TUI — watching model output stream in real-time, glancing at the status bar, using keyboard shortcuts, and sending input to models via the command pane.
**FRs covered:** FR32-FR37, FR32a, FR33, FR49

### Epic 6: Init Wizard & Onboarding *(parallel with Epics 3, 4, 5 & 7)*
New user goes from zero to a working configuration in under 5 minutes through a guided, conversational setup experience with smart defaults and progressive disclosure.
**FRs covered:** FR42-FR45

### Epic 7: Lite Mode Experience *(parallel with Epics 5 & 6)*
Users without tmux get a styled single-stream experience with Rich-formatted status, colored escalation, and formatted tables — the tool adapts automatically to the environment.
**FRs covered:** Cross-cutting UX (UX-DR1, UX-DR20)

## Parallel Execution Schedule

```
Phase 1:  Epic 1 (Foundation & Config)
Phase 2:  Epic 2 (Providers)
Phase 3:  Epic 3 (Engine)          ║  Epic 6 (Init Wizard)
Phase 4:  Epic 4 (Unattended)      ║  Epic 6 (cont. if needed)
Phase 5:  Epic 5 (TUI)  ║  Epic 7 (Lite Mode)  ║  Epic 6 (cont. if needed)
```

**Dependency Rules:**
- Epics 1 → 2 → 3 → 4: strictly sequential (each builds on the previous)
- Epic 6 starts after Epic 2 (needs config schema + provider detection); independent of Epics 3-5 and 7
- Epics 5 and 7 start after Epic 4 (need the complete engine to render); independent of each other and Epic 6
- All three presentation epics (5, 6, 7) touch separate code modules and can build simultaneously without interference

## Epic 1: Project Foundation & Configuration

User can install the tool and define, validate, and preview orchestrator configurations — seeing exactly what will execute before spending API credits.

### Story 1.1: Project Scaffolding & Tooling Setup

As a **developer**,
I want a properly structured Python project with all dependencies, linting, type checking, and CI configured,
So that I have a solid, consistent foundation to build every subsequent feature on.

**Acceptance Criteria:**

**Given** a new project directory
**When** I run `uv init --name bmad-orch --package`
**Then** the project has `src/bmad_orch/` layout with `__init__.py` and `py.typed`
**And** `.python-version` exists, pins Python 3.13, and is tracked in version control (must NOT be gitignored)
**And** `uv.lock` exists and is tracked in version control

**Given** the project is initialized
**When** I run `uv add "typer[all]" rich pydantic pydantic-settings pyyaml structlog psutil libtmux` and `uv add --dev pytest pytest-cov ruff pyright pre-commit import-linter`
**Then** all core and development dependencies are added to `pyproject.toml`
**And** note: `rich` and `libtmux` are declared as dependencies but per architecture rules must only be imported lazily at function-level in rendering modules — never at module-level in core engine code. This is enforced by `test_import_isolation.py` (see Story 1.2+).

**Given** the dependencies are installed
**When** I configure `pyproject.toml` with `[tool.ruff]`, `[tool.pyright]` (strict), `[tool.pytest.ini_options]`, and `[tool.importlinter]` sections
**And** I create `src/bmad_orch/types.py`, `src/bmad_orch/errors.py`, and `src/bmad_orch/cli.py` with initial type-safe boilerplate
**And** I run `uv run bmad-orch --help`
**Then** Typer displays the CLI help with `start`, `resume`, `status`, `validate` subcommands and `--init` option listed
**And** when `--init` is passed, the callback must exit after the wizard completes and must NOT fall through to execute a subcommand

**Given** the project is configured
**When** I run `uv run ruff check . && uv run pyright`
**Then** both pass with zero errors under strict configuration
**And** pyright recognizes the package as typed via the `py.typed` PEP 561 marker

**Given** the project is configured
**When** I create `tests/conftest.py` and smoke tests in `tests/test_smoke.py`
**And** I run `uv run pytest`
**Then** the test suite runs with coverage reporting enabled for `src/bmad_orch/`
**And** smoke tests specifically verify:
    - `bmad_orch` is importable
    - `OutputChunk`, `ErrorSeverity`, and `StepType` can be instantiated from `types.py`
    - `BmadOrchError` and its subclasses can be instantiated with appropriate `severity` from `errors.py`
    - `bmad-orch --help` exits with status 0 and lists all 4 subcommands (`start`, `resume`, `status`, `validate`)

**Given** the project is configured
**When** I create `[tool.importlinter]` configuration in `pyproject.toml` enforcing the layer hierarchy: `rendering` -> `providers` -> `engine` -> `state` -> `config` -> `types`
**And** I create stub `__init__.py` files for each layer package (`rendering/`, `providers/`, `engine/`, `state/`, `config/`) so import-linter can resolve them
**And** I run `uv run lint-imports`
**Then** the check passes with zero violations against real (non-vacuous) module resolution

**Given** the project is initialized
**When** I run `pre-commit install` and then `git commit`
**Then** pre-commit hooks execute Ruff and pyright automatically
**And** `.pre-commit-config.yaml` exists with pinned hook versions

**Given** the project contains a `.github/workflows/` directory
**When** I inspect `ci.yml`
**Then** it contains jobs for `ruff`, `pyright`, `pytest`, and `import-linter` triggered on PRs to `main`
**And** `release.yml` contains a job to publish to PyPI using `pypa/gh-action-pypi-publish` on tagged releases

**Given** the project is initialized
**When** I create a `.gitignore`
**Then** it excludes `__pycache__/`, `.venv/`, `.ruff_cache/`, `dist/`, `*.egg-info/`, `.pyright_cache/`, `bmad-orch-state.json`, `bmad-orch-state.tmp`, and `coverage.xml`
**And** it does NOT exclude `.python-version` (which must be tracked in version control)

**Given** the project contains `src/bmad_orch/__init__.py`
**When** I inspect its contents
**Then** it exports a `__version__` string and defines `__all__`

**Given** the project contains `types.py` and `errors.py`
**When** I inspect their contents
**Then** `types.py` defines `OutputChunk` (frozen dataclass), `EscalationState` (enum: ok/attention/action/complete/idle), `ProviderName` (NewType over str), `StepOutcome` (enum: `PASSED`, `FAILED`, `SKIPPED`, `ERROR`), `ErrorSeverity` (enum: `BLOCKING`, `RECOVERABLE`, `IMPACTFUL`), and `StepType` (enum: generative/validation) with zero internal dependencies
**And** `errors.py` defines the `BmadOrchError` hierarchy with `ConfigError` (BLOCKING), `ProviderError` with subclasses `ProviderNotFoundError` (BLOCKING) / `ProviderTimeoutError` (RECOVERABLE) / `ProviderCrashError` (IMPACTFUL), `StateError` (IMPACTFUL), `GitError` (IMPACTFUL), `ResourceError` (IMPACTFUL), `WizardError` (BLOCKING) — each carrying its assigned `ErrorSeverity`
**And** `severity` must be an instance attribute set in `__init__`, not a mutable class variable — subclasses override via `__init__` default, not class-level assignment
**And** every exception class references `ErrorSeverity` from `types.py` through a clean, non-circular import

### Story 1.2: Configuration Schema & Validation Models

As a **user**,
I want a well-defined configuration schema that validates my `bmad-orch.yaml` file,
So that I know my config is correct before I run any cycles.

**Acceptance Criteria:**

**Given** a valid `bmad-orch.yaml` with providers, cycles, steps, git, pauses, and error_handling sections
**When** the config is loaded into Pydantic models
**Then** `OrchestratorConfig` is created with typed fields for `ProviderConfig`, `CycleConfig`, `StepConfig`, `GitConfig`, `PauseConfig`, and `ErrorConfig`

**Given** a `bmad-orch.yaml` with a missing required field (e.g., no `providers` section)
**When** the config is parsed
**Then** a `ConfigError` is raised with a clear message identifying the missing field

**Given** a `bmad-orch.yaml` with an invalid value (e.g., `commit_at: "never"` instead of `step|cycle|end`)
**When** the config is parsed
**Then** a `ConfigError` is raised identifying the invalid value and listing valid options

**Given** a `StepConfig` entry
**When** it is validated
**Then** it contains `skill` (str), `provider` (int reference), `type` (generative|validation), and `prompt` (str template)

**Given** a `CycleConfig` entry
**When** it is validated
**Then** it contains `steps` (ordered list of `StepConfig`), `repeat` (int >= 1), and optional pause overrides

### Story 1.3: Config File Loading & Discovery

As a **user**,
I want to load my config from a file using either a flag or convention,
So that I can validate my setup before running cycles.

**Acceptance Criteria:**

**Given** a `bmad-orch.yaml` exists in the current working directory
**When** I run `bmad-orch validate` with no flags
**Then** the system discovers and loads `bmad-orch.yaml` from the cwd

**Given** a config file exists at `/path/to/my-config.yaml`
**When** I run `bmad-orch validate --config /path/to/my-config.yaml`
**Then** the system loads the config from the explicit path (overriding cwd discovery)

**Given** no `bmad-orch.yaml` exists in cwd and no `--config` flag is provided
**When** I run `bmad-orch validate`
**Then** the system exits with code 2 and a clear error: `✗ No config found — create bmad-orch.yaml or use --config <path>`

**Given** a valid config file
**When** I run `bmad-orch validate`
**Then** the system reports schema correctness and exits with code 0
**And** the output confirms provider names and model names from the config

**Given** a config file with a YAML syntax error
**When** I run `bmad-orch validate`
**Then** the system exits with code 2 and a clear error identifying the line and nature of the YAML parse failure

### Story 1.4: Prompt Template Variable Registry

As a **user**,
I want prompt templates in my config to support dynamic variables,
So that each step receives context-aware prompts with the correct story IDs, file paths, and other run-time values.

**Acceptance Criteria:**

**Given** a step prompt containing `{next_story_id}`
**When** the template variable registry resolves it
**Then** the variable is replaced with the correct story identifier from orchestrator state

**Given** a step prompt containing `{current_story_file}`
**When** the template variable registry resolves it
**Then** the variable is replaced with the file path of the current story artifact

**Given** a step prompt containing an unknown variable `{nonexistent_var}`
**When** the template variable registry attempts resolution
**Then** the step halts with a `ConfigError` identifying the unresolvable variable: `✗ Unresolvable template variable '{nonexistent_var}' in step 'create-story' — check prompt template in config`

**Given** a step prompt containing multiple variables `{next_story_id}` and `{current_story_file}`
**When** the template variable registry resolves them
**Then** all variables are replaced in a single pass with no partial resolution

**Given** a step prompt with no template variables (plain text)
**When** the template variable registry processes it
**Then** the prompt is passed through unchanged

### Story 1.5: Playbook Summary & Dry Run

As a **user**,
I want to preview exactly what the orchestrator will execute before it starts,
So that I can catch config mistakes before spending API credits.

**Acceptance Criteria:**

**Given** a valid config file
**When** I run `bmad-orch start --dry-run`
**Then** the system displays the complete execution plan showing all cycles, their steps, assigned providers/models, step types (generative/validation), repeat counts, and prompt templates
**And** no providers are invoked
**And** the system exits with code 0

**Given** a valid config and first run with this config
**When** I run `bmad-orch start`
**Then** a pre-flight summary table is displayed showing providers, cycles, steps, and prompts
**And** the system waits for user confirmation (Enter to proceed) before execution begins

**Given** a valid config and a previous successful run exists with this config
**When** I run `bmad-orch start`
**Then** the pre-flight summary displays briefly (auto-dismiss after 3 seconds) or is skippable

**Given** the pre-flight summary is displayed on first run
**When** the user chooses to modify
**Then** the system opens the config file in `$EDITOR`, and re-validates on save before re-displaying the summary

**Given** a config file with an invalid provider reference
**When** I run `bmad-orch start --dry-run`
**Then** the system reports the config error with exit code 2 and does not display the execution plan

## Epic 2: Provider Detection & Execution

The orchestrator detects installed AI CLIs (Claude, Gemini), queries their available models, and executes prompts with full streaming output capture via PTY.

### Story 2.1: Provider Adapter Interface & Detection Framework

As a **developer**,
I want a provider adapter interface with CLI detection capabilities,
So that new providers can be added by implementing a single contract without changing core engine code.

**Acceptance Criteria:**

**Given** the `providers/base.py` module
**When** I inspect the `ProviderAdapter` ABC
**Then** it defines `async def execute(prompt: str) -> AsyncIterator[OutputChunk]`, `def detect() -> bool`, and `def list_models() -> list[str]`

**Given** the provider detection framework
**When** I call `detect()` on an adapter
**Then** it checks whether the provider's CLI binary is installed and executable on the host machine

**Given** a provider CLI is installed
**When** I call `list_models()` on its adapter
**Then** it queries the CLI for available models and returns them as a list of strings

**Given** the adapter registry in `providers/__init__.py`
**When** I call `get_adapter(name)` with a valid provider name
**Then** it returns the correct adapter instance

**Given** the adapter registry
**When** I call `get_adapter(name)` with an unknown provider name
**Then** it raises `ProviderNotFoundError` with a clear message listing available providers

**Given** any provider adapter's `execute()` method
**When** the subprocess produces output
**Then** output is captured via PTY and yielded as `OutputChunk` objects preserving ANSI formatting

### Story 2.2: Claude CLI Adapter

As a **user**,
I want the orchestrator to invoke Claude CLI with my configured prompts,
So that Claude can execute generative and validation steps in my workflows.

**Acceptance Criteria:**

**Given** the Claude CLI is installed on the host
**When** `ClaudeAdapter.detect()` is called
**Then** it returns `True`

**Given** the Claude CLI is not installed
**When** `ClaudeAdapter.detect()` is called
**Then** it returns `False`

**Given** a detected Claude CLI
**When** `ClaudeAdapter.list_models()` is called
**Then** it returns the list of available models from the Claude CLI

**Given** a valid prompt and model configuration
**When** `ClaudeAdapter.execute(prompt)` is called
**Then** the Claude CLI is invoked as an async subprocess via PTY with the configured model and prompt
**And** stdout is streamed as `OutputChunk` objects via `AsyncIterator`

**Given** a running Claude subprocess
**When** it completes successfully
**Then** the adapter detects completion and yields a final `OutputChunk` with completion status

**Given** a running Claude subprocess
**When** it times out or terminates unexpectedly (crash, OOM, signal)
**Then** the adapter detects the failure, calls `process.kill()` + `await process.wait()`, and raises `ProviderCrashError` or `ProviderTimeoutError` with exit code context

**Given** a running Claude subprocess
**When** the CLI output format is unrecognizable
**Then** the adapter parses defensively and raises an explicit error rather than silently producing garbage output

### Story 2.3: Gemini CLI Adapter

As a **user**,
I want the orchestrator to invoke Gemini CLI with my configured prompts,
So that Gemini can execute validation steps and provide adversarial review in my workflows.

**Acceptance Criteria:**

**Given** the Gemini CLI is installed on the host
**When** `GeminiAdapter.detect()` is called
**Then** it returns `True`

**Given** the Gemini CLI is not installed
**When** `GeminiAdapter.detect()` is called
**Then** it returns `False`

**Given** a detected Gemini CLI
**When** `GeminiAdapter.list_models()` is called
**Then** it returns the list of available models from the Gemini CLI

**Given** a valid prompt and model configuration
**When** `GeminiAdapter.execute(prompt)` is called
**Then** the Gemini CLI is invoked as an async subprocess via PTY with the configured model and prompt
**And** stdout is streamed as `OutputChunk` objects via `AsyncIterator`

**Given** a running Gemini subprocess
**When** it completes successfully
**Then** the adapter detects completion and yields a final `OutputChunk` with completion status

**Given** a running Gemini subprocess
**When** it times out or terminates unexpectedly
**Then** the adapter detects the failure, calls `process.kill()` + `await process.wait()`, and raises the appropriate `ProviderError` subclass

**Given** a running Gemini subprocess
**When** the CLI output format is unrecognizable
**Then** the adapter parses defensively and raises an explicit error

### Story 2.4: Single-Provider Graceful Mode

As a **user with only one AI CLI installed**,
I want the orchestrator to operate fully with a single provider,
So that I can run automated cycles without needing to install a second CLI.

**Acceptance Criteria:**

**Given** a config file that references two providers but only one is detected on the host
**When** the orchestrator validates the config
**Then** it reports which providers are missing and exits with a clear error suggesting the user update their config or install the missing CLI

**Given** a config file that references only one provider for all steps
**When** the orchestrator validates the config
**Then** validation passes — single-provider configs are fully valid

**Given** a single-provider config
**When** cycles execute
**Then** all steps run against the single provider with no errors or warnings about missing adversarial validation

**Given** the provider detection framework
**When** no CLI providers are detected at all
**Then** the system exits with a clear error message and helpful install links for supported CLIs

## Epic 3: Core Cycle Engine

User runs the orchestrator and it executes multi-step, multi-cycle workflows — distinguishing generative from validation steps, repeating cycles as configured, pausing between steps, tracking state atomically, logging comprehensively, and handling errors as they occur.

### Story 3.1: Event Emitter & Event Types

As a **developer**,
I want a typed event system that decouples the engine from all presentation layers,
So that renderers can subscribe to engine events without the engine knowing or caring which renderers exist.

**Acceptance Criteria:**

**Given** the `engine/events.py` module
**When** I inspect the event types
**Then** it defines frozen dataclasses for `StepStarted`, `StepCompleted`, `CycleStarted`, `CycleCompleted`, `EscalationChanged`, `LogEntry`, `ProviderOutput`, `RunCompleted`, `ErrorOccurred`, and `ResourceThresholdBreached`

**Given** any event dataclass
**When** I attempt to mutate a field after creation
**Then** it raises `FrozenInstanceError` — all events are immutable

**Given** the `EventEmitter` in `engine/emitter.py`
**When** I call `subscribe(event_type, callback)`
**Then** the callback is registered for that event type

**Given** an emitter with subscribers registered
**When** I call `emit(event)`
**Then** all subscribers for that event type are invoked synchronously with the event
**And** events are delivered in subscription order

**Given** a subscriber that raises an exception
**When** an event is emitted
**Then** the emitter catches the exception, logs it, and continues to invoke remaining subscribers — a broken renderer never crashes the engine

**Given** the emitter
**When** I inspect its imports
**Then** it accepts `Callable` subscribers, never imports from `rendering/`, and has no knowledge of any specific renderer

### Story 3.2: State Manager & Atomic Persistence

As a **user**,
I want execution state persisted atomically after every step,
So that a crash at any point leaves a valid, recoverable state file and I never lose completed work.

**Acceptance Criteria:**

**Given** the `state/schema.py` module
**When** I inspect the state models
**Then** it defines Pydantic models for `RunState`, `StepRecord`, `CycleRecord`, and `ErrorRecord` — all immutable with `with_*` update methods

**Given** a step completes successfully
**When** the state manager saves state
**Then** it writes to `.bmad-orch-state.tmp` in the same directory as the state file, then performs atomic `os.rename()` to `bmad-orch-state.json`

**Given** a crash occurs during a state write
**When** the orchestrator restarts
**Then** the previous valid state file remains intact (the temp file is orphaned, not the real state file)

**Given** a completed step
**When** state is recorded
**Then** the `StepRecord` includes which step was completed, which provider executed it, the outcome, and a timestamp

**Given** multiple runs over time
**When** I inspect the state file
**Then** it maintains a running history of all state changes across runs (append to run history, not overwrite)

**Given** the state manager
**When** I call `load()` with no existing state file
**Then** it returns a fresh `RunState` with empty history

**Given** the temp file location
**When** the state manager creates it
**Then** the temp file is always in the same directory as the state file (same-filesystem requirement for atomic rename)

### Story 3.3: Structured Logging Subsystem

As a **user**,
I want comprehensive, structured logs for every step,
So that I can diagnose any failure without reproducing it.

**Acceptance Criteria:**

**Given** the `logging.py` module
**When** `configure_logging(mode)` is called with human mode (TUI/Lite)
**Then** structlog is configured with a processor chain producing `[timestamp] [severity_icon] [context] message` colored text output

**Given** the `logging.py` module
**When** `configure_logging(mode)` is called with machine mode (Headless)
**Then** structlog is configured with a processor chain producing `[ISO-8601 timestamp] [SEVERITY] [context_dict] message` structured plain text

**Given** an async step execution
**When** log calls are made within the step
**Then** `structlog.contextvars` automatically includes the current step identifier, provider name, and cycle context without explicit passing

**Given** two concurrent async tasks (e.g., resource monitor and step execution)
**When** both produce log output
**Then** context does not leak between tasks — resource monitor logs do not inherit step/provider context

**Given** a step execution
**When** per-step logs are captured
**Then** each log entry includes timestamp, step identifier, provider tag, and severity level

**Given** structured log output
**When** I grep the log files
**Then** the format is grep-friendly with consistent field positions suitable for both human reading and automated parsing

### Story 3.4: Cycle Execution Engine

As a **user**,
I want the orchestrator to execute my configured cycles step by step,
So that my multi-step, multi-model workflows run automatically in the correct order.

**Acceptance Criteria:**

**Given** a cycle with 4 ordered steps
**When** the cycle engine executes
**Then** steps run in configured order (step 1, then 2, then 3, then 4)

**Given** a cycle with generative and validation step types
**When** the cycle runs for the first time
**Then** both generative and validation steps execute

**Given** a cycle with `repeat: 2`
**When** the second repetition runs
**Then** only validation steps execute — generative steps run only on the first cycle

**Given** a cycle with `repeat: 3`
**When** all repetitions complete
**Then** the generative step ran once and validation steps ran 3 times total

**Given** configured pause durations between steps
**When** a step completes
**Then** the engine pauses for the configured duration before starting the next step

**Given** configured pause durations between cycles
**When** a cycle repetition completes
**Then** the engine pauses for the configured duration before starting the next repetition

**Given** the cycle engine executing a step
**When** the step starts and completes
**Then** `StepStarted` and `StepCompleted` events are emitted with step details, provider, and timing

**Given** the cycle engine executing a cycle
**When** the cycle starts and completes
**Then** `CycleStarted` and `CycleCompleted` events are emitted

**Given** the cycle engine
**When** a step completes
**Then** state is persisted atomically before the next step begins

### Story 3.5: Error Detection & Classification

As a **user**,
I want errors automatically classified and handled appropriately,
So that transient issues are retried silently while serious failures are surfaced clearly.

**Acceptance Criteria:**

**Given** a provider returns a rate limit error (HTTP 429 or equivalent CLI error)
**When** the error classification system evaluates it
**Then** it is classified as `RECOVERABLE` with severity `ProviderTimeoutError`

**Given** a recoverable error during step execution
**When** the error handling logic processes it
**Then** the error is logged with full context and execution continues to the next retry or step
**And** the user sees nothing unless they inspect logs

**Given** a provider subprocess crash (unexpected termination, OOM kill)
**When** the error classification system evaluates it
**Then** it is classified as `IMPACTFUL` with severity `ProviderCrashError`

**Given** an impactful error
**When** the error handling logic processes it
**Then** an `ErrorOccurred` event is emitted with the error details, classification, and suggested next action

**Given** an error with structured context
**When** it is logged
**Then** the log entry follows the format `✗ [What happened] — [What to do next]` and includes the error classification, provider name, step identifier, and timestamp

**Given** the error classification system
**When** I inspect the implementation
**Then** the engine checks `error.severity` (the `ErrorSeverity` enum), not `isinstance()` checks against exception subclasses

### Story 3.6: Multi-Cycle Workflow Orchestration

As a **user**,
I want to run a complete workflow (story → atdd → dev) as a single command,
So that multiple cycle types execute in sequence without manual intervention.

**Acceptance Criteria:**

**Given** a config with three cycles defined (story, atdd, dev) in a specific order
**When** the runner executes the workflow
**Then** cycles execute in the configured order: story cycle completes fully, then atdd cycle, then dev cycle

**Given** configured pause durations between workflows
**When** one cycle type completes and the next begins
**Then** the engine pauses for the configured between-workflows duration

**Given** the runner module in `engine/runner.py`
**When** it orchestrates a workflow
**Then** it wires together the cycle engine, provider adapters, state manager, event emitter, and logging subsystem

**Given** a multi-cycle workflow executing
**When** each cycle completes
**Then** the state file reflects the completed cycle and the next cycle to execute

**Given** template variables in step prompts
**When** the runner prepares a step for execution
**Then** it resolves all template variables from current orchestrator state (e.g., `{current_story_file}` reflects the output from the story cycle)

**Given** a `RunCompleted` event
**When** the entire workflow finishes
**Then** the event includes total step count, total cycle count, elapsed time, and error count

## Epic 4: Reliable Unattended Execution

User runs `bmad-orch start --headless` and returns to completed, committed, auditable work — with git integration, resume capability, resource monitoring, emergency error handling, structured headless output, and CI/CD exit code contract.

### Story 4.1: Git Integration & Configurable Commits

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

### Story 4.2: Emergency Error Flow & Impactful Error Handling

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

### Story 4.3: Resource Monitoring

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

### Story 4.4: Resume Flow & Recovery

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

### Story 4.5: Log Consolidation & Status Command

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

### Story 4.6: Headless Renderer & Exit Code Contract

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

## Epic 5: Interactive TUI

User observes and controls live execution in a three-pane tmux TUI — watching model output stream in real-time, glancing at the status bar, using keyboard shortcuts, and sending input to models via the command pane.

### Story 5.1: Three-Pane tmux Layout & Pane Lifecycle

As a **user**,
I want the orchestrator to launch a three-pane tmux layout automatically,
So that I can observe model output and system status in an organized terminal view.

**Acceptance Criteria:**

**Given** a user runs `bmad-orch start` with tmux available
**When** the TUI renderer initializes
**Then** libtmux is imported lazily (function-level, not module-level) and a tmux session is created with three panes: Model A (~40% height), Model B (~40% height), Command/Status (~20% / 5-6 lines)

**Given** the three-pane layout is created
**When** I inspect the pane proportions
**Then** model panes absorb the majority of vertical space and the command pane is fixed at a minimum of 6 rows

**Given** the orchestrator run completes or is aborted
**When** the TUI shuts down
**Then** tmux panes are cleaned up properly with no orphaned sessions or processes

**Given** a terminal with dimensions below 120x30
**When** the TUI renderer attempts to initialize
**Then** it falls back to Lite mode with a warning: `Terminal too small for TUI (need 120x30) — running in Lite mode`

**Given** a terminal resize (SIGWINCH) during a run
**When** tmux receives the signal
**Then** tmux re-tiles panes automatically with no rendering corruption

**Given** the user detaches from the tmux session (Ctrl+D)
**When** they later run `tmux attach`
**Then** the session is still running with current state visible — the orchestrator continued executing during detachment

**Given** the TUI renderer module
**When** I inspect its imports
**Then** libtmux is only imported inside functions, never at module level

### Story 5.2: Pane Headers & Escalation Colors

As a **user**,
I want pane borders to show me which model is in each pane and its current state at a glance,
So that I can assess the system's status from border color and header text alone.

**Acceptance Criteria:**

**Given** the TUI is running
**When** a model pane is active
**Then** its pane header (via tmux `pane-border-format`) displays: `─── 🤖 Provider | model-name | step description ─── ACTIVE ───` with ACTIVE in bold

**Given** a model pane that is idle
**When** it is waiting for its next step
**Then** its header displays: `─── 🤖 Provider | model-name ─── Waiting for next step ··· ───` with breathing dot animation (···) cycling at 1-second intervals in dim text

**Given** a model pane that completed its step
**When** the step finishes successfully
**Then** its header state changes to `COMPLETE` in green

**Given** a model pane where an error occurred
**When** the step fails
**Then** its header state changes to `ERROR` in red + bold

**Given** the escalation state changes (e.g., ok → attention)
**When** the state transition occurs
**Then** both the pane border color AND the header state label update atomically — driven by the single escalation state object

**Given** the escalation color system
**When** colors are applied to pane borders
**Then** they use ANSI 16 base colors only: green (ok), yellow (attention), red (action) — with text symbols (✓/⚠/✗) supplementing color so it is never the sole signal

**Given** a narrow terminal width
**When** pane headers need to truncate
**Then** they truncate the step description first, then the model name, keeping provider name and state label as the last items removed

### Story 5.3: Status Bar & Command Pane Log

As a **user**,
I want a glanceable status bar and recent event log in the command pane,
So that I know exactly what's happening in one-second scan without reading model output.

**Acceptance Criteria:**

**Given** the command pane during execution
**When** I look at line 2 (between Rich horizontal rules)
**Then** the status bar displays: `[story 2/5] step 3/4 | claude | cycle 1/2 | ▓▓▓░░ 60% | 12m | ✓ ok` with provider name in brand color (blue) + bold and state in escalation color

**Given** a terminal width of 120+ columns
**When** the status bar renders
**Then** all segments are visible: cycle id, step, provider, repeat, progress bar, time, state

**Given** a terminal width of 100 columns
**When** the status bar renders
**Then** the progress bar simplifies to percentage only (no bar characters)

**Given** a terminal width of 80 columns
**When** the status bar renders
**Then** only cycle id, step, provider, and state are shown

**Given** a terminal width below 80 columns
**When** the status bar renders
**Then** only step progress and state are shown

**Given** the command pane log area (lines 4-5)
**When** events occur
**Then** a rolling buffer shows the 2-3 most recent events with dim timestamps: `[14:23:01] Step 3 started: create story via Claude`

**Given** the rolling log buffer
**When** a new event arrives
**Then** newest appears at top, oldest drops off — the command pane never scrolls

**Given** an error event in the log
**When** it is displayed
**Then** it renders in escalation color (red + bold for impactful, yellow for attention)

**Given** the workflow completes
**When** the completion report renders
**Then** it replaces the status bar with: `✓ Complete | N stories | M commits | Tm | E errors` in green
**And** the first-ever completed run adds one milestone line: `First automated run complete.`

### Story 5.4: Provider Output Streaming to Panes

As a **user**,
I want to watch AI model output stream in real-time in the TUI panes,
So that I can see exactly what each model is producing, just like watching a CLI session.

**Acceptance Criteria:**

**Given** the TUI renderer
**When** it receives `ProviderOutput` events from the engine
**Then** it writes the output chunks to the active model's tmux pane in real-time

**Given** model output
**When** it is written to a pane
**Then** it is completely unmodified — raw output exactly as the CLI produces it, including any ANSI formatting from the provider

**Given** the cycle progresses from a Claude step to a Gemini step
**When** the active model switches
**Then** the Model A pane retains its output (persistent context) and the Model B pane begins streaming the new model's output
**And** pane headers update to reflect which pane is ACTIVE and which shows previous step output

**Given** visual differences between Claude and Gemini CLI output
**When** both are visible in their panes
**Then** the differences are preserved — the orchestrator does not normalize, reformat, or filter provider output

**Given** the TUI renderer subscribes to events
**When** I inspect the wiring
**Then** the rendering module's `__init__` wires renderer methods as subscribers to the emitter — no engine-to-rendering import exists

### Story 5.5: Keyboard Shortcuts & Execution Control

As a **user**,
I want keyboard shortcuts to control execution without leaving the terminal,
So that I can pause, skip, abort, or restart steps when I need to intervene.

**Acceptance Criteria:**

**Given** the TUI is running
**When** the user presses Ctrl+P
**Then** execution pauses after the current step completes, the status bar shows `⏸ paused`, and pressing Ctrl+P again resumes — no confirmation required (non-destructive toggle)

**Given** the TUI is running
**When** the user presses Ctrl+S
**Then** a confirmation prompt appears: `Skip current step? (y/n)` — single keystroke, no Enter required, defaults to `n` (safe option)
**And** if confirmed, the step is skipped with a log entry and execution continues to the next step

**Given** the TUI is running
**When** the user presses Ctrl+A
**Then** a confirmation prompt appears: `Abort run? State will be committed. (y/n)` — defaults to `n`
**And** if confirmed, the emergency flow triggers: commit state + push + halt

**Given** the TUI is running
**When** the user presses Ctrl+R
**Then** a confirmation prompt appears: `Restart current step? (y/n)` — defaults to `n`
**And** if confirmed, the current step restarts from the beginning with the same provider

**Given** the TUI is running
**When** the user presses Ctrl+D
**Then** the tmux session detaches immediately (standard tmux behavior) — the orchestrator continues running in the background

**Given** a destructive confirmation prompt is displayed
**When** the user does not respond within 30 seconds
**Then** the confirmation times out to the safe default (no action taken)

**Given** the TUI launches for the first time in a session
**When** the command pane initializes
**Then** a shortcut hint line is displayed: `Ctrl+P pause | Ctrl+S skip | Ctrl+A abort | Ctrl+R restart`
**And** the hint is shown once then hidden to save space

**Given** the init wizard or resume context screen is active
**When** the user presses execution control shortcuts
**Then** they are ignored — shortcuts are only active during execution

### Story 5.6: Command Pane Input & Model Interaction

As a **user**,
I want to send input to a model when it asks me a question,
So that I can respond to clarifying questions without stopping the run.

**Acceptance Criteria:**

**Given** the command pane during execution
**When** no model is awaiting input
**Then** the command pane shows a `> ` prompt at the bottom

**Given** a model asks a clarifying question (escalation state → attention/yellow)
**When** the user types a response in the command pane and presses Enter
**Then** the input is routed to the active model's subprocess stdin
**And** the pane border returns to green and the status bar returns to normal

**Given** the escalation state is green (no model awaiting input)
**When** the user types and presses Enter
**Then** the command pane shows `No active prompt. Input ignored.` in dim text

**Given** the user types a line starting with `/status`
**When** they press Enter
**Then** the command pane displays a current state summary (cycle, step, provider, elapsed time) — the input is not routed to any model

**Given** the user types `/log`
**When** they press Enter
**Then** the command pane displays the last 20 log entries

**Given** the user types `/help`
**When** they press Enter
**Then** the command pane displays available commands (`/status`, `/log`, `/help`) and keyboard shortcuts

**Given** a model needs multi-line input
**When** the input requirement is detected
**Then** the orchestrator opens `$EDITOR` in a temporary file and pipes the saved result to the model's subprocess stdin

## Epic 6: Init Wizard & Onboarding

New user goes from zero to a working configuration in under 5 minutes through a guided, conversational setup experience with smart defaults and progressive disclosure.

### Story 6.1: CLI Detection & tmux Discovery

As a **new user**,
I want the init wizard to detect what tools I have installed and guide me accordingly,
So that I know exactly what capabilities are available before configuring anything.

**Acceptance Criteria:**

**Given** a user runs `bmad-orch --init`
**When** the wizard starts
**Then** it first checks for tmux availability before any provider detection

**Given** tmux is not installed on macOS
**When** the wizard detects its absence
**Then** it displays: `tmux not found. Install with: brew install tmux`
**And** asks if the user wants to install now or continue without it

**Given** tmux is not installed on Linux
**When** the wizard detects its absence
**Then** it displays: `tmux not found. Install with: sudo apt install tmux` (or `sudo dnf install tmux`)

**Given** the user declines to install tmux
**When** the wizard continues
**Then** it displays: `No problem — Lite mode available. Install tmux later for the full TUI experience.` and proceeds to provider detection

**Given** the wizard proceeds to provider detection
**When** it scans for installed CLI tools
**Then** it checks for Claude CLI and Gemini CLI (and any other supported providers) and reports what was found

**Given** both Claude and Gemini CLIs are detected
**When** the results are presented
**Then** the wizard lists both with their detected versions conversationally: `Found Claude CLI and Gemini CLI — you're set for adversarial validation.`

**Given** only one CLI is detected (e.g., Claude only)
**When** the results are presented
**Then** the wizard frames it positively: `Found Claude CLI — that's all you need to get started. Add adversarial validation later with --init again.`

**Given** no CLI providers are detected
**When** the wizard reports the result
**Then** it exits with helpful install links for supported CLIs: `No AI CLIs detected. Install Claude CLI or Gemini CLI first.`
**And** the exit is clean with no config generated

### Story 6.2: Provider & Model Selection

As a **new user**,
I want the wizard to show me available models and let me pick which to use,
So that I can configure providers without memorizing model names.

**Acceptance Criteria:**

**Given** one or more CLI providers are detected
**When** the wizard queries each for available models
**Then** it presents a numbered list of models for each provider: `I found Claude CLI with: [1] opus-4 [2] sonnet-4. Which model for generative steps?`

**Given** a numbered model list is displayed
**When** the user types a number and presses Enter
**Then** the corresponding model is selected for the specified role

**Given** a model selection prompt
**When** the user presses Enter with no input
**Then** the default selection (first/recommended model) is accepted

**Given** the user enters an invalid number
**When** the input is validated
**Then** the wizard re-prompts with a hint: `Not a valid choice. Choose from the list above:`

**Given** multiple providers are available
**When** the wizard configures provider assignments
**Then** it asks which provider to use for generative steps and which for validation steps, with sensible defaults

**Given** only one provider is available
**When** the wizard configures provider assignments
**Then** it assigns the single provider to all step types without asking — no unnecessary questions about roles

**Given** any wizard prompt
**When** the user types `b` or `back`
**Then** the wizard returns to the previous question

**Given** any wizard prompt
**When** the user types `q` or presses Ctrl+C
**Then** the wizard exits cleanly with no config generated

### Story 6.3: Cycle & Workflow Configuration

As a **new user**,
I want the wizard to offer smart defaults I can accept with Enter,
So that I get a working config quickly without needing to understand every option.

**Acceptance Criteria:**

**Given** the wizard reaches cycle configuration
**When** it presents defaults
**Then** it offers: `Recommended: 1 story creation, 2 review cycles. Accept defaults? [Y/n]`

**Given** the user presses Enter or types `y`
**When** accepting defaults
**Then** the wizard uses the recommended cycle configuration and moves to the next section

**Given** the user types `n`
**When** declining defaults
**Then** the wizard walks through cycle configuration conversationally: `How many review rounds? Most users do 2 — enough to catch issues without burning credits.`

**Given** the wizard reaches git configuration
**When** it presents defaults
**Then** it offers: `Commit per cycle, push at end? [Y/n]`

**Given** the wizard reaches pause configuration
**When** it presents defaults
**Then** it offers: `Default pauses: 5s between steps, 15s between cycles. OK? [Y/n]`

**Given** the wizard reaches error handling configuration
**When** it presents defaults
**Then** it offers sensible retry defaults: `Retry transient errors up to 3 times with 10s delay? [Y/n]`

**Given** any configuration step
**When** the user accepts the default
**Then** the wizard moves forward immediately — no unnecessary follow-up questions

### Story 6.4: Config Generation & Validation

As a **new user**,
I want the wizard to generate a valid config and confirm it works,
So that I can start running cycles immediately with confidence.

**Acceptance Criteria:**

**Given** all wizard selections are complete
**When** the wizard generates the config
**Then** it creates a valid `bmad-orch.yaml` file in the current working directory with all selected providers, models, cycles, steps, git settings, pauses, and error handling

**Given** the config is generated
**When** the wizard validates it
**Then** it automatically runs the same validation as `bmad-orch validate` before saving — the user never gets a broken config

**Given** validation passes
**When** the wizard completes
**Then** it displays a Rich-formatted summary table showing the generated config: providers, models, cycle structure, git settings
**And** concludes with: `Config created! Run bmad-orch start to begin. Run bmad-orch validate to check config anytime.`

**Given** a `bmad-orch.yaml` already exists in the current directory
**When** the wizard attempts to save
**Then** it prompts: `Config exists. Overwrite? (y/n)` — defaults to `n` (safe option), single keystroke, no Enter required

**Given** the user declines to overwrite
**When** the wizard handles the refusal
**Then** it suggests an alternative: `Save as bmad-orch.backup.yaml instead? (y/n)` or allows the user to specify a different path

**Given** the generated YAML
**When** I inspect its format
**Then** config keys use `snake_case` matching Pydantic field names, and the structure matches the config schema from Epic 1
