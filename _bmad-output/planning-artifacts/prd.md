---
stepsCompleted: [step-01-init, step-02-discovery, step-02b-vision, step-02c-executive-summary, step-03-success, step-04-journeys, step-05-domain, step-06-innovation, step-07-project-type, step-08-scoping, step-09-functional, step-10-nonfunctional, step-11-polish, step-12-complete]
inputDocuments: []
documentCounts:
  briefs: 0
  research: 0
  brainstorming: 0
  projectDocs: 0
workflowType: 'prd'
classification:
  projectType: CLI Tool + TUI (tmux-based orchestrator)
  domain: Developer Tooling / AI Workflow Automation
  complexity: medium
  projectContext: greenfield
---

# Product Requirements Document - BMAD Orchestrator

**Author:** Bobby
**Date:** 2026-03-13

## Executive Summary

The BMAD Orchestrator is an autonomous workflow execution engine that programmatically drives BMAD development cycles across multiple AI CLI platforms. It solves a concrete problem: running BMAD's structured workflows — from story creation through code review — manually across different AI models is slow, error-prone, and leaves no audit trail. The Orchestrator replaces that manual process with a config-driven playbook that executes unattended, validates adversarially across models, and commits results to git with full traceability.

The target user starts as the creator (Bobby) and team, expanding to the broader BMAD community. The tool operates in two modes: an interactive tmux-based TUI for observation and intervention, and a headless mode for fully autonomous operation in containers or CI environments. The primary value proposition is "kick it off and walk away" — return to completed, multi-model-validated, committed work you can trust.

### What Makes This Special

The Orchestrator introduces **adversarial multi-model validation cycles** — configurable rounds where different AI platforms (Claude, Gemini) independently review the same artifacts. This exploits different model failure modes to produce higher-confidence output. The config-driven playbook architecture means every prompt, provider assignment, and cycle count is explicit, auditable, and tunable without touching code. The tmux TUI with a dedicated command pane lets users observe, intervene, or walk away — earning trust through transparency rather than demanding it.

## Project Classification

- **Project Type:** CLI Tool + TUI (Python, tmux-based orchestrator)
- **Domain:** Developer Tooling / AI Workflow Automation
- **Complexity:** Medium — multi-process orchestration, state management, dual-mode operation, and cross-platform CLI invocation create real engineering surface area
- **Project Context:** Greenfield — standalone tool, potential future integration into the BMAD ecosystem

## Success Criteria

### User Success

- A user configures a playbook and runs a full story cycle (create → review → ATDD → dev → code review) without intervening. They return to completed, committed, multi-model-validated artifacts ready for a 5-minute human review.
- The init wizard gets a new user from zero to a working config in under 5 minutes, querying available models from their installed CLIs.
- A user reads the state file or git log and can reconstruct exactly what happened, which model ran which step, and what the outcome was.

### Business Success

- Bobby and team use it daily as the standard way to run BMAD automated cycles.
- Community adoption measured by active users — target number TBD but tracked as primary growth metric.
- The tool becomes the recognized standard for automated BMAD workflow execution.

### Technical Success

- Runs 10+ story cycles without requiring human intervention (excluding genuine content decisions).
- Recovers gracefully from rate limit errors, transient CLI failures, and network interruptions.
- State file is always consistent — a crash at any point allows clean resume from last completed step.
- Logs are comprehensive enough to diagnose any failure without reproducing it.

### Measurable Outcomes

- **Attention reclaimed:** A full story cycle requires ≤5 minutes of human review time instead of 2+ hours of active participation.
- **Reliability:** <5% of runs require human intervention for non-content reasons (errors, crashes, state corruption).
- **Onboarding:** New user from install to first successful automated run in <15 minutes.

## User Journeys

### Journey 1: Solo Developer — First Run Success Path

*Meet Bobby. He's been running BMAD workflows manually — invoking Claude, copying output, switching to Gemini for a second opinion, committing results, repeating. It works, but it eats his afternoon.*

**Opening Scene:** Bobby installs the orchestrator and runs `bmad-orch --init`. The wizard detects his installed CLIs, queries available models, and walks him through provider setup and cycle configuration. He accepts most defaults, tweaks the story review cycle to 2 rounds, and gets a `config.yaml` in under 5 minutes.

**Rising Action:** He runs `bmad-orch start`. tmux splits into two panes — the active model's output on top and the command/log pane with status bar below. He watches Claude create the first story. The output pane switches to show Gemini when it runs adversarial review. The status bar ticks through each step. He glances at it, sees everything green, and goes to lunch.

