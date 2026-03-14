---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-03-13'
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
workflowType: 'architecture'
project_name: 'bmad-shell'
user_name: 'Bobby'
date: '2026-03-13'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
49 functional requirements spanning 10 capability domains. The heaviest areas are Configuration Management (FR1-FR9: config generation, schema validation, template variable resolution), Provider Management (FR10-FR14: CLI detection, subprocess invocation, output capture, adapter interface), and the Cycle Engine (FR15-FR19: ordered step execution, generative vs validation step distinction, cycle repetition). State Management (FR20-FR24) and the Interactive TUI (FR32-FR37, FR49) represent the highest architectural complexity — state must be crash-safe and the TUI must layer cleanly over a headless-capable engine.

**Non-Functional Requirements:**
15 NFRs driving architectural decisions:
- **Reliability (NFR1-NFR6):** Atomic state writes, crash recovery, transient failure handling, zero work loss, comprehensive logging. These mandate a write-ahead state pattern and defensive subprocess management.
- **Resource Management (NFR7-NFR11):** Continuous CPU/memory monitoring at 80% thresholds with subprocess killing capability. Requires a monitoring subsystem active in all modes.
- **Integration (NFR12-NFR15):** Defensive CLI output parsing, no backwards compatibility shims, isolated subprocess invocation (hung providers can't block the orchestrator), explicit git error handling.

**Scale & Complexity:**

- Primary domain: Python CLI tool / subprocess orchestration
- Complexity level: Medium — multi-process coordination with state management, but single-user, single-machine, well-bounded domain
- Estimated architectural components: ~8-10 major modules (config, providers, cycle engine, state manager, resource monitor, git integration, TUI renderer, lite renderer, headless output, init wizard)

### Technical Constraints & Dependencies

- **Python ecosystem** — Rich for terminal formatting, tmux for TUI layout, YAML for configuration
- **Subprocess-based provider interaction** — AI CLIs are invoked as subprocesses, not libraries. Output capture is via stdout/stderr pipes. No API-level integration.
- **tmux as soft dependency** — Required for TUI mode only. Lite and Headless modes operate without it. Minimum tmux 3.0+.
- **No network services** — The orchestrator itself has zero network dependencies. Connectivity is the AI CLI providers' concern.
- **Single-machine execution** — No distributed operation. No remote orchestration. One orchestrator process per run.
- **Headless-first architecture** — PRD explicitly mandates building the engine headless-first with TUI as a presentation layer on top.

### Cross-Cutting Concerns Identified

- **Escalation State** — Single state object (ok/attention/action/complete/idle) drives all rendering across all three modes (TUI borders, Rich formatting, headless log severity). Every component reads from this; none independently determines state.
- **Error Classification** — Every error is classified as recoverable or impactful. This classification drives retry behavior, state persistence, git operations, and user communication across all modes.
- **State Persistence** — The JSON state file is the single source of truth for resume, monitoring, audit, and cross-mode portability. Atomic writes are non-negotiable.
- **Resource Monitoring** — Active in all modes. Monitors orchestrator + all spawned subprocesses. Threshold enforcement triggers impactful error flow.
- **Logging** — Per-step structured logs consolidated before git commit. Must serve both human debugging (grep-friendly) and machine parsing (structured format).

## Starter Template Evaluation

### Primary Technology Domain

Python CLI Tool / Subprocess Orchestrator — based on PRD classification and project requirements analysis.

### Starter Options Considered

**Third-party starter templates evaluated and rejected:**
- `copier` Python templates — add unnecessary scaffolding opinions and template maintenance dependency
- Community `uv-example-project` templates — useful for reference but add non-standard structure choices

**Selected approach: `uv init --package`** — Python's standard packaging toolchain with zero third-party template dependencies. For a CLI tool distributed via PyPI, the native `src/` layout with `[project.scripts]` entry points is the cleanest foundation.

### Selected Starter: uv init --package

**Rationale for Selection:**
Standard Python packaging with no template bloat. `uv init --package` creates the exact structure a PyPI-distributed CLI tool needs: `src/` layout, `pyproject.toml` with build system, and entry point configuration. All additional tooling is added as explicit dependencies with clear rationale.

**Initialization Command:**

```bash
uv init --package bmad-orch
cd bmad-orch
uv add typer rich pydantic pydantic-settings pyyaml
uv add --dev pytest pytest-cov pytest-asyncio pytest-timeout ruff pyright pre-commit
```

**Project Structure:**

```
bmad-orch/
├── src/
│   └── bmad_orch/
│       └── __init__.py
├── pyproject.toml
├── .python-version         # Pins Python 3.13
├── README.md
└── uv.lock
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:**
- Python 3.13 (latest stable) with `requires-python = ">=3.13"` floor
- `src/` layout for clean import separation and standard Python packaging

**CLI Framework:**
- Typer (latest, supports Python 3.10-3.13) — most popular modern CLI framework, type-hint driven, built on Click, native Rich integration for `--help` rendering, auto-completion for bash/zsh/fish

**Terminal Formatting:**
- Rich (latest) — formatting layer only (no TUI framework), as specified in UX design

**Configuration & Validation:**
- Pydantic v2 (2.12.x stable) — config schema validation, typed Python objects from YAML
- pydantic-settings — environment variable overrides for headless/CI mode
- PyYAML — YAML parsing into Pydantic models

**Build Tooling:**
- uv — package management, virtual environment, lockfile, dependency resolution
- hatchling — build backend (uv default), modern and fast
- All configuration in `pyproject.toml` — no scattered config files

**Testing Framework:**
- pytest 9.x — standard Python testing
- pytest-cov — coverage measurement (required by reliability NFRs)
- pytest-asyncio — async subprocess management testing
- pytest-timeout — prevents subprocess test hangs in CI
- Consider pytest-subprocess for subprocess invocation mocking

**Linting, Formatting & Type Checking:**
- Ruff 0.15.x (Astral, same team as uv) — replaces Black + isort + flake8, 2026 style guide, configured strict from day one
- pyright (latest) — 3-5x faster than mypy, implements newest typing features first, strict mode from day one
- pre-commit — runs Ruff + pyright on every commit

**Code Organization:**
- `pyproject.toml` as single configuration source for all tools (Ruff, pytest, pyright)
- `[project.scripts]` defines `bmad-orch` CLI entry point → Typer app
- `uv.lock` checked into version control for reproducible installs

**Note:** Project initialization using this command should be the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
1. Async engine architecture (asyncio)
2. Engine-to-presentation decoupling (event emitter)
3. Subprocess I/O management (PTY-everywhere with renderer-driven display)
4. Atomic state write strategy (temp file + atomic rename)
5. Logging architecture (structlog with async context)

**Important Decisions (Shape Architecture):**
6. Git integration (subprocess git, hardened)
7. Resource monitoring (psutil + async periodic task)
8. tmux interface (libtmux, lazy import)
9. Distribution (PyPI via uv publish)
10. CI/CD (GitHub Actions)

**Deferred Decisions (Post-MVP):**
- Shell completion generation (Typer provides this, configure in Phase 2)
- Plugin/extension architecture for community providers (Phase 3)
- Config repository/registry integration (Phase 3)

### Architectural Rules

These rules are non-negotiable constraints that prevent architectural drift:

1. **Dependency isolation by mode:**
   - Core engine imports only: asyncio, pydantic, pyyaml, structlog, psutil
   - TUI mode adds: libtmux (lazy import, only when TUI activates)
   - TUI + Lite modes add: Rich (lazy import, only when visual output needed)
   - Headless mode: zero additional imports beyond core
   - **Enforcement:** Any core engine module importing Rich or libtmux is an architectural violation. Detectable by import analysis test.

2. **Zombie process cleanup:** Every error path, cancellation path, and timeout handler must explicitly call `process.kill()` + `await process.wait()`. No subprocess reference may be discarded without cleanup. This is an architectural rule, not an implementation detail.

3. **Immutable events:** All event dataclasses are `@dataclass(frozen=True)`. No renderer may mutate an event. Renderer exceptions are caught by the emitter and logged — a broken renderer never crashes the engine.

4. **Same-filesystem temp files:** The state manager's temp file must be created in the same directory as the state file. `os.rename()` is only atomic within the same filesystem.

5. **No interactive git:** All git subprocess calls set `GIT_TERMINAL_PROMPT=0`, `GIT_PAGER=cat`, `GIT_EDITOR=true`. Git must never block on user input in any mode.

### Engine Architecture

**Async Engine (asyncio):**
- Decision: Use asyncio as the core engine runtime
- Rationale: Multiple concurrent concerns — subprocess I/O capture, resource monitoring, user input routing, state updates, timeout management — all coordinated by a single event loop without thread synchronization complexity
- Affects: All engine components, provider adapters, resource monitor, TUI input routing
- Key module: `asyncio.create_subprocess_exec` for provider invocation

**Event Emitter Pattern (Engine-to-Presentation):**
- Decision: Engine emits typed frozen dataclass events; renderers subscribe to events they handle
- Rationale: Three renderers (TUI, Lite, Headless) with different display needs. Event emitter provides clean decoupling — engine never imports or references any renderer. Events are immutable, easily testable. Renderer exceptions are caught and logged, never propagated to engine.
- Event types: `StepStarted`, `StepCompleted`, `CycleStarted`, `CycleCompleted`, `EscalationChanged`, `LogEntry`, `ProviderOutput`, `RunCompleted`, `ErrorOccurred`, `ResourceThresholdBreached`
- Dispatch: Synchronous within the async loop — no fire-and-forget. Event delivery is guaranteed and ordered.
- Affects: Engine core, all three renderers, logging subsystem

**PTY-Everywhere Subprocess I/O:**
- Decision: All modes use PTY-based capture. TUI renderer writes captured output to tmux panes. One execution path for all modes.
- Rationale: The hybrid approach (tmux panes for TUI, PTY for Lite/Headless) creates two fundamentally different execution paths through the riskiest component (provider adapters). PTY-everywhere means one provider adapter interface, one test suite, and true headless-first architecture. The TUI renderer receives `ProviderOutput` events and writes them to tmux panes — it is a pure presentation layer. PTY capture preserves ANSI formatting faithfully. The microsecond latency from the extra hop is negligible for terminal text.
- Provider adapter interface: `async def execute(prompt: str) -> AsyncIterator[OutputChunk]`
- Affects: Provider adapter interface (single implementation), all three renderers (receive same events)

### State & Data Management

**Atomic State Writes (temp + rename):**
- Decision: Write state to temporary file in the same directory, then atomic `os.rename()`
- Rationale: POSIX atomic rename guarantees the state file is always valid. Crash during write leaves previous state intact. No external dependencies.
- Constraint: Temp file MUST be in the same directory as state file (same filesystem requirement for atomic rename)
- Implementation: `write_state()` writes to `.bmad-orch-state.tmp`, then `os.rename()` to `bmad-orch-state.json`
- Affects: State manager module, resume logic, all components that read state

**Structured Logging (structlog with async context):**
- Decision: Use structlog for all logging with `structlog.contextvars` for async-local context propagation
- Rationale: The PRD's structured log format maps directly to structlog's context-binding model. Bind step/provider context once, all subsequent log calls include it automatically.
- Async safety: `structlog.contextvars` prevents context leaking between concurrent async tasks (e.g., resource monitor logs won't inherit the current step's provider context)
- Processor chains configured at startup, not at call sites:
  - Human mode (TUI/Lite): `[timestamp, severity_icon, context, message]` → colored text
  - Machine mode (Headless): `[iso_timestamp, severity_tag, context_dict, message]` → structured plain text
- Affects: All modules that produce log output, log consolidation before git commit

**Git Integration (subprocess, hardened):**
- Decision: Shell out to `git` CLI commands via subprocess with hardened configuration
- Rationale: ~5 git operations needed. Subprocess inherits user's git config, credentials, and hooks. NFR15 error handling is cleaner with direct stderr parsing.
- Hardening: All git calls set env vars `GIT_TERMINAL_PROMPT=0`, `GIT_PAGER=cat`, `GIT_EDITOR=true` to prevent interactive blocking
- Error handling: Always capture stderr, handle `index.lock` contention (detect and report, don't silently delete)
- Affects: Git integration module, emergency commit flow, CI/CD pipeline interaction

### Resource Monitoring

**psutil + Async Periodic Task:**
- Decision: Use psutil for process monitoring, polled by an asyncio periodic task
- Rationale: psutil is the standard Python library for system/process monitoring. Async periodic polling (configurable interval, default 5s) fits naturally in the asyncio engine.
- Behavior: Threshold breach (80% CPU or memory) → kill offending subprocess (`process.kill()` + `await process.wait()`) → emit `ResourceThresholdBreached` event → trigger impactful error flow
- Affects: Resource monitor module, engine lifecycle management, error handling flow

### Infrastructure & Distribution

**PyPI Distribution:**
- Decision: Publish to PyPI, install via `pipx install bmad-orch` or `uv tool install bmad-orch`
- Rationale: Standard Python package distribution. Entry point in `[project.scripts]` creates the `bmad-orch` CLI command.
- Affects: pyproject.toml configuration, release workflow

**GitHub Actions CI/CD:**
- Decision: GitHub Actions for CI/CD pipeline
- Pipeline: PR checks run Ruff lint + format, pyright type check, pytest with coverage. Release publishes to PyPI on tagged versions. Import analysis test enforces dependency isolation by mode.
- Affects: .github/workflows configuration, release process

**libtmux for tmux Interface (lazy import):**
- Decision: Use libtmux for programmatic tmux control, imported lazily only when TUI mode activates
- Rationale: Established Python-tmux bridge. Lazy import ensures headless mode has zero tmux dependency at runtime.
- Affects: TUI renderer, pane lifecycle management, pane header updates

### Decision Impact Analysis

**Implementation Sequence:**
1. Project scaffolding (uv init, dependencies, pyproject.toml config)
2. Config schema (Pydantic models for bmad-orch.yaml)
3. Event emitter (typed frozen dataclass events, subscriber registry)
4. State manager (atomic writes, state schema)
5. Provider adapter interface (async PTY-based execution, OutputChunk iterator)
6. Cycle engine (asyncio event loop, step execution, event emission)
7. Logging subsystem (structlog configuration, async context, dual processor chains)
8. Headless renderer (structured text output — validates engine works end-to-end)
9. Git integration (hardened subprocess wrapper)
10. Resource monitor (psutil polling task)
11. Lite renderer (Rich-formatted single stream)
12. TUI renderer (libtmux pane management, ProviderOutput → pane writing)
13. Init wizard (Typer interactive flow)

**Cross-Component Dependencies:**
- Event emitter is the backbone — engine, renderers, logger, and resource monitor all use it
- Provider adapter has a single interface (`AsyncIterator[OutputChunk]`) consumed by all renderers identically
- State manager is consumed by engine, resume logic, and all renderers
- Escalation state drives both event emission and renderer behavior
- structlog contextvars flow through engine → providers → logging → renderers
- Dependency isolation enforced by import analysis: core engine never imports Rich or libtmux

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:** 8 areas where AI agents could make inconsistent choices — naming, structure, imports, error handling, async patterns, type annotations, testing, and subprocess lifecycle.

### Naming Patterns

**Python Code Naming:**
- Functions/variables/modules: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Module files: `snake_case.py` (e.g., `cycle_engine.py`, `state_manager.py`)
- Private internals: single underscore prefix `_helper_function()`, never double underscore
- Type aliases: `PascalCase` (e.g., `ProviderName = str`)

**Config YAML Keys:**
- `snake_case` for all keys — matches Python convention and Pydantic field names
- Example: `error_handling.max_retries`, not `error-handling.max-retries`

**State File JSON Keys:**
- `snake_case` for all keys — matches Pydantic `model_dump()` default output
- Example: `steps_completed`, `current_step`, `last_provider`

**Event Type Names:**
- `PascalCase` frozen dataclasses
- Past tense for completed actions: `StepCompleted`, `CycleCompleted`
- Present tense for state changes: `EscalationChanged`
- Present tense for ongoing outputs: `ProviderOutput`

**Log Messages:**
- Sentence case, no trailing period: `Step 3 started: create story via Claude`
- Use structlog context binding, never f-strings: `log.info("Step started", step=3, provider="claude")`

**Test Names:**
- Format: `test_<unit>_<behavior>`
- Examples: `test_cycle_engine_emits_step_started_event()`, `test_state_manager_survives_crash_during_write()`, `test_claude_adapter_handles_timeout()`
- No `test_should_*` prefix — adds words without information

### Structure Patterns

**Module Organization (feature-based):**

```
src/bmad_orch/
├── __init__.py
├── py.typed                # Marker for pyright strict mode on published package
├── cli.py                  # Typer app, entry point
├── types.py                # Shared types: OutputChunk, EscalationState, ProviderName, StepOutcome, ErrorSeverity — zero internal dependencies
├── errors.py               # Complete exception hierarchy
├── config/
│   ├── __init__.py
│   ├── schema.py           # Pydantic models for bmad-orch.yaml
│   └── loader.py           # YAML loading + validation
├── engine/
│   ├── __init__.py
│   ├── cycle.py            # Cycle execution logic
│   ├── events.py           # All event frozen dataclasses
│   ├── emitter.py          # Event emitter (accepts Callable subscribers)
│   └── runner.py           # Top-level run orchestration
├── providers/
│   ├── __init__.py
│   ├── base.py             # Provider adapter ABC
│   ├── claude.py           # Claude CLI adapter
│   └── gemini.py           # Gemini CLI adapter
├── state/
│   ├── __init__.py
│   ├── manager.py          # Atomic state read/write
│   └── schema.py           # Pydantic models for state file
├── rendering/
│   ├── __init__.py
│   ├── base.py             # Renderer Protocol definition
│   ├── headless.py         # Structured text output
│   ├── lite.py             # Rich-formatted output (lazy Rich import)
│   └── tui.py              # tmux pane management (lazy libtmux import)
├── git.py                  # Git subprocess wrapper
├── resources.py            # psutil resource monitor
├── logging.py              # structlog configuration
└── wizard.py               # Init wizard flow
```

**Test Organization (mirror structure):**

```
tests/
├── conftest.py             # Shared fixtures (session + function scope)
├── test_import_isolation.py # Runtime test: Rich/libtmux not in sys.modules after core imports
├── test_config/
│   ├── test_schema.py
│   └── test_loader.py
├── test_engine/
│   ├── test_cycle.py
│   ├── test_events.py
│   ├── test_emitter.py
│   └── test_runner.py
├── test_providers/
│   ├── test_base.py
│   ├── test_claude.py
│   └── test_gemini.py
├── test_state/
│   ├── test_manager.py
│   └── test_schema.py
├── test_rendering/
│   ├── test_headless.py
│   ├── test_lite.py
│   └── test_tui.py
├── test_git.py
├── test_resources.py
└── test_wizard.py
```

**Structural Rules:**
- Tests mirror source structure — `test_engine/test_cycle.py` tests `engine/cycle.py`
- Never co-located — all tests in `tests/` directory
- Every `__init__.py` has `__all__` — explicit public API per module
- Every persistent data domain gets `schema.py` (Pydantic models) + `manager.py` (I/O)
- `types.py` has zero internal dependencies — safe to import from anywhere

### Import Patterns

**Relative within, absolute across:**
- Inside a module package: `from .events import StepStarted` (within `engine/`)
- Across module packages: `from bmad_orch.engine.events import StepStarted` (from `rendering/`)
- This makes dependency boundaries visible — relative = same module, absolute = cross-module

**Lazy imports for mode-specific dependencies:**
```python
# In rendering/tui.py — libtmux imported inside functions, not at module level
def create_tui_session():
    import libtmux  # Lazy: only when TUI mode activates
    server = libtmux.Server()
    ...
```

**Dependency graph (acyclic):**
```
types.py, errors.py ← (foundational, everything can import)
config/ ← types, errors
state/ ← types, errors, config
providers/ ← types, errors
engine/ ← types, errors, config, state, providers
rendering/ ← types, errors, engine (events only)
```

**Forbidden:**
- `import *` — never
- Module-level `import rich` or `import libtmux` in core engine files
- Circular imports — the dependency graph above is enforced
- `TYPE_CHECKING` block for type-only imports that would cause circular dependencies

### Error Handling Patterns

**Exception Hierarchy:**

```
BmadOrchError (base, carries ErrorSeverity)
├── ConfigError              (BLOCKING)
├── ProviderError
│   ├── ProviderNotFoundError    (BLOCKING)
│   ├── ProviderTimeoutError     (RECOVERABLE)
│   └── ProviderCrashError       (IMPACTFUL)
├── StateError               (IMPACTFUL)
├── GitError                 (IMPACTFUL)
├── ResourceError            (IMPACTFUL)
└── WizardError              (BLOCKING)
```

**Severity Classification:**
- `BLOCKING` — pre-run, cannot proceed. Exit with specific code.
- `RECOVERABLE` — retry per config, log, continue. User never sees it unless inspecting logs.
- `IMPACTFUL` — emergency commit + push + halt. Show headline + next action.

**Error handling rules:**
- Engine checks `error.severity`, not `isinstance(error, RecoverableError)`
- All exceptions carry structured context
- Never catch bare `Exception` — always specific types or `BmadOrchError`
- User-facing format: `✗ [What happened] — [What to do next]`

### Async Patterns

**All public engine methods are `async def`.**

**Cancellation safety:**
- Every `await` in a loop checks cancellation or uses `asyncio.shield()` for critical sections (state writes)
- Never use `asyncio.wait_for` without a cleanup handler

**Subprocess lifecycle (non-negotiable pattern):**
```
process = create_subprocess(...)
try:
    async for chunk in read_pty_output(process):
        emit ProviderOutput event
    await process.wait()
finally:
    if process.returncode is None:
        process.kill()
        await process.wait()
```

### Type Annotation Patterns

- All public functions fully annotated (pyright strict mode enforces this)
- Union syntax: `str | None` not `Optional[str]`
- Abstract types from `collections.abc`: `Sequence`, `Mapping`, `AsyncIterator`
- Pydantic models for data crossing module boundaries
- Frozen dataclasses for events and internal value objects
- `py.typed` marker file in package root

### Testing Patterns

**Fixture Scoping:**
- **Session-scoped:** structlog configuration, event emitter factory
- **Function-scoped (default):** state manager with temp directory, mock provider adapters
- **Never module-scoped** — causes subtle test pollution

**Async test pattern:** Fixtures provide setup. Test body is act + assert only. No arrange in the test body.

**Import isolation test (`tests/test_import_isolation.py`):**
Runtime test that imports each core engine module and asserts `rich` and `libtmux` do not appear in `sys.modules`. Not a linting rule — a real test.

### Renderer Architecture

**Renderer Protocol (in `rendering/base.py`):**
Defines async handler methods for all event types: `on_step_started`, `on_provider_output`, `on_escalation_changed`, `on_step_completed`, `on_run_completed`, `on_error_occurred`.

**Emitter-Renderer wiring:**
- Emitter accepts `Callable` subscribers, not `Renderer` typed objects
- Emitter lives in `engine/` — never imports from `rendering/`
- The rendering module's `__init__` wires renderer methods as subscribers to the emitter
- No engine-to-rendering import — dependency flows one direction only

### Enforcement Guidelines

**All AI Agents MUST:**
1. Follow the module structure — new functionality goes in the appropriate existing module
2. Use relative imports within packages, absolute across packages
3. Add type annotations to all public functions
4. Write tests that mirror the source structure in `tests/`
5. Use structlog context binding, never f-string log messages
6. Use the exception hierarchy — never raise bare `Exception` or invent new exception classes without extending `BmadOrchError`
7. Follow the subprocess try/finally cleanup pattern
8. Keep Rich and libtmux imports lazy (function-level, not module-level) in rendering modules
9. Use Pydantic models for data crossing module boundaries
10. Use frozen dataclasses for events and internal value objects
11. Include `__all__` in every `__init__.py`
12. Name tests `test_<unit>_<behavior>`
13. Use function-scoped or session-scoped fixtures only

**Anti-Patterns to Reject:**
- `import *` — never
- Module-level `import rich` or `import libtmux` in core engine files
- Bare `except Exception:` — always specific types
- `subprocess.run()` in async code — always async subprocess creation
- Mutable state objects — always immutable with `with_*` update methods
- String concatenation for log messages — always structlog context binding
- `test_should_*` naming — use `test_<unit>_<behavior>`
- Module-scoped test fixtures — function or session only
- Inventing exception classes outside the defined hierarchy

## Project Structure & Boundaries

### Complete Project Directory Structure

```
bmad-orch/
├── .github/
│   └── workflows/
│       ├── ci.yml                  # PR checks: ruff, pyright, pytest, import isolation
│       └── release.yml             # Tagged release → PyPI publish
├── .gitignore
├── .pre-commit-config.yaml         # pre-commit hooks: ruff, pyright
├── .python-version                 # Pins Python 3.13
├── README.md
├── pyproject.toml                  # Single config source: project metadata, dependencies,
│                                   # ruff config, pytest config, pyright config
├── uv.lock                        # Checked into VCS for reproducible installs
│
├── src/
│   └── bmad_orch/
│       ├── __init__.py             # Package version, top-level __all__
│       ├── py.typed                # PEP 561 marker for type checker support
│       ├── cli.py                  # Typer app: bmad-orch start, resume, status, validate, --init
│       ├── types.py                # OutputChunk, EscalationState, ProviderName, StepOutcome,
│       │                           # ErrorSeverity, StepType — zero internal deps
│       ├── errors.py               # BmadOrchError hierarchy (see Implementation Patterns)
│       │
│       ├── config/
│       │   ├── __init__.py         # Exports: OrchestratorConfig, load_config, validate_config
│       │   ├── schema.py           # Pydantic models: OrchestratorConfig, ProviderConfig,
│       │   │                       # CycleConfig, StepConfig, GitConfig, PauseConfig, ErrorConfig
│       │   └── loader.py           # YAML file discovery, loading, Pydantic validation,
│       │                           # template variable registry
│       │
│       ├── engine/
│       │   ├── __init__.py         # Exports: CycleEngine, EventEmitter, Runner
│       │   ├── events.py           # Frozen dataclasses: StepStarted, StepCompleted,
│       │   │                       # CycleStarted, CycleCompleted, EscalationChanged,
│       │   │                       # ProviderOutput, RunCompleted, ErrorOccurred,
│       │   │                       # ResourceThresholdBreached, LogEntry
│       │   ├── emitter.py          # EventEmitter: subscribe(event_type, Callable), emit(event)
│       │   │                       # Catches subscriber exceptions, logs, never propagates
│       │   ├── cycle.py            # CycleExecutor: runs steps in order, distinguishes
│       │   │                       # generative vs validation, handles repeat counts
│       │   └── runner.py           # Runner: top-level orchestration, wires engine + providers
│       │                           # + state + renderers, manages the asyncio event loop
│       │
│       ├── providers/
│       │   ├── __init__.py         # Exports: ProviderAdapter, get_adapter(name)
│       │   ├── base.py             # ProviderAdapter ABC: execute(prompt) -> AsyncIterator[OutputChunk],
│       │   │                       # detect() -> bool, list_models() -> list[str]
│       │   ├── claude.py           # ClaudeAdapter: claude CLI invocation via PTY
│       │   └── gemini.py           # GeminiAdapter: gemini CLI invocation via PTY
│       │
│       ├── state/
│       │   ├── __init__.py         # Exports: StateManager, RunState
│       │   ├── schema.py           # Pydantic models: RunState, StepRecord, CycleRecord,
│       │   │                       # ErrorRecord — immutable with with_* update methods
│       │   └── manager.py          # StateManager: load(), save() with atomic temp+rename,
│       │                           # state file discovery, resume point detection
│       │
│       ├── rendering/
│       │   ├── __init__.py         # Exports: create_renderer(mode) — factory that wires
│       │   │                       # renderer methods as emitter subscribers
│       │   ├── base.py             # Renderer Protocol: on_step_started, on_provider_output,
│       │   │                       # on_escalation_changed, on_step_completed, etc.
│       │   ├── headless.py         # HeadlessRenderer: structured plain text to stdout/stderr,
│       │   │                       # no ANSI, no dependencies beyond structlog
│       │   ├── lite.py             # LiteRenderer: Rich-formatted single stream output
│       │   │                       # (lazy Rich import). Status line, colored escalation,
│       │   │                       # pre-flight table, completion summary
│       │   └── tui.py              # TuiRenderer: libtmux session/pane management
│       │                           # (lazy libtmux import). Creates 3-pane layout,
│       │                           # writes ProviderOutput to panes, manages pane headers,
│       │                           # border colors, status bar in command pane
│       │
│       ├── git.py                  # GitClient: hardened subprocess wrapper. commit(), push(),
│       │                           # add(), status(). Sets GIT_TERMINAL_PROMPT=0, GIT_PAGER=cat,
│       │                           # GIT_EDITOR=true. Handles index.lock, captures stderr.
│       │
│       ├── resources.py            # ResourceMonitor: async periodic psutil polling.
│       │                           # Tracks orchestrator PID + all spawned subprocess PIDs.
│       │                           # Emits ResourceThresholdBreached on 80% CPU/memory.
│       │
│       ├── logging.py              # configure_logging(mode): sets up structlog with
│       │                           # contextvars, selects human or machine processor chain.
│       │                           # Per-step log capture, consolidation before git commit.
│       │
│       └── wizard.py               # InitWizard: Typer-driven interactive flow. Detects tmux,
│                                   # detects CLIs, queries models, configures cycles,
│                                   # generates bmad-orch.yaml. Conversational tone.
│
└── tests/
    ├── conftest.py                 # Shared fixtures: tmp state dirs, mock providers,
    │                               # event collectors, sample configs
    ├── test_import_isolation.py    # Asserts core modules don't pull in Rich/libtmux
    ├── test_cli.py                 # Typer CLI integration tests
    ├── test_types.py               # Shared type validation
    ├── test_errors.py              # Exception hierarchy, severity classification
    │
    ├── test_config/
    │   ├── test_schema.py          # Pydantic model validation, edge cases
    │   └── test_loader.py          # YAML loading, file discovery, template resolution
    │
    ├── test_engine/
    │   ├── test_events.py          # Event immutability, field validation
    │   ├── test_emitter.py         # Subscribe, emit, exception isolation
    │   ├── test_cycle.py           # Step ordering, generative vs validation, repeat
    │   └── test_runner.py          # End-to-end engine orchestration with mock providers
    │
    ├── test_providers/
    │   ├── test_base.py            # Adapter interface contract tests
    │   ├── test_claude.py          # Claude CLI detection, PTY execution, error handling
    │   └── test_gemini.py          # Gemini CLI detection, PTY execution, error handling
    │
    ├── test_state/
    │   ├── test_schema.py          # State model immutability, with_* methods
    │   └── test_manager.py         # Atomic writes, crash recovery, resume detection
    │
    ├── test_rendering/
    │   ├── test_headless.py        # Structured output format, no ANSI codes
    │   ├── test_lite.py            # Rich formatting, status bar, escalation colors
    │   └── test_tui.py             # libtmux pane creation, output writing, header updates
    │
    ├── test_git.py                 # Git subprocess wrapper, env hardening, error handling
    ├── test_resources.py           # psutil polling, threshold detection, subprocess tracking
    └── test_wizard.py              # Init wizard flow, CLI detection, config generation
```

### Architectural Boundaries

**Module Boundaries (import direction enforced):**

```
                    ┌──────────┐
                    │ cli.py   │  Entry point — wires everything
                    └────┬─────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
        ┌──────────┐ ┌────────┐ ┌────────┐
        │ wizard   │ │ runner │ │ git    │
        └──────────┘ └───┬────┘ └────────┘
                         │
           ┌─────────────┼─────────────┐
           ▼             ▼             ▼
     ┌──────────┐  ┌──────────┐  ┌───────────┐
     │ engine/  │  │rendering/│  │ resources  │
     │ cycle    │  │ (factory)│  │            │
     │ emitter  │  └──────────┘  └───────────┘
     └────┬─────┘        │
          │         ┌────┴────────────┐
          ▼         ▼        ▼        ▼
    ┌──────────┐ ┌────────┐┌──────┐┌─────┐
    │providers/│ │headless││ lite ││ tui │
    └──────────┘ └────────┘└──────┘└─────┘
          │
          ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐
    │ state/   │  │ config/  │  │ logging  │
    └──────────┘  └──────────┘  └──────────┘
          │            │
          ▼            ▼
    ┌──────────┐  ┌──────────┐
    │ types.py │  │ errors.py│
    └──────────┘  └──────────┘
```

**Boundary Rules:**
- Arrows show allowed import direction — never import against the arrow
- `types.py` and `errors.py` are foundational — imported by everything, import nothing internal
- `rendering/` imports from `engine/events.py` only — never from `engine/cycle.py` or `engine/runner.py`
- `engine/` never imports from `rendering/` — emitter accepts plain Callables
- `providers/` never imports from `engine/` — adapters are standalone
- `cli.py` is the composition root — the only place that wires all modules together

**Event-Driven Integration:**
All cross-module communication flows through the event emitter:
- Engine emits → Renderers display
- Engine emits → Logger records
- ResourceMonitor emits → Engine reacts (halt)
- No direct function calls across module boundaries for runtime behavior

### Requirements to Structure Mapping

**FR Category to Module Mapping:**

| FR Category | FRs | Primary Module | Supporting Modules |
|---|---|---|---|
| Configuration Management | FR1-FR9 | `config/` | `wizard.py`, `cli.py` |
| Provider Management | FR10-FR14 | `providers/` | `config/schema.py` |
| Cycle Engine | FR15-FR19 | `engine/cycle.py` | `engine/runner.py` |
| State Management | FR20-FR24 | `state/` | `engine/runner.py` |
| Logging and Observability | FR25-FR28 | `logging.py` | `engine/events.py` |
| Git Integration | FR29-FR31 | `git.py` | `engine/runner.py` |
| Interactive TUI | FR32-FR37 | `rendering/tui.py` | `rendering/base.py` |
| Validation and Diagnostics | FR38-FR41 | `config/loader.py`, `errors.py` | `cli.py` |
| Init Wizard | FR42-FR45 | `wizard.py` | `providers/`, `config/` |
| Workflow Control | FR46-FR47 | `engine/runner.py` | `rendering/`, `cli.py` |
| Audit Trail | FR48 | `state/schema.py` | `logging.py` |
| User-Model Interaction | FR49 | `rendering/tui.py` | `engine/emitter.py` |

**NFR to Module Mapping:**

| NFR Category | NFRs | Primary Module | Enforcement |
|---|---|---|---|
| Reliability | NFR1-NFR6 | `state/manager.py`, `logging.py` | Atomic writes, comprehensive logging |
| Resource Management | NFR7-NFR11 | `resources.py` | Async polling, subprocess kill + cleanup |
| Integration | NFR12-NFR15 | `providers/`, `git.py` | Defensive parsing, subprocess isolation |

**Cross-Cutting Concerns to Location:**

| Concern | Where It Lives | How It Is Enforced |
|---|---|---|
| Escalation State | `types.py` (enum), `engine/emitter.py` (transitions) | Only engine mutates, renderers read via events |
| Error Classification | `errors.py` (hierarchy), `types.py` (ErrorSeverity) | Exception severity attribute, engine checks |
| Subprocess Cleanup | `providers/base.py` (pattern), every adapter | try/finally in every subprocess call |
| Atomic State | `state/manager.py` | temp + rename, same-directory constraint |
| Dependency Isolation | `rendering/` lazy imports | `test_import_isolation.py` runtime test |

### Data Flow

**Happy Path (start to completion):**
```
cli.py -> load config -> validate -> create runner
  runner -> create engine + providers + renderer + state manager + resource monitor
    engine.run():
      for each cycle:
        for each step:
          provider.execute(prompt) -> AsyncIterator[OutputChunk]
            emitter.emit(ProviderOutput) -> renderer displays
          emitter.emit(StepCompleted) -> state_manager.save() -> renderer updates
        emitter.emit(CycleCompleted) -> git.commit() if configured
      emitter.emit(RunCompleted) -> git.push() if configured -> renderer shows summary
```

**Error Path (impactful error):**
```
provider raises ProviderCrashError (severity=IMPACTFUL)
  -> engine catches, emits ErrorOccurred
    -> renderer shows headline
    -> state_manager.save(error state) — atomic write
    -> git.commit() + git.push() — emergency commit
    -> engine halts, cli.py exits with code 3
```

**Resume Path:**
```
cli.py resume -> state_manager.load() -> detect resume point
  -> renderer shows resume context (last run, failure point, options)
  -> user selects option -> engine.run(from=resume_point)
```

### Development Workflow

**Local Development:**
```
uv sync                           # Install all dependencies
uv run bmad-orch --init           # Test init wizard
uv run bmad-orch start            # Test TUI mode
uv run bmad-orch start --headless # Test headless mode
uv run pytest                     # Run all tests
uv run ruff check .               # Lint
uv run ruff format .              # Format
uv run pyright                    # Type check
```

**Pre-Commit Hooks (.pre-commit-config.yaml):**
- `ruff check --fix` — auto-fix lint issues
- `ruff format` — format code
- `pyright` — type check

**CI Pipeline (.github/workflows/ci.yml):**
1. `uv sync` — install dependencies
2. `ruff check .` — lint (no auto-fix in CI)
3. `ruff format --check .` — format check
4. `pyright` — type check
5. `pytest --cov=bmad_orch --cov-report=xml` — tests + coverage
6. Import isolation test runs as part of pytest suite

**Release Pipeline (.github/workflows/release.yml):**
1. Triggered on version tag (v*)
2. Run full CI checks
3. `uv build` — build wheel + sdist
4. `uv publish` — publish to PyPI

## Architecture Validation Results

### Coherence Validation

**Decision Compatibility:** All technology choices are compatible. Python 3.13 + asyncio + Typer + Rich + Pydantic v2 + structlog + psutil + libtmux — all current, all Python-native, no known conflicts. Typer uses Rich internally (zero integration friction). Pydantic v2 + PyYAML is a standard combination. structlog works with asyncio via `structlog.contextvars`. libtmux is pure Python.

**Pattern Consistency:** All patterns align. snake_case naming across Python code, YAML keys, JSON keys, and structlog context. Event emitter pattern consistently used for all cross-module communication. Subprocess try/finally cleanup applies everywhere subprocesses are spawned. Error severity classification drives behavior uniformly across engine, renderers, and git operations.

**Structure Alignment:** Project structure supports all decisions. Dependency graph is acyclic and matches import rules. `types.py` and `errors.py` at the root enable foundational imports without circular dependencies. Rendering module's lazy imports enforce dependency isolation. `cli.py` as composition root means wiring changes don't propagate.

**No contradictions found.**

### Requirements Coverage Validation

**Functional Requirements — Full Coverage (49/49):**

| FRs | Status | Architectural Support |
|---|---|---|
| FR1-FR9 (Config) | Covered | `config/schema.py`, `config/loader.py`, `wizard.py`, `cli.py` |
| FR10-FR14 (Providers) | Covered | `providers/base.py`, `providers/claude.py`, `providers/gemini.py`, PTY execution |
| FR15-FR19 (Cycle Engine) | Covered | `engine/cycle.py`, `engine/runner.py` |
| FR20-FR24 (State) | Covered | `state/manager.py`, `state/schema.py` |
| FR25-FR28 (Logging) | Covered | `logging.py` (structlog, dual processor chains) |
| FR29-FR31 (Git) | Covered | `git.py` (hardened wrapper, configurable timing, emergency commit) |
| FR32-FR37 (TUI) | Covered | `rendering/tui.py` (libtmux, 3-pane, shortcuts) |
| FR38-FR41 (Validation) | Covered | `config/loader.py`, `errors.py`, engine error handling |
| FR42-FR45 (Init Wizard) | Covered | `wizard.py` |
| FR46-FR47 (Workflow Control) | Covered | `engine/runner.py`, renderers |
| FR48 (Audit Trail) | Covered | `state/schema.py` |
| FR49 (User-Model Interaction) | Covered | `rendering/tui.py` |

**Non-Functional Requirements — Full Coverage (15/15):**

| NFRs | Status | Architectural Support |
|---|---|---|
| NFR1-NFR6 (Reliability) | Covered | Atomic state writes, subprocess cleanup, structlog logging |
| NFR7-NFR11 (Resources) | Covered | `resources.py` (psutil, 80% threshold, kill + cleanup) |
| NFR12-NFR15 (Integration) | Covered | Defensive adapters, hardened git, subprocess isolation |

### Implementation Readiness Validation

**Decision Completeness:** All critical decisions documented with specific technology choices and versions. Rationale provided for every decision. No ambiguous TBD items for MVP.

**Structure Completeness:** Every source file and test file defined with purpose and exports. Module boundaries explicit with enforced dependency graph.

**Pattern Completeness:** 13 enforcement rules, 9 anti-patterns, concrete exception hierarchy, subprocess lifecycle pattern, async test pattern, import rules, naming conventions — all specific enough for AI agents to follow without interpretation.

### Gap Analysis Results

**Critical Gaps:** None.

**Important Gaps (non-blocking, address during implementation):**
1. Config template variable resolution (FR9) — `config/loader.py` should include a `TemplateResolver`. Module is defined; resolution mechanism is an implementation detail.
2. Keyboard shortcut registration — libtmux supports `bind-key`. Implementation detail for `rendering/tui.py`.
3. Lite mode sequential output handling — Rich `Live` display or manual terminal update. Implementation detail for `rendering/lite.py`.

**Nice-to-Have Gaps:**
- Shell completion (deferred Phase 2, Typer provides mechanism)
- Detailed pyproject.toml sections (implementation detail for story 1)

### Architecture Completeness Checklist

**Requirements Analysis**
- [x] Project context thoroughly analyzed (49 FRs, 15 NFRs)
- [x] Scale and complexity assessed (medium, single-machine CLI tool)
- [x] Technical constraints identified (subprocess-based, tmux soft dependency, headless-first)
- [x] Cross-cutting concerns mapped (escalation, errors, state, resources, logging)

**Architectural Decisions**
- [x] Critical decisions documented with versions (asyncio, event emitter, PTY-everywhere, atomic state, structlog)
- [x] Technology stack fully specified (Python 3.13, uv, Typer, Rich, Pydantic, structlog, psutil, libtmux, Ruff, pyright)
- [x] Integration patterns defined (event-driven, Callable subscribers, Renderer Protocol)
- [x] 5 architectural rules established (dependency isolation, zombie cleanup, immutable events, same-filesystem temps, no interactive git)

**Implementation Patterns**
- [x] Naming conventions established (Python, YAML, JSON, events, logs, tests)
- [x] Structure patterns defined (module organization, test mirroring, __all__ exports)
- [x] Import patterns specified (relative within, absolute across, lazy mode imports)
- [x] Error handling patterns documented (exception hierarchy, severity classification)
- [x] Async patterns specified (subprocess lifecycle, cancellation safety)
- [x] Testing patterns defined (fixture scoping, test naming, import isolation)

**Project Structure**
- [x] Complete directory structure defined (every file with purpose)
- [x] Component boundaries established (dependency graph, boundary rules)
- [x] Integration points mapped (event emitter backbone)
- [x] Requirements to structure mapping complete (49 FRs + 15 NFRs mapped)
- [x] Data flow documented (happy path, error path, resume path)
- [x] Development workflow defined (local dev, pre-commit, CI, release)

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High — all requirements mapped, no critical gaps, patterns are specific and enforceable.

**Key Strengths:**
- Headless-first with PTY-everywhere gives one execution path and true presentation layer separation
- Event emitter backbone enables clean module boundaries without circular dependencies
- Comprehensive enforcement guidelines (13 rules + 9 anti-patterns) leave minimal room for AI agent interpretation
- FR-to-module mapping means any story can be traced to its architectural home
- Exception hierarchy with severity attributes unifies error handling across the entire system

**Areas for Future Enhancement:**
- Phase 1.5: Retry logic for transient failures (architecture supports via RECOVERABLE severity)
- Phase 2: Four-pane TUI layout (tmux split is one additional pane)
- Phase 2: `--init --update` for adding providers (wizard.py extension)
- Phase 3: Plugin architecture for community providers (provider adapter ABC is extensible)

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented
- Use implementation patterns consistently across all components
- Respect project structure and module boundaries — check the dependency graph before adding imports
- Use the exception hierarchy — never invent new exception types outside the defined tree
- Every subprocess gets try/finally cleanup — no exceptions
- Refer to this document for all architectural questions

**First Implementation Priority:**
```
uv init --package bmad-orch
cd bmad-orch
uv add typer rich pydantic pydantic-settings pyyaml structlog psutil libtmux
uv add --dev pytest pytest-cov pytest-asyncio pytest-timeout ruff pyright pre-commit
```
Then scaffold the module structure as defined in Project Structure and Boundaries.
