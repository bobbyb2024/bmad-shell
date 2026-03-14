# Executive Summary

## Project Vision

The BMAD Orchestrator replaces manual, attention-intensive BMAD workflow execution with an autonomous, config-driven engine that runs multi-model adversarial validation cycles unattended. The UX vision is "trust through transparency" — a tool that earns confidence by showing exactly what it does, intervenes only when it must, and leaves a legible trail of everything that happened. The interaction model spans two modes: an interactive tmux TUI for observation and intervention, and a headless mode for CI/CD pipelines and containers.

## Target Users

1. **Power User (Bobby/Creator)** — Runs BMAD workflows daily. Wants minimal friction, maximum automation. Configures once, tweaks occasionally, trusts the tool to run unattended. Values speed of setup, reliability of execution, and clarity of output.

2. **Team Developer (Sarah)** — Joins projects with existing configs. Needs to understand the playbook, observe execution, and intervene when models ask questions or flag issues. Values config portability, clear intervention signals, and resume from failure.

3. **Community Newcomer (Alex)** — First time automating BMAD. May have only one CLI installed. Needs guided onboarding with smart defaults and progressive complexity disclosure. Values low barrier to entry and a working first run.

4. **CI/CD Pipeline (Non-Human)** — Cares about exit codes, structured logs, and committed artifacts. Needs zero-interaction operation, clear failure signals, and machine-parseable output.

## Key Design Challenges

1. **Two-Mode Cognitive Split** — TUI and headless modes serve fundamentally different interaction models. The TUI must add observability value without distraction; headless output must be self-sufficient without the visual layer.

2. **Intervention Timing in Autonomous Flows** — The tool runs unattended but occasionally needs human input. Intervention points must be unmissable without creating alert fatigue — users must trust they can walk away AND know when to come back.

3. **Init Wizard Complexity Gradient** — Users range from experts who want fast configuration to newcomers who need guided defaults. Progressive disclosure must serve both without forking into separate flows.

4. **State Legibility Across Time** — State files, logs, and git history must tell a coherent story hours or days later. Users returning to failed runs need immediate situational awareness.

## Design Opportunities

1. **Trust Through Transparency** — Live model output and status bar earn user trust incrementally. The emotional arc of usage progresses from anxious watching (first run) to glancing (third run) to confident absence (tenth run). The UX must support all three states simultaneously.

2. **Command Pane as Safety Net** — More than a power interface, the command pane is what makes walking away feel safe. If users don't trust they can intervene cleanly, they'll never leave the terminal.

3. **Resume UX as Differentiator** — Contextual resume choices with enough state context to decide intelligently. The state file must contain human-readable descriptions and timestamps so the resume screen practically writes itself.

4. **Decision-Point Optimization** — Only four moments require user decisions: init wizard configuration, run-start playbook confirmation, mid-run intervention responses, and post-failure resume choices. Everything else is ambient observation. The UX should optimize these four decisional moments and make all other output glanceable.