**Climax:** He comes back to a terminal showing `✓ Story cycle complete — 3 stories specced, reviewed, ATDD tests generated, code implemented, code reviewed. 12 commits pushed.` The state file shows every step, every model, every outcome. The git log reads like a clean audit trail.

**Resolution:** Bobby opens the first story file. It's solid. He spends 5 minutes reviewing, finds one thing he'd tweak in the prompt config for next time. He edits `config.yaml`, kicks off another run, and gets back to the work that actually needs his brain.

*Requirements revealed: init wizard, config generation, tmux TUI, status bar, state management, log capture, git integration, resume capability.*

### Journey 2: Team Developer — Joining an Existing Project

*Meet Sarah. She's on Bobby's team. Bobby already set up the orchestrator config for the project. She needs to run the next sprint's story cycle.*

**Opening Scene:** Sarah pulls the repo. The `config.yaml` is already there. She runs `bmad-orch start` and the orchestrator detects the existing config, shows her the playbook summary, and asks if she wants to proceed or modify.

**Rising Action:** She proceeds. The tmux TUI launches. Midway through, Gemini's adversarial review flags a concern and asks a clarifying question. The command pane highlights it — `⚠ Active model awaiting input`. Sarah types her response in the command pane, which routes it to the active model. The run continues.

**Climax:** The run completes. Sarah notices one story's code review requested changes. The orchestrator logged the failure, committed the partial work, and marked the state file with exactly where it stopped and why.

**Resolution:** Sarah adjusts the story based on the review feedback, then runs `bmad-orch resume`. It picks up from the last completed step and finishes the cycle cleanly.

*Requirements revealed: config portability, playbook summary on start, command-pane input routing, error-triggered partial commit, resume from failure.*

### Journey 3: CI/CD Pipeline — Headless Automation

*The pipeline isn't a person. It doesn't care about tmux. It cares about exit codes, logs, and committed artifacts.*

**Opening Scene:** A merge to `develop` triggers a GitHub Actions workflow. The workflow runs `bmad-orch start --headless --config ./orchestrator-config.yaml`. No TUI, no panes — pure subprocess execution with structured log output.

**Rising Action:** The orchestrator executes the playbook sequentially. Each step writes to a structured log file. State updates after every step. Rate limit pauses fire between cycles. A transient API timeout hits during Gemini's review — the orchestrator catches it, logs a warning, waits, retries, and continues.

**Climax:** The full cycle completes. Exit code 0. Logs consolidated into a single file. All artifacts committed and pushed. The pipeline step passes green.

**Resolution:** If something had gone wrong — an impactful error — the orchestrator would have logged the failure, committed the partial state, pushed to the repo, and exited with a non-zero code. The pipeline would fail visibly, and the team would find the exact failure point in the state file and logs.

*Requirements revealed: headless mode, --headless flag, structured logging, exit codes, retry logic for transient errors, non-zero exit on impactful failure, CI/CD integration contract.*

### Journey 4: Community User — First-Time Setup

*Meet Alex. They found BMAD Orchestrator through the BMAD community. They've used BMAD manually but never automated it. They have Claude CLI installed but not Gemini.*

**Opening Scene:** Alex installs the orchestrator and runs `bmad-orch --init`. The wizard detects Claude CLI but not Gemini. It informs Alex: "Only one provider detected. You can run single-model cycles, or install a second provider for adversarial validation." Alex proceeds with Claude only for now.

**Rising Action:** The wizard asks about cycle configuration. Alex doesn't know what to pick. The wizard offers sensible defaults: "Recommended: 1 story creation, 2 review cycles. Accept defaults? [Y/n]". Alex hits enter. Config generated.

**Climax:** Alex runs their first cycle. It works. Single-model, no adversarial validation, but the automation alone saves them significant time. They later install Gemini CLI, run `bmad-orch --init --update`, and the wizard detects the new provider and offers to add adversarial validation cycles.

**Resolution:** Alex is now running multi-model cycles. They share their config with the community Discord. Someone else picks it up and runs it on their project.

*Requirements revealed: graceful single-provider mode, smart defaults, init --update for adding providers, provider detection, progressive disclosure of complexity.*

### Journey Requirements Summary

