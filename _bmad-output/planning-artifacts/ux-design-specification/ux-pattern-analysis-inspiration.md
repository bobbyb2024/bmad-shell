# UX Pattern Analysis & Inspiration

## Inspiring Products Analysis

**Claude CLI / Gemini CLI / Copilot CLI** — The primary inspiration sources are the AI CLI tools the target users already use daily. These tools define the interaction vocabulary users expect:

- **Streaming output** — Real-time token-by-token display of model thinking. This is the single most trust-building UX pattern in AI CLI tools. Users see the model working, not just waiting for a result. The Orchestrator must preserve this feel in its output panes.
- **Minimal chrome** — The interface is the conversation, not UI furniture around it. No sidebars, no menus, no decorative elements. Content dominates the viewport.
- **Fast startup** — From command to first visible output in seconds. No splash screens, no loading indicators, no preamble. The tool respects the user's time from the first keystroke.
- **Keyboard-native** — Every interaction works without a mouse. Tab completion, arrow keys, keyboard shortcuts. The hands never leave the keyboard.
- **Clear model identification** — Users always know which model they're interacting with. Provider and model name are visible without searching.

## Transferable UX Patterns

**Streaming Output as Trust Mechanism**
- Adopt directly: both TUI panes should stream live model output exactly as Claude/Gemini CLIs do today. The user should feel like they're watching two CLI sessions, not a custom application pretending to show CLI output.
- Do not reformat or normalize provider output — visual differences between Claude and Gemini output help users distinguish which model said what. The difference is a useful signal, not an inconsistency to fix.

**Three-Pane TUI Layout (tmux-native)**
- **Model A pane** (top or left) — Streams the active generative/validation model output
- **Model B pane** (middle or right) — Holds persistent output from the previous step, providing visible context for comparison
- **Command/Status pane** (bottom, thin strip ~5-6 lines) — Status bar, command input, and recent log lines
- The execution model is sequential, not parallel. One pane streams live while the other holds static content from its last completed step. The dual-pane value is **persistent context** — users see what Model A produced while Model B reviews it. This makes the adversarial review relationship visible.
- When a pane is idle, it displays `Waiting for next step` with a subtle breathing dot animation (···) at 1-second intervals to confirm the system is alive without being distracting.
- This three-pane layout naturally extends to Phase 2's four-pane layout by splitting one model pane — no rearchitecting required.

**Minimal Chrome / Content-First**
- Adopt directly: the TUI panes should look and feel like native terminal output. The command/status pane is the only persistent UI element. Everything else is content.

**Command Pane as Familiar Input**
- The command pane should feel like a terminal prompt the user already knows — not a custom input widget. Input routing to the active model should feel like typing in a CLI session.

**Fast Startup Pattern**
- `bmad-orch start` → playbook pre-flight summary → first pane streaming within seconds. Match the startup speed users expect from `claude` or `gemini` commands.

## Anti-Patterns to Avoid

1. **Custom TUI frameworks that don't feel like a terminal** — Tools like some ncurses-heavy applications that replace the terminal's native feel with a pseudo-GUI. The Orchestrator should feel like tmux + CLI sessions, not a terminal application pretending to be a desktop app.

2. **Progress bars for unpredictable durations** — AI model responses have variable length and timing. A progress bar that stalls at 47% for 3 minutes destroys confidence. Streaming output is the progress indicator — if tokens are flowing, progress is happening.

3. **Interruptive notifications** — Tools that steal focus, flash the terminal, or beep on every state change. The escalation ladder (green/yellow/red) handles urgency. No additional notification mechanisms unless the user configures them.

4. **Verbose startup sequences** — Tools that print version info, configuration summaries, dependency checks, and loading messages before doing anything useful. The pre-flight summary is the one allowed startup display — everything else should be silent or in logs.

5. **Hiding or reformatting model output** — Some orchestration tools summarize, filter, or normalize model output. Users of Claude/Gemini CLIs expect to see the raw streaming response. Don't abstract away what the model is actually saying, and don't normalize the visual differences between providers.

6. **Static idle states** — A pane showing a fixed "Waiting..." message for minutes looks frozen. Breathing animations or subtle indicators confirm liveness without demanding attention.

## Design Inspiration Strategy

**What to Adopt Directly:**
- Streaming output display — identical feel to Claude/Gemini CLI output, unmodified per provider
- Keyboard-native interaction — no mouse dependencies
- Minimal chrome — content-first, command/status pane as only persistent UI element
- Fast startup — command to first output in seconds

**What to Extend:**
- Single-pane CLI → three-pane layout (Model A, Model B, Command/Status). Users get the familiar CLI output feel with persistent cross-model context. Sequential execution with visible comparison — "watching two experts work."
- Single-session model identification → multi-model status bar showing which provider is active in which pane, current step, and cycle progress.
- Static idle → breathing dot animation for liveness indication.

**What to Avoid:**
- Custom TUI frameworks that break terminal-native feel
- Progress bars for unpredictable AI operations
- Any output filtering, summarization, or normalization that hides what models are actually producing
- Startup ceremony beyond the pre-flight summary
- Static idle states that look like frozen processes
