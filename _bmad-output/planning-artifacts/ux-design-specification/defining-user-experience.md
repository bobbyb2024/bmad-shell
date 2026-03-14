# Defining User Experience

## Defining Experience

**"Start and forget."**

The BMAD Orchestrator's defining experience is the moment a user types `bmad-orch start`, walks away from their terminal, and returns to completed, committed, multi-model-validated work. Everything in the UX exists to make this moment reliable, trustworthy, and repeatable.

This is the dishwasher model: load the config (once), press start, walk away, come back to clean results. Users don't describe the wash cycle to their friends — they describe the freedom. "I kicked off a full story cycle before lunch and came back to everything done." That's the sentence the UX must earn.

Multi-model adversarial validation and the dual-pane TUI are trust mechanisms that support "start and forget" — they're how users build confidence to walk away, not the experience itself. The TUI is training wheels that become unnecessary. The validation is quality assurance that runs invisibly.

## User Mental Model

**Current state (manual execution):**
Users currently run BMAD workflows by hand — invoking Claude CLI, copying output, switching to Gemini for review, pasting context, committing results, repeating for each step. It works, but it's hand-washing every dish individually. Every step requires active attention and manual transitions.

**Mental models users bring:**
- **Build systems** — `make build` or `npm run build`: kick off a command, wait for it to finish, check the result. Users already understand "run and wait."
- **CI/CD pipelines** — GitHub Actions, Jenkins: trigger a workflow, walk away, check the green/red status later. Users already understand "fire and forget with status checks."
- **tmux sessions** — Detach from a session, do other work, reattach later. Users already understand persistent terminal processes that outlive their attention.

**The novel element:**
Trusting an AI orchestration loop to produce quality output unattended. This is the gap between "I ran a build" and "I let two AI models create and review my code without me." The multi-model validation cycle exists to close this trust gap — it's the mechanism that makes "start and forget" feel safe rather than reckless.

**User workarounds today:**
- Running AI CLIs in tmux panes manually and switching between them
- Keeping notes on which step they're on and which model ran what
- Manually copying output between models for cross-review
- Committing in batches and hoping they don't lose work to a crash

## Success Criteria

1. **Physical departure** — User starts a run and physically leaves the terminal with confidence. Not "I'll check back in 5 minutes" — actual departure.
2. **Unambiguous return** — User returns to a clear terminal state: completed (green, summary visible), failed (red, headline visible), or in-progress (streaming, status bar updating). Never ambiguous, never mid-transition.
3. **Review-ready output** — Completed work is ready for a brief human review (5 minutes), not a debugging or reformatting session. Artifacts are committed, logs are consolidated, state is clean.
4. **Self-explanatory failure** — If something failed, the failure state tells the user what happened and what to do next without consulting logs. The resume flow presents clear options with enough context to decide.
5. **Repeatable confidence** — Each successful "start and forget" cycle increases the user's willingness to walk away earlier and stay away longer. By the tenth run, starting the orchestrator is as thoughtless as starting a dishwasher.

## Novel UX Patterns

**Pattern type: Established patterns combined in a novel context.**

The individual interaction patterns are all familiar:
- CLI command execution (established)
- tmux pane layout (established)
- Status bars and progress indication (established)
- Streaming terminal output (established)

The novelty is the **trust architecture** — the combination of patterns that lets users trust autonomous AI workflow execution:
- Dual-pane persistent context (watch Model A's output while Model B reviews it)
- Escalation ladder (green/yellow/red) across pane borders and status bar
- Pre-flight summary as a confidence checkpoint
- Resume flow with contextual state information

No new interaction paradigms need to be taught. The innovation is in how established patterns combine to create trust for a new category of tool. Users need zero UX education — they need confidence that the familiar patterns are reliable.

## Experience Mechanics

**1. Initiation:**
- User types `bmad-orch start` (or `bmad-orch start --config path`)
- Orchestrator loads config, detects providers, validates
- Pre-flight summary displays in Rich table format (3-second scan)
- User confirms or the summary auto-dismisses (after first successful run with this config)
- tmux layout launches: three panes appear, first model begins streaming

**2. Interaction (active observation — optional):**
- Model A pane streams generative output (e.g., story creation via Claude)
- Model B pane shows "Waiting for next step ···"
- Status bar shows: `[story 1/5] step 1/4 | claude | cycle 1/2 | ▓░░░░ 20% | 3m elapsed | ✓ ok`
- Pane borders glow green — all nominal
- User watches, builds confidence, eventually walks away
- If model asks a question: pane border turns yellow, status bar shows "Model awaiting input", command pane highlights the question. User responds via command pane or — if away — the orchestrator handles the timeout gracefully per config.

**3. Feedback (ambient — no interaction required):**
- Status bar continuously updates with step/cycle progress
- Pane borders maintain escalation color state
- Completed steps are logged, state file updated atomically
- Transient errors (rate limits, timeouts) handled invisibly with retry
- Impactful errors: pane border turns red, status bar shows headline, state committed

**4. Completion:**
- All cycles complete. Status bar shows final summary: `✓ Complete | 5 stories | 12 commits | 47m | 0 errors`
- First run only: one additional line — "First automated run complete."
- Model panes show final output from last steps
- Git commits and push completed per config
- State file records complete run history
- User returns, scans the summary, reviews artifacts — 5-minute human checkpoint