| Capability | J1 | J2 | J3 | J4 |
|---|---|---|---|---|
| Init wizard with CLI detection | ✓ | | | ✓ |
| Config-driven playbook | ✓ | ✓ | ✓ | ✓ |
| tmux TUI (2-pane layout + status bar) | ✓ | ✓ | | |
| Headless mode | | | ✓ | |
| Command-pane input routing to active model | | ✓ | | |
| Playbook summary on start | | ✓ | | |
| State management + resume | ✓ | ✓ | ✓ | ✓ |
| Git commit/push integration | ✓ | ✓ | ✓ | ✓ |
| Log capture + consolidation | ✓ | ✓ | ✓ | ✓ |
| Error handling (recoverable/impactful) | | ✓ | ✓ | |
| Retry logic for transient failures | | | ✓ | |
| CI/CD exit code contract | | | ✓ | |
| Single-provider graceful mode | | | | ✓ |
| Init --update for adding providers | | | | ✓ |
| Smart defaults for new users | | | | ✓ |

## CLI Tool Specific Requirements

### Project-Type Overview

The BMAD Orchestrator is a dual-mode CLI tool: interactive (tmux TUI) and scriptable (headless). It follows CLI conventions for discoverability, composability, and automation-friendliness. The command structure is shallow and verb-based. Configuration uses convention-based file discovery with explicit flag override.

### Command Structure

```
bmad-orch --init                          # Config wizard (interactive)
bmad-orch --init --update                 # Update existing config
bmad-orch start                           # Run with default config
bmad-orch start --headless                # Headless mode
bmad-orch start --config <path>           # Explicit config path
bmad-orch start --headless --config <path># Headless with explicit config
bmad-orch start --dry-run                 # Show execution plan without running
bmad-orch resume                          # Resume from last state
bmad-orch status                          # Show current state without running
bmad-orch validate                        # Validate config without executing
```

**Config resolution order (first match wins):**
1. `--config <path>` flag (explicit)
2. `bmad-orch.yaml` in current working directory (convention)

### Output Formats

- **State file:** JSON — machine-parseable for CI/CD integration and tooling, human-readable run history as audit trail
- **Log files:** Structured text with timestamps, step identifiers, provider tags, and severity levels — human-readable in terminal, grep-friendly for debugging
- **Consolidated log:** Single file per run, assembled from per-step logs before commit
- **Exit codes:** 0 = success, non-zero = failure with specific codes for different failure categories (config error, provider error, impactful runtime error)

### Config Schema

```yaml
# bmad-orch.yaml
providers:
  1:
    name: claude
    cli: claude
    model: opus-4
  2:
    name: gemini
    cli: gemini
    model: gemini-2.5-pro

cycles:
  story:
    steps:
      - skill: create-story
        provider: 1
        type: generative
        prompt: "/bmad-create-story for story {next_story_id}"
      - skill: adversarial-story-review
        provider: 1
        type: validation
        prompt: "/bmad-review-adversarial-general review story {current_story_file}"
      - skill: adversarial-story-review
        provider: 2
        type: validation
        prompt: "/bmad-review-adversarial-general review story {current_story_file}"
    repeat: 2
    pause_between_steps: 5s
    pause_between_cycles: 15s

  atdd:
    steps:
      - skill: atdd-test-builder
        provider: 1
        type: validation
        prompt: "/bmad-tea-testarch-atdd for {current_story_file}"
      - skill: atdd-test-builder
        provider: 2
        type: validation
        prompt: "/bmad-tea-testarch-atdd for {current_story_file}"
    repeat: 1

  dev:
    steps:
      - skill: dev-story
        provider: 1
        type: generative
        prompt: "/bmad-dev-story {current_story_file}"
      - skill: code-review
        provider: 2
        type: validation
        prompt: "/bmad-code-review"
    repeat: 1

git:
  commit_at: cycle       # step | cycle | end
  push_at: end           # step | cycle | end

pauses:
  between_steps: 5s
  between_cycles: 15s
  between_workflows: 30s

error_handling:
  retry_transient: true
  max_retries: 3
  retry_delay: 10s
```

### Scripting Support

- All commands return appropriate exit codes for shell scripting and CI/CD
- `--headless` flag suppresses all TUI output, writes structured logs only
- `status` and `validate` commands enable pre-flight checks in pipelines
- `--dry-run` shows execution plan without invoking providers
- JSON state file enables external tooling to monitor and react to orchestrator state
- Stdout/stderr separation: operational output to stdout, errors to stderr

### Implementation Considerations

