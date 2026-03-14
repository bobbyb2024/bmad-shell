# Responsive Design & Accessibility

## Terminal Size Adaptation

The BMAD Orchestrator runs in terminals of varying sizes. Rather than breakpoints at pixel widths, the responsive strategy is about graceful degradation when terminal dimensions shrink.

**Minimum viable dimensions:**

| Mode | Min Columns | Min Rows | Behavior Below Minimum |
|---|---|---|---|
| TUI (3-pane) | 120 | 30 | Falls back to Lite mode with warning |
| Lite (Rich only) | 80 | 24 | Status bar truncates segments right-to-left |
| Headless | N/A | N/A | No terminal dependency |

**TUI Pane Sizing Strategy:**
- Model panes split 50/50 horizontally (or vertically, user-configurable)
- Command pane fixed at 6 rows minimum (status bar + 2 log lines + input prompt + padding)
- Model panes absorb all remaining terminal height
- On terminal resize (SIGWINCH), tmux re-tiles automatically — no custom resize logic needed

**Width Adaptation (Status Bar):**
The status bar is the primary element that must adapt to width. Segments truncate right-to-left as width decreases:

| Width | Displayed Segments |
|---|---|
| 120+ cols | `[story 2/5] step 3/4 | claude | cycle 1/2 | ▓▓▓░░ 60% | 12m | ✓ ok` |
| 100 cols | `[story 2/5] step 3/4 | claude | cycle 1/2 | 60% | ✓ ok` |
| 80 cols | `[story 2/5] step 3/4 | claude | ✓ ok` |
| <80 cols | `step 3/4 | ✓ ok` |

**Pane Header Adaptation:**
Pane headers (tmux `pane-border-format`) truncate the step description first, then the model name, keeping the provider name and state label as the last items removed.

## Operational Mode Degradation

The three-mode architecture (TUI → Lite → Headless) IS the responsive strategy. Rather than adapting a single interface, the tool selects the appropriate mode:

```
Terminal + tmux available → TUI mode (full experience)
Terminal + no tmux       → Lite mode (Rich-formatted single stream)
No terminal (piped/CI)   → Headless mode (structured plain text)
```

**Auto-detection logic:**
1. Check `$TERM` is set and not `dumb` → terminal exists
2. Check `tmux` binary exists and is executable → tmux available
3. Check `$TMUX` is set → already inside tmux (nest or reuse decision)
4. If terminal but no tmux → Lite mode with one-time suggestion: `Install tmux for the full TUI experience`
5. If no terminal → Headless mode automatically

**Mode override:** `--mode tui|lite|headless` flag overrides auto-detection. If TUI is forced but tmux is unavailable, exit with clear error (don't silently fall back).

## Accessibility Strategy

**Target:** The BMAD Orchestrator should be usable by anyone who can operate a terminal. Terminal applications have inherent accessibility characteristics (keyboard-driven, text-based) but also specific challenges.

**Accessibility Principles:**
1. **All information conveyed by color is also conveyed by text** — escalation states use both color AND text symbols (`✓`, `⚠`, `✗`)
2. **All interaction is keyboard-driven** — no mouse dependency anywhere
3. **Screen reader compatibility** — structured text output with clear labels, no decorative characters that confuse screen readers
4. **No reliance on animation** — breathing dots (`···`) for idle state are decorative only; the text label "Waiting" carries the meaning

**Color Accessibility:**

| Concern | Mitigation |
|---|---|
| Red/green color blindness | All states use both color AND symbol: `✓` (green), `⚠` (yellow), `✗` (red). Symbol alone is sufficient. |
| Low contrast terminals | ANSI base 16 colors adapt to the user's terminal theme. Light themes get dark text; dark themes get light text. No hardcoded RGB values. |
| Monochrome terminals | All information is conveyed by text content alone. Colors are enhancement, not information carrier. |
| `NO_COLOR` environment variable | Respected. When set, all ANSI color codes are stripped. Text symbols and labels remain. |

**Keyboard Accessibility:**

| Requirement | Implementation |
|---|---|
| All actions reachable by keyboard | All shortcuts are Ctrl+key combinations. No mouse-only interactions. |
| Focus is always visible | Command pane `> ` prompt is the single focus point. No hidden cursor states. |
| No keyboard traps | `Ctrl+D` always detaches. `Ctrl+C` always interrupts. `q` always quits wizards. |
| Tab order is logical | N/A — single input point (command pane). No tab navigation needed. |

**Screen Reader Considerations:**
- Status bar content is plain text with no box-drawing characters
- Log entries are timestamped lines — natural reading order is correct
- Error messages follow consistent `✗ [what] — [action]` format that reads naturally
- Init wizard prompts are conversational text — screen readers handle them natively
- tmux pane borders and Rich formatting are visual-only; underlying text is accessible

**High Contrast / Theme Compatibility:**
- The tool uses ANSI 16 base colors exclusively — these respect the user's terminal color scheme
- Bold and dim text attributes work across all terminal themes
- No background colors are set (except tmux pane borders, which use terminal defaults)
- Users with custom high-contrast terminal themes get high-contrast BMAD Orchestrator automatically

## Testing Strategy

**Terminal Size Testing:**
- Test TUI at 120x30 (minimum), 160x50 (comfortable), and 80x24 (Lite fallback trigger)
- Verify status bar truncation at 120, 100, 80, and 60 column widths
- Verify pane header truncation at narrow terminal widths
- Test SIGWINCH handling — resize mid-run, verify no rendering corruption

**Mode Degradation Testing:**
- Test auto-detection with tmux present, tmux absent, and no terminal
- Test `--mode` override with mismatched environments (force TUI without tmux → clean error)
- Test Lite mode renders correctly without tmux dependency
- Test headless mode produces valid structured logs with no ANSI escape codes

**Accessibility Testing:**
- Verify all escalation states are distinguishable without color (symbols only)
- Test with `NO_COLOR=1` — all output remains meaningful
- Test with `TERM=dumb` — graceful degradation to headless
- Verify screen reader output for init wizard flow (test with `cat` piping as proxy for screen reader linear reading)
- Test keyboard-only operation — complete full workflow without mouse

**Cross-Terminal Testing:**
- Test on common terminal emulators: iTerm2, Terminal.app, GNOME Terminal, Windows Terminal, Alacritty
- Verify ANSI color rendering across terminals
- Test tmux version compatibility (target tmux 3.0+)

## Implementation Guidelines

**Terminal Size Handling:**
- Query terminal dimensions via `shutil.get_terminal_size()` at startup and on SIGWINCH
- Status bar rendering function accepts width parameter — pure function, easily testable
- Pane header rendering function accepts width parameter — same pattern
- Never assume terminal size — always query and adapt

**Color Output:**
- Check `NO_COLOR` environment variable at startup — if set, disable all ANSI codes
- Check `TERM` value — if `dumb`, disable ANSI codes
- Use Rich's `Console(no_color=...)` for automatic detection in Lite mode
- For TUI mode, tmux handles its own color capability detection
- Never use RGB/256-color codes — ANSI 16 base colors only

**Screen Reader Friendliness:**
- Avoid box-drawing characters (`─`, `│`, `┌`) in Rich output — use simple dashes and pipes
- Keep decorative elements (spinners, progress bars) on lines separate from informational content
- Ensure all Rich Tables have header rows that describe column content
- Log format is naturally screen-reader-friendly: timestamp, severity, context, message
