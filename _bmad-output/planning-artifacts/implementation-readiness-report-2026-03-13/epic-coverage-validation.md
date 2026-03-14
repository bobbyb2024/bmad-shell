# Epic Coverage Validation

## Coverage Matrix

| FR Number | PRD Requirement | Epic Coverage | Status |
| :--- | :--- | :--- | :--- |
| FR1 | User can generate a new orchestrator config file through an interactive wizard | Epic 1, Story 6.1-6.4 | ✓ Covered |
| FR2 | User can define multiple providers with name, CLI command, and model in the config | Epic 1, Story 1.2 | ✓ Covered |
| FR3 | User can define cycles with ordered steps, each specifying a skill, provider, step type (generative/validation), and prompt template | Epic 1, Story 1.2 | ✓ Covered |
| FR3a | User can define the execution order of cycles within a workflow | Epic 1, Story 1.2 | ✓ Covered |
| FR4 | User can configure cycle repeat counts | Epic 1, Story 1.2 | ✓ Covered |
| FR5 | User can configure pause durations between steps, cycles, and workflows | Epic 1, Story 1.2 | ✓ Covered |
| FR6 | User can configure git commit and push timing | Epic 1, Story 1.2 | ✓ Covered |
| FR7 | User can configure error handling behavior | Epic 1, Story 1.2 | ✓ Covered |
| FR8 | User can specify config file location via command-line flag or convention-based discovery | Epic 1, Story 1.3 | ✓ Covered |
| FR9 | System can resolve prompt template variables from orchestrator state | Epic 3, Story 1.4, 3.6 | ✓ Covered |
| FR10 | System can detect installed CLI tools (Claude, Gemini, others) on the host machine | Epic 2, Story 2.1 | ✓ Covered |
| FR11 | System can query a provider's CLI for available models | Epic 2, Story 2.1 | ✓ Covered |
| FR12a | System can invoke a provider's CLI as a subprocess with a configured prompt | Epic 2, Story 2.2, 2.3 | ✓ Covered |
| FR12b | System can capture stdout and stderr from a running provider subprocess | Epic 2, Story 2.2, 2.3 | ✓ Covered |
| FR12c | System can detect provider subprocess completion, timeout, or unexpected termination | Epic 2, Story 2.2, 2.3 | ✓ Covered |
| FR13 | System can normalize provider output and error behavior through a provider adapter interface | Epic 2, Story 2.1 | ✓ Covered |
| FR14 | System can operate with a single provider when only one is available (graceful degradation) | Epic 2, Story 2.4 | ✓ Covered |
| FR15 | System can execute a cycle's steps in configured order | Epic 3, Story 3.4 | ✓ Covered |
| FR16 | System can distinguish generative steps from validation steps | Epic 3, Story 3.4 | ✓ Covered |
| FR17 | System can repeat a cycle's validation steps for the configured number of repetitions | Epic 3, Story 3.4 | ✓ Covered |
| FR18 | System can execute multiple cycles in sequence as a complete workflow | Epic 3, Story 3.6 | ✓ Covered |
| FR19 | System can pause for configured durations between steps and cycles | Epic 3, Story 3.4 | ✓ Covered |
| FR20 | System can atomically persist execution state to a JSON state file after each step completion | Epic 3, Story 3.2 | ✓ Covered |
| FR21 | System can record which step was last completed, which provider executed it, and the outcome | Epic 3, Story 3.2 | ✓ Covered |
| FR22 | User can resume execution from the last completed step after an interruption | Epic 4, Story 4.4 | ✓ Covered |
| FR23 | User can choose on resume whether to re-run the last step, continue from next, restart the cycle, or start from scratch | Epic 4, Story 4.4 | ✓ Covered |
| FR24 | System can maintain a running log of all state changes across multiple runs | Epic 3, Story 3.2 | ✓ Covered |
| FR25 | System can capture per-step logs with timestamps, step identifiers, provider tags, and severity levels | Epic 3, Story 3.3 | ✓ Covered |
| FR26 | System can consolidate per-step logs into a single run log file before commit | Epic 4, Story 4.5 | ✓ Covered |
| FR27 | User can view current orchestrator state without starting a run (`status` command) | Epic 4, Story 4.5 | ✓ Covered |
| FR28 | System can write structured text logs suitable for both human reading and grep-based debugging | Epic 3, Story 3.3 | ✓ Covered |
| FR29 | System can commit orchestrator output and logs to git at configurable intervals | Epic 4, Story 4.1 | ✓ Covered |
| FR30 | System can push commits to remote at configurable intervals | Epic 4, Story 4.1 | ✓ Covered |
| FR31 | System can perform emergency commit and push when an impactful error occurs before halting | Epic 4, Story 4.2 | ✓ Covered |
| FR32 | System can display a two-pane tmux layout showing active model output and command/log pane | Epic 5, Story 5.1 | ✓ Covered |
| FR32a | TUI output pane automatically switches to display the currently active model as the cycle progresses | Epic 5, Story 5.4 | ✓ Covered |
| FR33 | System can display a status bar showing current phase, step, provider, and cycle progress | Epic 5, Story 5.3 | ✓ Covered |
| FR34 | User can pause execution after the current step completes | Epic 5, Story 5.5 | ✓ Covered |
| FR35 | User can skip the current step | Epic 5, Story 5.5 | ✓ Covered |
| FR36 | User can abort execution (triggering commit + push + halt) | Epic 5, Story 5.5 | ✓ Covered |
| FR37 | User can restart the current step | Epic 5, Story 5.5 | ✓ Covered |
| FR38 | User can validate a config file for schema correctness, provider availability, and model existence without executing (`validate` command) | Epic 1, Story 1.3 | ✓ Covered |
| FR39 | System can detect and classify errors as recoverable or impactful | Epic 3, Story 3.5 | ✓ Covered |
| FR40 | System can log recoverable errors and continue execution | Epic 3, Story 3.5 | ✓ Covered |
| FR41 | System can halt execution on impactful errors after committing state and pushing to remote | Epic 4, Story 4.2 | ✓ Covered |
| FR42 | Init wizard can detect installed CLI providers and present them for selection | Epic 6, Story 6.1 | ✓ Covered |
| FR43 | Init wizard can query selected providers for available models and present them for selection | Epic 6, Story 6.2 | ✓ Covered |
| FR44 | Init wizard can offer sensible default cycle configurations that the user can accept or modify | Epic 6, Story 6.3 | ✓ Covered |
| FR45 | Init wizard can generate a valid `bmad-orch.yaml` config file from user selections | Epic 6, Story 6.4 | ✓ Covered |
| FR46 | System can display a playbook summary on start showing all cycles, steps, providers, and prompts | Epic 1, Story 1.5 | ✓ Covered |
| FR47 | User can perform a dry run showing complete execution plan without invoking any providers | Epic 1, Story 1.5 | ✓ Covered |
| FR48 | State file maintains a human-readable run history serving as machine-parseable state and audit trail | Epic 4, Story 4.5 | ✓ Covered |
| FR49 | User can send input to the active model's subprocess via the command pane | Epic 5, Story 5.6 | ✓ Covered |

## Missing Requirements

None. All 53 functional requirements (including sub-items) from the PRD are mapped to specific epics and stories.

## Coverage Statistics

- Total PRD FRs: 53
- FRs covered in epics: 53
- Coverage percentage: 100%

---