- **Provider adapter pattern:** Each CLI provider (Claude, Gemini, future providers) gets a thin adapter that normalizes invocation, output capture, and error detection. New providers require only a new adapter, no core changes.
- **Config validation:** `bmad-orch validate` checks config schema, provider availability, model existence, and prompt template variable resolution before any execution.
- **Shell completion:** Provide completions for bash/zsh/fish for commands, flags, and config file paths.

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Problem-solving MVP — deliver the core "kick it off and walk away" experience on a single machine with interactive TUI. Prove the cycle engine, state management, and multi-model validation work reliably. Everything else builds on that foundation.

**Architecture Principle:** Build headless-first with TUI as a presentation layer. The core cycle engine runs without tmux; the TUI observes and controls it. This makes Phase 1.5 (headless/CI) nearly free and keeps the engine fully testable.

**Note:** MCP is not in the orchestrator's scope. Individual CLI tools handle their own MCP configuration. The orchestrator invokes the CLI; the CLI's MCP config handles the rest.

### MVP Feature Set (Phase 1)

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

### Phase 1.5 (Fast Follow)

- Container/headless mode (`--headless` flag)
- CI/CD pipeline integration with exit code contract
- Retry logic for transient failures (rate limits, timeouts)
- Structured logging for non-interactive environments

### Phase 2 (Growth)

- Four-pane tmux layout (Model A, Model B, Command Pane, Log Pane)
- Direct model pane interaction (focus switching, direct input to models)
- Advanced TUI features (richer status display, run analytics, history)
- Additional provider adapters beyond Claude and Gemini
- Community documentation and getting-started guides
- Community-shareable config templates and example playbooks
- Enhanced init wizard with config validation and recommendations
- `--init --update` for adding providers to existing config

### Phase 3 (Vision)

- Shared playbook marketplace for community-contributed configs
- Config repository/registry for discovering and sharing workflow patterns
- Community contribution workflow for submitting and reviewing playbooks

### Risk Mitigation Strategy

**Technical Risks:** The provider adapter layer is the riskiest component — different CLIs have different invocation patterns, output formats, and error behaviors. Mitigation: build Claude and Gemini adapters first, extract the common interface, then validate that a third adapter fits the pattern before committing to the abstraction.

**Market Risks:** Community adoption depends on the tool working reliably out of the box. Mitigation: Bobby and team dogfood extensively in Phase 1 before any community release. Phase 1.5 (headless/CI) validates automation reliability.

**Resource Risks:** The MVP is scoped for a small team. The headless-first architecture means the core engine can be validated before investing in the TUI presentation layer, providing an early internal milestone (engine-only) before the full MVP.

## Functional Requirements

### Configuration Management

- FR1: User can generate a new orchestrator config file through an interactive wizard
- FR2: User can define multiple providers with name, CLI command, and model in the config
- FR3: User can define cycles with ordered steps, each specifying a skill, provider, step type (generative/validation), and prompt template
- FR3a: User can define the execution order of cycles within a workflow
- FR4: User can configure cycle repeat counts to control how many times validation steps re-execute
- FR5: User can configure pause durations between steps, cycles, and workflows
- FR6: User can configure git commit and push timing (per-step, per-cycle, or end-of-run)
- FR7: User can configure error handling behavior (retry settings, max retries, retry delay)
- FR8: User can specify config file location via command-line flag or convention-based discovery
- FR9: System can resolve prompt template variables (e.g., `{next_story_id}`, `{current_story_file}`) from orchestrator state; unresolvable variables halt the step with a clear error identifying the missing variable

### Provider Management

- FR10: System can detect installed CLI tools (Claude, Gemini, others) on the host machine
- FR11: System can query a provider's CLI for available models
- FR12a: System can invoke a provider's CLI as a subprocess with a configured prompt
- FR12b: System can capture stdout and stderr from a running provider subprocess
- FR12c: System can detect provider subprocess completion, timeout, or unexpected termination
- FR13: System can normalize provider output and error behavior through a provider adapter interface
- FR14: System can operate with a single provider when only one is available (graceful degradation)

### Cycle Engine

- FR15: System can execute a cycle's steps in configured order
- FR16: System can distinguish generative steps (run only on first cycle) from validation steps (run every cycle)
- FR17: System can repeat a cycle's validation steps for the configured number of repetitions
- FR18: System can execute multiple cycles in sequence (story → atdd → dev) as a complete workflow
- FR19: System can pause for configured durations between steps and cycles to manage rate limits

### State Management

