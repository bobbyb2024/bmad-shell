# Desired Emotional Response

## Primary Emotional Goals

1. **Relief** — "I don't have to babysit this." The dominant emotion is liberation from attention-intensive manual workflow execution. Users should feel their time and cognitive load have been genuinely returned to them.
2. **Confidence** — "It told me exactly what happened." When the system encounters issues, users should feel informed and in control, never blindsided. Transparency in failure builds more trust than flawless execution.
3. **Satisfaction** — "It just keeps going and getting it done." The quiet pride of watching loops complete, stories accumulate, and commits land. Not flashy excitement — the deep satisfaction of a system that reliably produces results.

## Emotional Journey Mapping

| Stage | Desired Emotion | Anti-Emotion to Avoid |
|---|---|---|
| **Discovery/Install** | Curiosity, low-stakes interest | Overwhelm, skepticism |
| **Init Wizard** | Guided confidence — "this knows what it's doing" | Confusion, decision paralysis |
| **First Run (watching)** | Fascinated observation — "oh, it's actually doing it" | Anxiety, distrust |
| **First Run (walking away)** | Cautious relief — "I think I can leave" | Fear of missing something |
| **Returning to completed work** | Satisfied surprise — "it actually finished everything" | Dread of checking what went wrong |
| **First completed run** | Milestone recognition — understated "first automated run complete" acknowledgment | Emotional flatness on a meaningful moment |
| **Subsequent runs** | Invisible confidence — "of course it worked" | Complacency masking fragility |
| **Failure/error** | Informed calm — "I know exactly what happened" | Panic, blame, confusion |
| **Resume after failure** | Controlled recovery — "I can fix this in 30 seconds" | Helplessness, starting-over dread |

## Micro-Emotions

- **Confidence over confusion** — Every surface (status bar, logs, state file, resume screen) must reinforce "you know what's happening." Ambiguity is the enemy.
- **Trust over skepticism** — Earned incrementally through observed consistency. Never demanded through messaging ("trust us!"). The TUI's live output is the trust-building mechanism.
- **Accomplishment over frustration** — Completed cycles should feel like *the user* accomplished something, not just the tool. The work product is theirs; the orchestrator is invisible infrastructure.
- **Calm over anxiety** — Error handling must feel measured and professional. The TUI shows a one-line headline; the log file contains full diagnostic depth. Error density in the interface kills calm — keep it to headlines, not walls of text.

## Design Implications

- **Relief** → Minimize required interaction. Every prompt, confirmation, or input request that isn't strictly necessary erodes the core emotional promise. Default aggressively.
- **Confidence** → Error messages are a first-class UX surface. Headline in the status bar (what happened), full context in the log file (what the system tried, what the user can do next). Error UX quality is a testable requirement — every error template should be reviewed for clarity like user-facing copy.
- **Satisfaction** → Completion summaries should celebrate throughput quietly. "3 stories completed, 12 commits pushed, 0 interventions required." Let the numbers speak. Exception: the very first completed run gets one understated milestone line — after that, pure numbers.
- **Informed calm** → The escalation ladder governs both urgency AND information density:
  - **Green** = minimal info (progress indicator only — "your attention is not needed")
  - **Yellow** = one-line context ("Model awaiting input" — "glance when convenient")
  - **Red** = headline + action ("Gemini timeout — resume options available" — "look now, here's why")

## Emotional Design Principles

1. **Disappearing tool** — The highest emotional compliment is "I forgot it was running." Design every interaction to get out of the way faster. This tool's emotional model is a reliable car, not a shiny gadget.
2. **Failure is a feature** — How the tool handles failure defines more trust than how it handles success. Graceful, informative, recoverable failure is emotionally superior to fragile perfection. Error paths deserve first-class testing — error message quality is a functional requirement.
3. **Numbers over narratives** — Completion stats, cycle counts, and timing data create quiet satisfaction without demanding attention. "5 cycles, 0 errors, 47 minutes" is more emotionally satisfying than "Great job! Everything worked!"
4. **Emotional escalation ladder** — Green (ignore me, minimal info) → Yellow (glance when convenient, one-line context) → Red (look now, headline + action). Never jump from green to panic. The ladder preserves calm and controls information density simultaneously.
5. **No performative enthusiasm** — No celebration banners, no congratulatory messages, no emoji fireworks. The tool's tone is professional, understated, results-oriented. One exception: the first-ever completed run gets a single understated milestone acknowledgment. After that, the output speaks for itself.
