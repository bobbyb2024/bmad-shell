# Project Scoping & Phased Development

## MVP Strategy & Philosophy

**MVP Approach:** Problem-solving MVP — deliver the core "kick it off and walk away" experience on a single machine with interactive TUI. Prove the cycle engine, state management, and multi-model validation work reliably. Everything else builds on that foundation.

**Architecture Principle:** Build headless-first with TUI as a presentation layer. The core cycle engine runs without tmux; the TUI observes and controls it. This makes Phase 1.5 (headless/CI) nearly free and keeps the engine fully testable.

**Note:** MCP is not in the orchestrator's scope. Individual CLI tools handle their own MCP configuration. The orchestrator invokes the CLI; the CLI's MCP config handles the rest.

## MVP Feature Set (Phase 1)

**Core User Journeys Supported:** Journey 1 (Solo Developer), Journey 4 (Community User)

**Must-Have Capabilities:**
- Config-driven playbook with per-step prompts, provider assignments, and cycle counts
- Two primary providers (Claude CLI, Gemini CLI) + provider adapter pattern for extensibility
- Configurable adversarial multi-model validation cycles (generative + validation step types)
- State management with resume capability from any failure point
- Per-step log capture with consolidation before commit
- Git integration: commit/push at configurable intervals (per-step, per-cycle, end-of-run)
- tmux-based TUI: two-pane layout (active model output + command/log pane) with status bar
- Command-pane input routing to active model when awaiting response
- Keyboard shortcuts for pause, skip, abort, restart
- Init wizard that queries CLIs for available models
- Graceful single-provider mode with smart defaults
- Configurable pauses between steps/cycles for rate limit management
- Error handling: recoverable → log + continue; impactful → log + commit + push + halt
- `bmad-orch validate`, `bmad-orch status`, and `--dry-run` commands
- Playbook summary on start with proceed/modify prompt
- Resource monitoring with 80% threshold enforcement

## Phase 1.5 (Fast Follow)

- Container/headless mode (`--headless` flag)
- CI/CD pipeline integration with exit code contract
- Retry logic for transient failures (rate limits, timeouts)
- Structured logging for non-interactive environments

## Phase 2 (Growth)

- Four-pane tmux layout (Model A, Model B, Command Pane, Log Pane)
- Direct model pane interaction (focus switching, direct input to models)
- Advanced TUI features (richer status display, run analytics, history)
- Additional provider adapters beyond Claude and Gemini
- Community documentation and getting-started guides
- Community-shareable config templates and example playbooks
- Enhanced init wizard with config validation and recommendations
- `--init --update` for adding providers to existing config

## Phase 3 (Vision)

- Shared playbook marketplace for community-contributed configs
- Config repository/registry for discovering and sharing workflow patterns
- Community contribution workflow for submitting and reviewing playbooks

## Risk Mitigation Strategy

**Technical Risks:** The provider adapter layer is the riskiest component — different CLIs have different invocation patterns, output formats, and error behaviors. Mitigation: build Claude and Gemini adapters first, extract the common interface, then validate that a third adapter fits the pattern before committing to the abstraction.

**Market Risks:** Community adoption depends on the tool working reliably out of the box. Mitigation: Bobby and team dogfood extensively in Phase 1 before any community release. Phase 1.5 (headless/CI) validates automation reliability.

**Resource Risks:** The MVP is scoped for a small team. The headless-first architecture means the core engine can be validated before investing in the TUI presentation layer, providing an early internal milestone (engine-only) before the full MVP.
