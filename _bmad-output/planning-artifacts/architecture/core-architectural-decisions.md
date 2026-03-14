# Core Architectural Decisions

## Decision Priority Analysis

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

## Architectural Rules

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

## Engine Architecture

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

## State & Data Management

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

## Resource Monitoring

**psutil + Async Periodic Task:**
- Decision: Use psutil for process monitoring, polled by an asyncio periodic task
- Rationale: psutil is the standard Python library for system/process monitoring. Async periodic polling (configurable interval, default 5s) fits naturally in the asyncio engine.
- Behavior: Threshold breach (80% CPU or memory) → kill offending subprocess (`process.kill()` + `await process.wait()`) → emit `ResourceThresholdBreached` event → trigger impactful error flow
- Affects: Resource monitor module, engine lifecycle management, error handling flow

## Infrastructure & Distribution

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

## Decision Impact Analysis

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
