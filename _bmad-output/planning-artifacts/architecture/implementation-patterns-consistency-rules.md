# Implementation Patterns & Consistency Rules

## Pattern Categories Defined

**Critical Conflict Points Identified:** 8 areas where AI agents could make inconsistent choices — naming, structure, imports, error handling, async patterns, type annotations, testing, and subprocess lifecycle.

## Naming Patterns

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

## Structure Patterns

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

## Import Patterns

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

## Error Handling Patterns

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

## Async Patterns

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

## Type Annotation Patterns

- All public functions fully annotated (pyright strict mode enforces this)
- Union syntax: `str | None` not `Optional[str]`
- Abstract types from `collections.abc`: `Sequence`, `Mapping`, `AsyncIterator`
- Pydantic models for data crossing module boundaries
- Frozen dataclasses for events and internal value objects
- `py.typed` marker file in package root

## Testing Patterns

**Fixture Scoping:**
- **Session-scoped:** structlog configuration, event emitter factory
- **Function-scoped (default):** state manager with temp directory, mock provider adapters
- **Never module-scoped** — causes subtle test pollution

**Async test pattern:** Fixtures provide setup. Test body is act + assert only. No arrange in the test body.

**Import isolation test (`tests/test_import_isolation.py`):**
Runtime test that imports each core engine module and asserts `rich` and `libtmux` do not appear in `sys.modules`. Not a linting rule — a real test.

## Renderer Architecture

**Renderer Protocol (in `rendering/base.py`):**
Defines async handler methods for all event types: `on_step_started`, `on_provider_output`, `on_escalation_changed`, `on_step_completed`, `on_run_completed`, `on_error_occurred`.

**Emitter-Renderer wiring:**
- Emitter accepts `Callable` subscribers, not `Renderer` typed objects
- Emitter lives in `engine/` — never imports from `rendering/`
- The rendering module's `__init__` wires renderer methods as subscribers to the emitter
- No engine-to-rendering import — dependency flows one direction only

## Enforcement Guidelines

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
