# Component Strategy

## Design System Components

**tmux (structural layer) provides:**
- Pane splitting, resizing, and destruction
- Pane border rendering with `pane-border-format` for dynamic headers
- Pane border coloring for escalation states
- Session persistence (detach/reattach — critical for "start and forget")
- Keyboard binding for shortcuts (pause, skip, abort, restart)

**Rich (formatting layer) provides:**
- Styled text output (bold, dim, ANSI color tokens)
- Tables (pre-flight summary, completion reports)
- Horizontal rules (status bar separators)
- Spinners (breathing dots for idle states)
- Progress bars (`▓░` character rendering)
- Columns layout (status bar segment arrangement)

## Custom Components

### 1. Status Bar

**Purpose:** Primary glanceable element — tells the user everything they need to know in one scan.
**Location:** Command pane, line 2 (between Rich horizontal rules)
**Content:** Cycle ID, step progress, active provider, repeat count, progress bar, elapsed time, escalation state
**Format:** `[story 2/5] step 3/4 | claude | cycle 1/2 | ▓▓▓░░ 60% | 12m | ✓ ok`
**States:**
- Nominal: state segment in green (`✓ ok`)
- Attention: state segment in yellow (`⚠ awaiting input`)
- Action: state segment in red + bold (`✗ error`)
- Complete: state segment in green + bold (`✓ complete`)
- Idle: state segment in dim (`· waiting`)
**Responsive:** Truncates segments right-to-left (time → progress → repeat → step) when terminal width < 80 columns
**Implementation:** Rich Columns or formatted string with ANSI tokens

### 2. Pane Header

**Purpose:** Identifies which provider/model is in each pane and its current state.
**Location:** tmux pane border (top edge of each model pane)
**Content:** Provider icon, provider name, model name, step description, state label
**Format:** `─── 🤖 Claude | opus-4 | create story ─── ACTIVE ───`
**States:**
- ACTIVE (bold) — currently streaming output
- Waiting for next step ··· (dim + breathing dots) — idle, awaiting next assignment
- COMPLETE (green) — finished all assigned steps
- ERROR (red + bold) — step failed in this pane
**Implementation:** tmux `pane-border-format` with dynamic title updates via `tmux select-pane -T`

### 3. Pre-Flight Summary

**Purpose:** Confidence checkpoint before execution — catches config mistakes in a 3-second scan.
**Location:** Command pane (full pane, before tmux layout launches)
**Content:** Rich table showing all cycles, steps, providers, models, and prompt templates
**States:**
- First run: displayed and waits for confirmation
- Subsequent runs: displayed briefly (3s auto-dismiss) or skipped with `--no-preflight`
**Implementation:** Rich Table with brand-colored borders

### 4. Command Pane Log

**Purpose:** Rolling context for returning users — "what just happened?" at a glance.
**Location:** Command pane, lines 4-5 (below status bar, above input prompt)
**Content:** 2-3 most recent events with timestamps
**States:**
- Normal events: dim timestamp + normal description
- Error events: dim timestamp + red bold description
- Completion events: dim timestamp + green description
**Behavior:** Rolling buffer — newest at top, oldest drops off. Never scrolls the command pane.
**Implementation:** Rich styled text, managed by a fixed-size deque

### 5. Completion Report

**Purpose:** End-of-run summary — tells the returning user "here's what happened."
**Location:** Command pane (replaces status bar with final report)
**Content:** Cycle counts, story counts, commit counts, push status, timing, error count
**States:**
- Success: green `✓ Complete`, all stats in normal text
- Partial (errors occurred): yellow `⚠ Partial`, error count in red
- First run: adds one milestone line below the stats
**Implementation:** Rich formatted string replacing the live status bar

### 6. Resume Context Screen

**Purpose:** Give the user enough information to choose how to resume without reading logs.
**Location:** Full terminal (before TUI launches)
**Content:** Last run timestamp, failure point, failure reason, completed work summary, numbered options
**States:** Single state — always shows context + options
**Implementation:** Rich styled text, reads from JSON state file

### 7. Init Wizard Prompts

**Purpose:** Conversational config creation — the gateway experience.
**Location:** Full terminal (no tmux)
**Content:** Sequential questions with defaults, provider/model detection results, config summary
**States:**
- Question: prompt with default in brackets
- Detection result: list with recommendations
- Summary: Rich table of generated config
- Error: helpful message with remediation
**Tone:** Conversational, not form-like. Frames limitations as choices.
**Implementation:** Rich styled prompts with Python `input()` for responses

### 8. Error Headline

**Purpose:** One-line error summary in the command pane — severity + what happened + next action.
**Location:** Command pane log area (appears as a log entry)
**Content:** Severity indicator, error description, suggested action
**Format:** `✗ Gemini subprocess terminated (exit 137) — run bmad-orch resume`
**States:**
- Recoverable (logged, execution continues): yellow, no action suggested
- Impactful (execution halted): red + bold, action suggested
**Implementation:** Rich styled text with escalation color

## Component Implementation Strategy

**Rendering Ownership:**
- Components 1, 3, 4, 5, 6, 7, 8 → Rich (formatting layer)
- Component 2 → tmux (structural layer)
- No component spans both layers — clean separation maintained

**Shared State:**
- All components read from the single escalation state object
- Color tokens are consistent across all components (same green/yellow/red everywhere)
- Components never independently decide escalation state — they only render it

**Testing Strategy:**
- Each component is a pure function: state in → formatted string out
- Test against expected ANSI output strings for each state
- Error headlines tested as user-facing copy — clarity and accuracy verified
- Integration test: state transition → all components update atomically

## Implementation Roadmap

**Phase 1 — MVP Core (required for "start and forget"):**
1. Status Bar — the primary glanceable element
2. Pane Header — model identification and state
3. Pre-Flight Summary — config confidence checkpoint
4. Command Pane Log — rolling event context
5. Completion Report — end-of-run summary
6. Init Wizard Prompts — the gateway experience
7. Error Headline — failure communication

**Phase 1 — MVP Supporting:**
8. Resume Context Screen — failure recovery flow

**Phase 1.5 — Headless:**
- All components have headless equivalents (plain text, structured logs)
- No new components — same information, no styling

**Phase 2 — Enhancements:**
- Four-pane layout (split one model pane) — existing components adapt, no new ones
- Richer status display (analytics, history) — extends Status Bar and Completion Report
