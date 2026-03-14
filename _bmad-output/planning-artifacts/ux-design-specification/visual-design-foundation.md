# Visual Design Foundation

## Color System

**Philosophy: Terminal-native with a whisper of brand identity.**

The orchestrator inherits the user's terminal theme as its base — no forced backgrounds, no overridden foregrounds. Color is used sparingly and semantically, never decoratively. The only deliberate color choices are the escalation states and a single subtle brand accent.

**Semantic Color Tokens:**

| Token | ANSI Mapping | Purpose |
|---|---|---|
| `brand` | Blue (ANSI 4 / bright blue) | BMAD identity — pane header provider labels, startup banner, pre-flight table borders. Used sparingly as the one recognizable accent. |
| `ok` | Green (ANSI 2) | Nominal state — pane borders when running normally, success indicators, completion stats |
| `attention` | Yellow (ANSI 3) | Needs glance — model awaiting input, non-critical warnings, approaching thresholds |
| `action` | Red (ANSI 1) | Needs now — errors, impactful failures, halted execution |
| `content` | Terminal default foreground | All model output, primary text — inherits user's theme |
| `secondary` | Dim (ANSI dim attribute) | Timestamps, elapsed time, secondary status segments, idle indicators |
| `emphasis` | Bold (ANSI bold attribute) | Active provider names, current step, important status values |

**Color Rules:**
- Maximum of 2 colors visible at any time in the status bar (brand accent + one escalation state)
- Model output panes: ZERO orchestrator-applied color — content streams in whatever the AI CLI produces
- Pane borders: one color at a time (escalation state)
- When in doubt, use dim over color. Color means something; dim means "less important."
- No background colors applied by the orchestrator — ever. Background is always the user's terminal default.

**ANSI Compatibility:**
- All color tokens map to base ANSI 16 colors for maximum terminal compatibility
- Rich handles the mapping — if a terminal supports 256 or truecolor, Rich can enhance automatically
- Colorblind consideration: green/yellow/red is supplemented by the status text itself (ok/attention/action) — color is never the sole signal

## Typography System

**Terminal typography is constrained to the user's monospace font.** The orchestrator does not choose typefaces. Instead, it uses ANSI text attributes as its typographic system:

**Text Hierarchy:**

| Level | Attributes | Usage |
|---|---|---|
| **Header** | Bold + brand color | Pane header labels, pre-flight table title, section headers in completion reports |
| **Active** | Bold | Current provider name, active step description, important values |
| **Normal** | Default | Status bar segments, log entries, general text |
| **Secondary** | Dim | Timestamps, elapsed time, cycle counts when not the focus, breathing dots |
| **Alert** | Bold + escalation color | Error headlines, intervention prompts, status warnings |

**Text Rules:**
- Bold means "look at this." Use it for the one thing per line that matters most.
- Dim means "this is here if you need it." Timestamps, secondary counters, separators.
- No underline (too visually heavy in terminals, often confused with links).
- No inverse/reverse video (used by terminal selection, don't compete with it).
- No blinking text — ever.

## Spacing & Layout Foundation

**Spacing unit: 1 character width / 1 line height.** All spacing is character-based.

**Pane Layout Proportions (TUI mode):**
```
┌─────────────────────────────────────┐
│ Model A pane          (~40% height) │
│ [provider header in pane border]    │
│                                     │
├─────────────────────────────────────┤
│ Model B pane          (~40% height) │
│ [provider header in pane border]    │
│                                     │
├─────────────────────────────────────┤
│ Command/Status pane   (~20% / 5-6 lines) │
│ [status bar] [input] [recent log]   │
└─────────────────────────────────────┘
```

**Status Bar Layout (left-to-right priority):**
```
[story 2/5] step 3/4 | claude | cycle 1/2 | ▓▓▓░░ 60% | 12m | ✓ ok
 ^^^^^^^^^  ^^^^^^^^   ^^^^^^   ^^^^^^^^^   ^^^^^^^^^   ^^^   ^^^^
 cycle id   step       provider  repeat     progress   time  state
 (bold)     (normal)   (brand+   (normal)   (dim)      (dim) (escalation
                        bold)                                  color)
```

**Spacing Rules:**
- Status bar segments separated by ` | ` (space-pipe-space) — 3 characters between segments
- No segment padding beyond the pipe separator
- If terminal width is too narrow, truncate from right (drop least-important segments first: time, progress, repeat count)
- Pane headers: 1 space padding on each side of the header text within the tmux border
- No decorative borders, boxes, or frames beyond tmux's native pane borders

**Information Density:**
- Command pane: dense — every line has a purpose (status bar, input line, 3-4 recent log lines)
- Model panes: sparse — raw model output with natural whitespace as the model produces it
- Pre-flight summary: medium — Rich table with compact padding, scannable in 3 seconds

## Accessibility Considerations

**Color Accessibility:**
- All escalation states (ok/attention/action) are communicated through both color AND text labels — color is never the sole signal
- ANSI base 16 colors are universally supported and render distinctly in both light and dark terminal themes
- No red/green distinction without accompanying text (yellow serves as the middle state, breaking the red-green binary)

**Terminal Compatibility:**
- All visual elements degrade gracefully: truecolor → 256 color → 16 color → monochrome (bold/dim only)
- Rich handles automatic color downgrade based on terminal capability detection
- Headless mode produces zero ANSI codes — plain text with severity tags

**Readability:**
- Bold used sparingly — maximum one bold element per status bar segment
- Dim used for de-emphasis, never for critical information
- No dense color combinations — maximum 2 colors per visual line
- Status bar is readable at 80 columns minimum; graceful truncation below that
