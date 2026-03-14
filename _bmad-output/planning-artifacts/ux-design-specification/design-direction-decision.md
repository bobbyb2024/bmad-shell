# Design Direction Decision

## Design Directions Explored

Three terminal-native design directions were evaluated, each showing the same mid-run state (story cycle, step 3, Claude active, Gemini waiting):

**Direction A: Ultra-Minimal** — tmux borders do all structural work, status bar compressed to one line, command pane is just a prompt. Maximum content, minimum chrome. Feels like raw tmux with smart borders.

**Direction B: Structured Status** — Status bar gets its own bordered Rich section, recent log lines visible below, more information density in the command pane. Feels like a well-configured monitoring tool.

**Direction C: Clean Separation** — Full box-drawing borders create a cohesive framed application. Strongest visual identity but adds border chrome that competes with tmux's native pane borders.

## Chosen Direction

**Direction B: Structured Status**

The chosen direction features:
- tmux pane borders with dynamic headers for model identification (Layer 1)
- A Rich-formatted command pane with a visually distinct status bar section, recent log lines, and input prompt (Layer 2)
- Raw, unmodified model output in both model panes (Layer 3)

**Reference Layout:**
```
─── 🤖 Claude | opus-4 | create story ─────────────────── ACTIVE ───

[raw model streaming output]

─── 🤖 Gemini | 2.5-pro ──────────────── Waiting for next step ··· ───

[previous step output / idle state]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 story 1/3 │ step 3/4 │ claude │ cycle 1/2 │ ▓▓▓░░ 60% │ 12m │ ✓ ok
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 [14:23:01] Step 3 started: create story 2.3 via Claude
 [14:22:45] Step 2 complete: adversarial review passed (Gemini)
> _
```

## Design Rationale

1. **Best "glance and know" support** — The structured status section with Rich formatting creates a visually distinct zone that the eye finds immediately. Users returning to the terminal don't scan the model output — they scan the status bar. Direction B makes this scan instant.

2. **Log lines provide context without log files** — The 2-3 recent log lines below the status bar give returning users immediate context: "what just happened?" without opening a log file. This directly supports the "self-explanatory failure" success criterion.

3. **Model panes stay clean** — Unlike Direction C's box-drawing borders, Direction B uses tmux's native pane borders for model separation. Model output remains raw and unframed — exactly as the CLI produces it.

4. **Monitoring tool mental model** — Direction B feels like htop or a well-configured tmux status bar — tools terminal users already know and trust. It doesn't try to be an application; it tries to be a smart terminal layout.

5. **Information density matches emotional design** — The command pane is dense (every line has a purpose), the model panes are sparse (raw output with natural whitespace). This contrast naturally draws the eye to the command pane for status and to the model panes for content — exactly the right attention split.

## Implementation Approach

**Command Pane Structure (Rich-formatted, ~5-6 lines):**
```
Line 1: ━━━ Rich horizontal rule (visual separator from model panes)
Line 2: Status bar segments: cycle | step | provider | repeat | progress | time | state
Line 3: ━━━ Rich horizontal rule
Line 4: Recent log entry (most recent)
Line 5: Recent log entry (previous)
Line 6: > [input prompt]
```

**Status Bar Rendering:**
- Rich `Table` or `Columns` layout with `│` segment separators
- Provider name in brand color (blue) + bold
- State indicator in escalation color (green/yellow/red)
- Progress bar using Rich's bar rendering (`▓░` characters)
- Time and secondary metrics in dim

**Log Line Rendering:**
- Timestamp in dim: `[14:23:01]`
- Event description in normal: `Step 3 started: create story 2.3 via Claude`
- Rolling buffer — newest at top, oldest drops off as new events arrive
- Error events rendered in escalation color with bold

**Pane Header Rendering (tmux `pane-border-format`):**
- Format: `─── [icon] Provider | model | step description ─── STATE ───`
- STATE values: `ACTIVE` (bold), `Waiting for next step ···` (dim + breathing dots), `COMPLETE` (green), `ERROR` (red + bold)
- Border color matches escalation state

**Escalation Visual States:**

| State | Pane Border | Status Bar State | Log Line Style |
|---|---|---|---|
| Nominal | Green border | `✓ ok` in green | Normal text |
| Attention | Yellow border | `⚠ awaiting input` in yellow | Yellow highlight |
| Action | Red border | `✗ error` in red + bold | Red + bold |
| Complete | Green border | `✓ complete` in green + bold | Green text |
| Idle | Default border | `· waiting` in dim | Dim text |
