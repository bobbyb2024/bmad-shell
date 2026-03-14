# UX Consistency Patterns

## Keyboard Shortcuts

**Design Principle:** Shortcuts use familiar terminal conventions. No custom modifier keys. All shortcuts work in the command pane only — model panes are output-only.

**Execution Control Shortcuts:**

| Shortcut | Action | Behavior |
|---|---|---|
| `Ctrl+P` | Pause | Completes current step, then pauses before next step. Status bar shows `⏸ paused`. Resume with `Ctrl+P` again (toggle). |
| `Ctrl+S` | Skip | Skips the current step. Logs skip event. Continues to next step. Confirmation required: "Skip current step? (y/n)" |
| `Ctrl+A` | Abort | Triggers emergency sequence: commit state, push to remote, halt execution. Confirmation required: "Abort run? State will be committed. (y/n)" |
| `Ctrl+R` | Restart step | Restarts the current step from the beginning with the same provider. Confirmation required: "Restart current step? (y/n)" |
| `Ctrl+D` | Detach | Detaches the tmux session (standard tmux behavior). Orchestrator continues running. Reattach with `tmux attach`. |

**Shortcut Rules:**
- Destructive shortcuts (skip, abort, restart) always require a `(y/n)` confirmation
- Non-destructive shortcuts (pause, detach) act immediately with no confirmation
- All shortcuts are displayed in the command pane on first run: `Ctrl+P pause | Ctrl+S skip | Ctrl+A abort | Ctrl+R restart`
- Shortcut hint line is shown once per session, then hidden to save space
- Shortcuts are disabled during the init wizard and resume context screen (no execution to control)

## Input Patterns

**Three input contexts exist, each with consistent behavior:**

### Init Wizard Input
- **Format:** Conversational question + default in brackets: `Which model? [1]:`
- **Default acceptance:** Enter with no input accepts the bracketed default
- **Selection from list:** Numbered options, user types the number
- **Free text:** Rare — only for custom values not in a list
- **Validation:** Immediate inline feedback. Invalid input re-prompts with hint: `Not a valid model. Choose from the list above:`
- **Back navigation:** `b` or `back` returns to the previous question
- **Quit:** `q` or `Ctrl+C` exits the wizard cleanly with no config generated

### Command Pane Input (Mid-Run)
- **Format:** `> ` prompt at the bottom of the command pane
- **Routing:** Input is routed to the active model's subprocess stdin when in yellow (awaiting input) state
- **When green:** Input is queued — if no model is awaiting input, the command pane shows `No active prompt. Input ignored.` in dim text
- **Multi-line:** Not supported in command pane. If a model needs multi-line input, the orchestrator opens `$EDITOR` in a temporary file and pipes the result.
- **Special commands:** Lines starting with `/` are orchestrator commands, not model input:
  - `/status` — show current state summary
  - `/log` — show last 20 log entries
  - `/help` — show available commands and shortcuts

### Resume Choice Input
- **Format:** Numbered options: `Choice [1]:`
- **Default:** First option (re-run failed step) is the default
- **Validation:** Invalid numbers re-prompt: `Choose 1-4:`
- **No free text** — only numbered selections

## Feedback Patterns

**All feedback follows the escalation ladder and uses consistent formatting across modes:**

### State Transitions
Every state transition follows the same three-part communication pattern:
1. **Visual indicator** — Color change (pane border in TUI, severity tag in headless)
2. **Status update** — One-line summary in status bar / structured log
3. **Log entry** — Timestamped event in command pane log / log file

**Transition Examples:**

| Event | Visual | Status | Log |
|---|---|---|---|
| Step starts | Active pane border brightens | Provider name updates | `[14:23:01] Step 3 started: create story via Claude` |
| Step completes | No change (stays green) | Step counter increments | `[14:25:30] Step 3 complete: story created` |
| Model asks question | Pane border → yellow | `⚠ awaiting input` | `[14:26:01] ⚠ Claude asks: "Include timeout ACs?"` |
| User responds | Pane border → green | Status returns to normal | `[14:26:15] User responded to Claude prompt` |
| Transient error | No visual change | No status change | `[14:27:00] Retry 1/3: Gemini rate limit (429)` |
| Impactful error | Pane border → red | `✗ error` in red | `[14:28:00] ✗ Gemini subprocess terminated` |
| Cycle complete | No special indicator | Cycle counter increments | `[14:30:00] Story cycle 1/2 complete` |
| Run complete | Both borders → green | `✓ complete` | `[14:45:00] ✓ Run complete: 5 stories, 12 commits` |

