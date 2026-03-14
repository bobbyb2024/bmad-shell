# Core User Experience

## Defining Experience

The BMAD Orchestrator's core experience is **confident inaction**. The most frequent user "action" is not interacting — the tool's job is to make doing nothing feel productive. Users start a run and walk away. They come back to completed, committed, multi-model-validated work. The core loop is: configure once, start, walk away, return to results, review briefly, adjust config if needed, repeat.

The critical interaction to get right is the **init wizard** — it's the gateway to everything. If a user can't get from zero to a working config quickly and confidently, nothing else matters. The wizard must feel like a conversation with a knowledgeable colleague, not a config form to fill in. Limitations should be framed as choices ("You have Claude — that's all you need to get started. Add adversarial validation later with init again."), not deficiencies ("Only one provider detected."). BMAD itself handles recovery from failures gracefully, so the orchestrator's job is to stay out of the way during execution and surface only what requires a human decision.

## Platform Strategy

- **Terminal-native**: CLI commands + tmux-based TUI. No web, mobile, or graphical interface.
- **Keyboard-only**: All interactions via keyboard. No mouse dependency.
- **Local-first**: Orchestrates local CLI subprocesses on the user's machine. No network services required beyond what the AI CLIs themselves need.
- **Container/CI-ready**: Headless mode (Phase 1.5) strips the TUI layer, leaving pure subprocess execution with structured logs and exit codes.
- **Offline-capable**: The orchestrator itself has no network dependencies — connectivity requirements come from the underlying AI CLI providers.

## Effortless Interactions

1. **Starting a run** — `bmad-orch start` with an existing config is one command to execution. The playbook summary displays automatically as a pre-flight check — a 3-second scan, not a 30-second read — then execution begins.
2. **Ambient state awareness** — A glance at the TUI or status bar instantly communicates: running, waiting, needs-me, or done. No reading required — color and structure convey state in under one second.
3. **Returning to completed work** — A clear "done" state with a concise summary of what was accomplished, how many cycles ran, and what was committed. The user's re-entry cost is a 5-minute review, not a 30-minute investigation.
4. **Invisible recovery** — Transient failures (rate limits, timeouts, network blips) are handled silently by the orchestrator. Users never see them unless they choose to inspect logs. The system heals itself without surfacing noise.

## Critical Success Moments

1. **"It just worked"** — First-time user completes the init wizard, starts a cycle, walks away, and returns to completed work. This is the defining moment that converts a user into a believer. Everything in the UX serves this moment.
2. **"I can trust this"** — After watching 2-3 runs and seeing the TUI behave predictably — correct status, clean transitions, no surprises — the user stops watching. Trust is earned through observed consistency, not promised reliability.
3. **"That was easy"** — A team member pulls the repo, runs `bmad-orch start`, and the existing config just works. No setup, no init, no questions. Config portability eliminates onboarding friction for teams.

## Experience Principles

1. **Inaction is the product** — The best UX is the one the user never has to think about. Optimize for confident absence, not engaged interaction.
2. **Gateway first** — The init wizard is the highest-priority UX surface. A failed first run kills adoption permanently. Smart defaults, progressive disclosure, conversational tone, and a working config in under 5 minutes.
3. **Glanceable, not readable** — Every surface — status bar, TUI panes, completion summaries, playbook pre-flight checks — must communicate through structure and color, not paragraphs. One-second scan, not one-minute read.
4. **Decisions only when necessary** — Five decision points require user cognition: init wizard configuration, playbook pre-flight confirmation, run-start, mid-run intervention responses, and post-failure resume choices. Everything else is autopilot.
5. **Trust compounds** — Each successful unattended run builds confidence. The UX must never break this compounding effect with false alarms, unclear states, or unnecessary interruptions.
6. **Pre-flight, not speed bump** — The playbook summary is mandatory on first run of a config (catches typos, wrong models, missing variables before burning 30 minutes of API credits). After first successful run, it becomes skippable or auto-dismissing. Frame it as a pilot's checklist — quick, structured, confidence-building.