- FR20: System can atomically persist execution state to a JSON state file after each step completion
- FR21: System can record which step was last completed, which provider executed it, and the outcome
- FR22: User can resume execution from the last completed step after an interruption
- FR23: User can choose on resume whether to re-run the last step, continue from next, restart the cycle, or start from scratch
- FR24: System can maintain a running log of all state changes across multiple runs

### Logging & Observability

- FR25: System can capture per-step logs with timestamps, step identifiers, provider tags, and severity levels
- FR26: System can consolidate per-step logs into a single run log file before commit
- FR27: User can view current orchestrator state without starting a run (`status` command)
- FR28: System can write structured text logs suitable for both human reading and grep-based debugging

### Git Integration

- FR29: System can commit orchestrator output and logs to git at configurable intervals
- FR30: System can push commits to remote at configurable intervals
- FR31: System can perform emergency commit and push when an impactful error occurs before halting

### Interactive TUI (Phase 1)

- FR32: System can display a two-pane tmux layout showing active model output and command/log pane
- FR32a: TUI output pane automatically switches to display the currently active model as the cycle progresses
- FR33: System can display a status bar showing current phase, step, provider, and cycle progress
- FR34: User can pause execution after the current step completes
- FR35: User can skip the current step
- FR36: User can abort execution (triggering commit + push + halt)
- FR37: User can restart the current step

### Validation & Diagnostics

- FR38: User can validate a config file for schema correctness, provider availability, and model existence without executing (`validate` command)
- FR39: System can detect and classify errors as recoverable or impactful
- FR40: System can log recoverable errors and continue execution
- FR41: System can halt execution on impactful errors after committing state and pushing to remote

### Init Wizard

- FR42: Init wizard can detect installed CLI providers and present them for selection
- FR43: Init wizard can query selected providers for available models and present them for selection
- FR44: Init wizard can offer sensible default cycle configurations that the user can accept or modify
- FR45: Init wizard can generate a valid `bmad-orch.yaml` config file from user selections

### Workflow Control

- FR46: System can display a playbook summary on start showing all cycles, steps, providers, and prompts that will execute, and prompt the user to proceed or modify
- FR47: User can perform a dry run that shows the complete execution plan without invoking any providers (`--dry-run` flag)

### Audit Trail

- FR48: State file maintains a human-readable run history including all completed steps, providers used, outcomes, timestamps, and errors — serving as both machine-parseable state and human-readable audit trail

### User-Model Interaction

- FR49: User can send input to the active model's subprocess via the command pane when the model is awaiting a response

## Non-Functional Requirements

### Reliability

- NFR1: System must maintain consistent state file integrity — a crash or kill at any point must leave the state file in a valid, recoverable condition (atomic writes)
- NFR2: System must complete 10+ consecutive story cycles without requiring human intervention for non-content reasons
- NFR3: System must detect and recover from transient provider failures (rate limits, timeouts, network interruptions) without corrupting state
- NFR4: System must never lose completed work — all successful step outputs must be persisted before the next step begins
- NFR5: System must gracefully handle unexpected provider subprocess termination (crash, OOM kill, signal) without entering an unrecoverable state
- NFR6: Log files must be complete enough to diagnose any failure without reproducing it — every state transition, provider invocation, and error must be logged with timestamps

### Resource Management

- NFR7: The orchestrator process plus all spawned CLI subprocesses must not collectively exceed 80% of system CPU usage; the orchestrator must monitor resource consumption continuously
- NFR8: The orchestrator must monitor memory usage of itself and spawned subprocesses; if combined usage exceeds 80% of system memory, the orchestrator must kill the offending subprocess and log an impactful error
- NFR9: The orchestrator must not leak file handles, subprocess references, or temporary files across step boundaries — each step must clean up fully before the next begins
- NFR10: Resource monitoring must be active in both interactive and headless modes
- NFR11: When a subprocess is killed for resource violation, the orchestrator must treat it as an impactful error (log, commit, push, halt)

### Integration

- NFR12: Provider adapters must tolerate minor CLI output format changes without breaking — parse defensively, fail explicitly when output is unrecognizable
- NFR13: The orchestrator must target current/latest versions of provider CLIs only — no backwards compatibility shims
- NFR14: Provider subprocess invocation must be isolated — a hung or misbehaving provider must not block the orchestrator's ability to log, update state, or respond to user commands
- NFR15: Git operations must handle common failure cases (lock files, network failures, auth issues) with clear error messages rather than silent failures