### Progress Communication
- **During step execution:** Streaming model output IS the progress indicator. No additional progress bar for individual steps.
- **Across steps:** Status bar step counter (`step 3/4`) shows progression.
- **Across cycles:** Status bar cycle counter (`cycle 1/2`) shows repetition progress.
- **Overall run:** Status bar progress bar (`▓▓▓░░ 60%`) shows percentage of total steps completed across all cycles.

## State Communication Patterns

**Consistent across all three operational modes:**

| Information | TUI Mode | Lite Mode | Headless Mode |
|---|---|---|---|
| Current step | Status bar + pane header | Rich status line | Structured log entry |
| Active provider | Status bar (brand color) + pane header | Rich status line | Log tag `[provider/model]` |
| Escalation state | Pane border color + status bar | Rich colored status | Log severity `[WARN]`/`[ERROR]` |
| Step completion | Log entry in command pane | Inline Rich text | Structured log entry |
| Error detail | Headline in command pane | Inline Rich text | stderr output |
| Full error context | Log file | Log file | Log file |
| Run completion | Completion Report component | Rich summary | stdout summary + exit code |
| Audit trail | JSON state file | JSON state file | JSON state file |

**The state file is always the source of truth.** All three modes read from and write to the same state file format. A run started in any mode can be resumed in any other mode.

## Error Patterns

**Error Classification:**

| Category | Severity | Visual | Behavior |
|---|---|---|---|
| Transient (rate limit, timeout, network blip) | Recoverable | No visual change | Retry per config. Log only. User never sees it unless checking logs. |
| Provider failure (crash, OOM, unexpected exit) | Impactful | Red border + red status | Emergency commit + push. Halt. Show headline + next action. |
| Config error (bad model, missing variable, schema violation) | Blocking | N/A (pre-execution) | Clear error message with specific fix. Exit with code 2. |
| Resource violation (CPU/memory threshold exceeded) | Impactful | Red border + red status | Kill subprocess. Emergency commit + push. Halt. |
| User abort (Ctrl+A) | Intentional | N/A | Commit state + push. Clean exit. |

**Error Message Format (consistent across all error types):**
```
✗ [What happened] — [What to do next]
```

**Examples:**
- `✗ Gemini subprocess terminated (exit 137) — run bmad-orch resume`
- `✗ Config error: model 'opus-5' not found for provider 'claude' — check bmad-orch.yaml`
- `✗ Memory threshold exceeded (85%) — subprocess killed, state saved`

**Error Rules:**
- Every error has a "what to do next" — no error message ends without guidance
- Transient errors are invisible to the user unless they inspect logs
- Impactful errors always commit state before halting — work is never lost
- Error messages use the same vocabulary as the rest of the tool (provider names, step descriptions, config file names)

## Confirmation Patterns

**When confirmations are required:**

| Action | Confirmation? | Format | Reason |
|---|---|---|---|
| Start run (first time with config) | Yes | Pre-flight summary + Enter | Catches config mistakes |
| Start run (subsequent) | No | Auto-dismiss after 3s | Trust is earned |
| Skip step (Ctrl+S) | Yes | `Skip current step? (y/n)` | Destructive — skips work |
| Abort run (Ctrl+A) | Yes | `Abort run? State will be committed. (y/n)` | Destructive — halts execution |
| Restart step (Ctrl+R) | Yes | `Restart current step? (y/n)` | Destructive — discards current step progress |
| Pause (Ctrl+P) | No | Immediate toggle | Non-destructive |
| Resume choice | Yes | Numbered selection | Decision point — user must choose path |
| Init wizard overwrite | Yes | `Config exists. Overwrite? (y/n)` | Destructive — replaces config |

**Confirmation Rules:**
- Destructive actions always confirm. Non-destructive actions never confirm.
- Confirmations default to the safe option (e.g., `(y/N)` for abort — default is don't abort)
- Confirmations are single-keystroke: `y` or `n`, no Enter required
- Confirmations timeout after 30 seconds to the safe default (except resume choices, which wait indefinitely)
