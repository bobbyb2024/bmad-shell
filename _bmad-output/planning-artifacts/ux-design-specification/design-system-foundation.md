# Design System Foundation

## Design System Choice

**Hybrid: tmux (layout + structural chrome) + Rich (command pane formatting)** — tmux manages the three-pane layout and pane headers as the structural engine, Rich handles formatting exclusively within the command/status pane. Model output panes remain raw subprocess output. This three-layer separation delivers terminal-native feel with polished informational styling and zero rendering conflicts. Terminal-native is the brand — the design system reinforces this positioning.

## Rationale for Selection

1. **Zero-friction install** — Rich is a Python package bundled in `pyproject.toml`. Users run `pip install bmad-orch` (or `pipx install bmad-orch`) and everything resolves automatically. tmux is a soft dependency — recommended but not required for basic operation.
2. **Terminal-native feel** — tmux owns pane layout, splitting, resizing, and pane headers — patterns users already understand. Rich adds styling only in the command pane without taking over the screen or introducing a custom event loop.
3. **Rich over Textual** — Textual is a full TUI framework with its own event loop that would fight tmux for control. Rich is a formatting/output library — lightweight, no widget framework overhead, simple print-like API. It stays out of the way.
4. **No rendering conflicts** — Rich never manages model output panes. Pane headers use tmux's native `pane-border-format`, eliminating scroll-off issues and output interception latency. Each layer has a single owner.
5. **Proven and popular** — Rich is one of the most widely used Python terminal libraries (~50k GitHub stars), well-maintained, with excellent documentation. Low risk, low learning curve.
6. **Competitive positioning** — Terminal-native + tmux-based is a deliberate market position. Competing orchestration tools (LangChain, CrewAI, AutoGen) are library-first with optional web dashboards. This tool is FOR terminal users, not a web dashboard that happens to run from the command line.

## Three Operational Modes

**1. TUI Mode (default — requires tmux)**
- Full three-pane layout: Model A, Model B, Command/Status
- tmux pane borders with escalation colors, Rich-formatted command pane
- Complete visual experience as designed

**2. Lite Mode (implicit when tmux unavailable)**
- No tmux — Rich IS available
- Single-pane sequential experience: model output streams one at a time, Rich formats status updates, escalation colors, pre-flight summaries, and completion reports
- Degraded but still visual — styled status bars, colored escalation, formatted tables
- Fills the gap between full TUI and headless. Users without tmux still get a meaningful visual experience.

**3. Headless Mode (`--headless` flag)**
- No tmux, no Rich — entire visual layer peels off
- Structured plain text with timestamps and severity tags
- Machine-parseable, grep-friendly — for CI/CD pipelines and containers
- Exit codes for scripting integration

**tmux Detection & Guidance:**
- Init wizard step zero: detect tmux before provider detection
- If missing on macOS: "tmux not found. Install with: `brew install tmux`"
- If missing on Linux: "tmux not found. Install with: `sudo apt install tmux` or `sudo dnf install tmux`"
- If user declines or can't install: "No tmux? No problem — you'll run in Lite mode with styled terminal output. Install tmux later for the full TUI experience."
- tmux never blocks adoption. Users get value immediately.

## Implementation Approach

**Layer 1 — Layout + Structural Chrome (tmux) [TUI mode only]:**
- Three-pane layout: Model A (top), Model B (middle), Command/Status (bottom)
- tmux controls pane creation, sizing, splitting, and destruction
- Pane proportions: model panes get majority of vertical space, command pane ~5-6 lines
- **Pane headers via `pane-border-format`** — pinned, non-scrolling pane labels showing provider name, model, current step, and pane state. Updated dynamically via `tmux select-pane -T`
- **Escalation colors in pane borders** — tmux pane border colors carry green/yellow/red semantics. Users glance at border color to know pane state without reading text.
- Phase 2 extensibility: four-pane layout is a single additional tmux split

**Layer 2 — Informational Chrome (Rich) [TUI + Lite modes]:**
- **TUI mode scope: command/status pane only** — Rich never renders to model output panes
- **Lite mode scope: full terminal** — Rich formats all status output, model output streams raw between Rich-formatted headers
- **Status bar** — Rich-formatted status line: `[story 2/5] step 3/4 | claude | cycle 1/2 | ▓▓▓░░ 60% | 12m elapsed | ✓ ok`
- **Escalation colors** — Same green/yellow/red palette as tmux borders, applied to status text via Rich's color system
- **Pre-flight summary** — Rich tables for playbook display — scannable in 3 seconds
- **Completion reports** — Rich-formatted stats: cycle counts, commit counts, timing, error counts
- **Error headlines** — Rich-styled one-line error summaries with severity coloring

**Layer 3 — Content (Raw Output) [All modes]:**
- Model streaming output remains completely unmodified — exactly as the CLI produces it
- In TUI mode: each model pane is a tmux pane running a subprocess
- In Lite mode: model output streams sequentially to the terminal
- In Headless mode: model output captured to log files
- Visual differences between provider outputs preserved in all modes

**Escalation State Architecture:**
- Single state object drives all escalation rendering across all layers
- When state transitions (e.g., `ok` → `attention`), one function atomically updates both tmux border color AND Rich status color
- No independent code paths, no race conditions, no contradictory signals between layers
- State machine is testable independently of renderers — UX correctness lives in state transitions, not rendering

## Customization Strategy

**Color Tokens (shared across tmux and Rich):**
- `ok` (green) — nominal state, no attention needed
- `attention` (yellow) — model awaiting input, non-critical event
- `action` (red) — error, intervention required
- `dim` — secondary/idle information (timestamps, muted text)
- `bold` — active/important elements (provider names, active step)
- All colors terminal-safe and selected for colorblind accessibility

**Pane Header Format [TUI mode]:**
- `[provider icon] Provider Name | model-name | step description [active/waiting]`
- Updated dynamically as steps progress via tmux pane title API
- Border color matches escalation state

**Status Bar Format [TUI + Lite modes]:**
- Fixed-format segments separated by `|`, left-to-right priority (most important info first)
- `[cycle type step/total] step N/M | provider | cycle R/T | progress | elapsed | state`

**Component Patterns:**
- Error display: headline in command pane (Rich), full context in log file — never both in the same surface
- Idle indicator: breathing dots in command pane + "Waiting for next step" in pane header
- Pre-flight: Rich table, auto-dismiss after first successful run
