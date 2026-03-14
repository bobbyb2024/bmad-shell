# Functional Requirements

## Configuration Management

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

## Provider Management

- FR10: System can detect installed CLI tools (Claude, Gemini, others) on the host machine
- FR11: System can query a provider's CLI for available models
- FR12a: System can invoke a provider's CLI as a subprocess with a configured prompt
- FR12b: System can capture stdout and stderr from a running provider subprocess
- FR12c: System can detect provider subprocess completion, timeout, or unexpected termination
- FR13: System can normalize provider output and error behavior through a provider adapter interface
- FR14: System can operate with a single provider when only one is available (graceful degradation)

## Cycle Engine

- FR15: System can execute a cycle's steps in configured order
- FR16: System can distinguish generative steps (run only on first cycle) from validation steps (run every cycle)
- FR17: System can repeat a cycle's validation steps for the configured number of repetitions
- FR18: System can execute multiple cycles in sequence (story → atdd → dev) as a complete workflow
- FR19: System can pause for configured durations between steps and cycles to manage rate limits

## State Management

- FR20: System can atomically persist execution state to a JSON state file after each step completion
- FR21: System can record which step was last completed, which provider executed it, and the outcome
- FR22: User can resume execution from the last completed step after an interruption
- FR23: User can choose on resume whether to re-run the last step, continue from next, restart the cycle, or start from scratch
- FR24: System can maintain a running log of all state changes across multiple runs

## Logging & Observability

- FR25: System can capture per-step logs with timestamps, step identifiers, provider tags, and severity levels
- FR26: System can consolidate per-step logs into a single run log file before commit
- FR27: User can view current orchestrator state without starting a run (`status` command)
- FR28: System can write structured text logs suitable for both human reading and grep-based debugging

## Git Integration

- FR29: System can commit orchestrator output and logs to git at configurable intervals
- FR30: System can push commits to remote at configurable intervals
- FR31: System can perform emergency commit and push when an impactful error occurs before halting

## Interactive TUI (Phase 1)

- FR32: System can display a two-pane tmux layout showing active model output and command/log pane
- FR32a: TUI output pane automatically switches to display the currently active model as the cycle progresses
- FR33: System can display a status bar showing current phase, step, provider, and cycle progress
- FR34: User can pause execution after the current step completes
- FR35: User can skip the current step
- FR36: User can abort execution (triggering commit + push + halt)
- FR37: User can restart the current step

## Validation & Diagnostics

- FR38: User can validate a config file for schema correctness, provider availability, and model existence without executing (`validate` command)
- FR39: System can detect and classify errors as recoverable or impactful
- FR40: System can log recoverable errors and continue execution
- FR41: System can halt execution on impactful errors after committing state and pushing to remote

## Init Wizard

- FR42: Init wizard can detect installed CLI providers and present them for selection
- FR43: Init wizard can query selected providers for available models and present them for selection
- FR44: Init wizard can offer sensible default cycle configurations that the user can accept or modify
- FR45: Init wizard can generate a valid `bmad-orch.yaml` config file from user selections

## Workflow Control

- FR46: System can display a playbook summary on start showing all cycles, steps, providers, and prompts that will execute, and prompt the user to proceed or modify
- FR47: User can perform a dry run that shows the complete execution plan without invoking any providers (`--dry-run` flag)

## Audit Trail

- FR48: State file maintains a human-readable run history including all completed steps, providers used, outcomes, timestamps, and errors — serving as both machine-parseable state and human-readable audit trail

## User-Model Interaction

- FR49: User can send input to the active model's subprocess via the command pane when the model is awaiting a response
