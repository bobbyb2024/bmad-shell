# Project Structure & Boundaries

## Complete Project Directory Structure

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

## Architectural Boundaries

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

## Requirements to Structure Mapping

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

## Data Flow

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

## Development Workflow

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
