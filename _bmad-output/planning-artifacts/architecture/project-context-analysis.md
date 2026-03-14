# Project Context Analysis

## Requirements Overview

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

## Technical Constraints & Dependencies

- **Python ecosystem** — Rich for terminal formatting, tmux for TUI layout, YAML for configuration
- **Subprocess-based provider interaction** — AI CLIs are invoked as subprocesses, not libraries. Output capture is via stdout/stderr pipes. No API-level integration.
- **tmux as soft dependency** — Required for TUI mode only. Lite and Headless modes operate without it. Minimum tmux 3.0+.
- **No network services** — The orchestrator itself has zero network dependencies. Connectivity is the AI CLI providers' concern.
- **Single-machine execution** — No distributed operation. No remote orchestration. One orchestrator process per run.
- **Headless-first architecture** — PRD explicitly mandates building the engine headless-first with TUI as a presentation layer on top.

## Cross-Cutting Concerns Identified

- **Escalation State** — Single state object (ok/attention/action/complete/idle) drives all rendering across all three modes (TUI borders, Rich formatting, headless log severity). Every component reads from this; none independently determines state.
- **Error Classification** — Every error is classified as recoverable or impactful. This classification drives retry behavior, state persistence, git operations, and user communication across all modes.
- **State Persistence** — The JSON state file is the single source of truth for resume, monitoring, audit, and cross-mode portability. Atomic writes are non-negotiable.
- **Resource Monitoring** — Active in all modes. Monitors orchestrator + all spawned subprocesses. Threshold enforcement triggers impactful error flow.
- **Logging** — Per-step structured logs consolidated before git commit. Must serve both human debugging (grep-friendly) and machine parsing (structured format).
