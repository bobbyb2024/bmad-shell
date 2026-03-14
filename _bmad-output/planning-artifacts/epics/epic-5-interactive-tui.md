# Epic 5: Interactive TUI

User observes and controls live execution in a three-pane tmux TUI — watching model output stream in real-time, glancing at the status bar, using keyboard shortcuts, and sending input to models via the command pane.

## Story 5.1: Three-Pane tmux Layout & Pane Lifecycle

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

## Story 5.2: Pane Headers & Escalation Colors

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

## Story 5.3: Status Bar & Command Pane Log

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

## Story 5.4: Provider Output Streaming to Panes

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

## Story 5.5: Keyboard Shortcuts & Execution Control

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

## Story 5.6: Command Pane Input & Model Interaction

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
