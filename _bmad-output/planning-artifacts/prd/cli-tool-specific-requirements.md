# CLI Tool Specific Requirements

## Project-Type Overview

The BMAD Orchestrator is a dual-mode CLI tool: interactive (tmux TUI) and scriptable (headless). It follows CLI conventions for discoverability, composability, and automation-friendliness. The command structure is shallow and verb-based. Configuration uses convention-based file discovery with explicit flag override.

## Command Structure

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

## Output Formats

- **State file:** JSON — machine-parseable for CI/CD integration and tooling, human-readable run history as audit trail
- **Log files:** Structured text with timestamps, step identifiers, provider tags, and severity levels — human-readable in terminal, grep-friendly for debugging
- **Consolidated log:** Single file per run, assembled from per-step logs before commit
- **Exit codes:** 0 = success, non-zero = failure with specific codes for different failure categories (config error, provider error, impactful runtime error)

## Config Schema

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

## Scripting Support

- All commands return appropriate exit codes for shell scripting and CI/CD
- `--headless` flag suppresses all TUI output, writes structured logs only
- `status` and `validate` commands enable pre-flight checks in pipelines
- `--dry-run` shows execution plan without invoking providers
- JSON state file enables external tooling to monitor and react to orchestrator state
- Stdout/stderr separation: operational output to stdout, errors to stderr

## Implementation Considerations

- **Provider adapter pattern:** Each CLI provider (Claude, Gemini, future providers) gets a thin adapter that normalizes invocation, output capture, and error detection. New providers require only a new adapter, no core changes.
- **Config validation:** `bmad-orch validate` checks config schema, provider availability, model existence, and prompt template variable resolution before any execution.
- **Shell completion:** Provide completions for bash/zsh/fish for commands, flags, and config file paths.
