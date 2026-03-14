# User Journeys

## Journey 1: Solo Developer — First Run Success Path

*Meet Bobby. He's been running BMAD workflows manually — invoking Claude, copying output, switching to Gemini for a second opinion, committing results, repeating. It works, but it eats his afternoon.*

**Opening Scene:** Bobby installs the orchestrator and runs `bmad-orch --init`. The wizard detects his installed CLIs, queries available models, and walks him through provider setup and cycle configuration. He accepts most defaults, tweaks the story review cycle to 2 rounds, and gets a `config.yaml` in under 5 minutes.

**Rising Action:** He runs `bmad-orch start`. tmux splits into two panes — the active model's output on top and the command/log pane with status bar below. He watches Claude create the first story. The output pane switches to show Gemini when it runs adversarial review. The status bar ticks through each step. He glances at it, sees everything green, and goes to lunch.

**Climax:** He comes back to a terminal showing `✓ Story cycle complete — 3 stories specced, reviewed, ATDD tests generated, code implemented, code reviewed. 12 commits pushed.` The state file shows every step, every model, every outcome. The git log reads like a clean audit trail.

**Resolution:** Bobby opens the first story file. It's solid. He spends 5 minutes reviewing, finds one thing he'd tweak in the prompt config for next time. He edits `config.yaml`, kicks off another run, and gets back to the work that actually needs his brain.

*Requirements revealed: init wizard, config generation, tmux TUI, status bar, state management, log capture, git integration, resume capability.*

## Journey 2: Team Developer — Joining an Existing Project

*Meet Sarah. She's on Bobby's team. Bobby already set up the orchestrator config for the project. She needs to run the next sprint's story cycle.*

**Opening Scene:** Sarah pulls the repo. The `config.yaml` is already there. She runs `bmad-orch start` and the orchestrator detects the existing config, shows her the playbook summary, and asks if she wants to proceed or modify.

**Rising Action:** She proceeds. The tmux TUI launches. Midway through, Gemini's adversarial review flags a concern and asks a clarifying question. The command pane highlights it — `⚠ Active model awaiting input`. Sarah types her response in the command pane, which routes it to the active model. The run continues.

**Climax:** The run completes. Sarah notices one story's code review requested changes. The orchestrator logged the failure, committed the partial work, and marked the state file with exactly where it stopped and why.

**Resolution:** Sarah adjusts the story based on the review feedback, then runs `bmad-orch resume`. It picks up from the last completed step and finishes the cycle cleanly.

*Requirements revealed: config portability, playbook summary on start, command-pane input routing, error-triggered partial commit, resume from failure.*

## Journey 3: CI/CD Pipeline — Headless Automation

*The pipeline isn't a person. It doesn't care about tmux. It cares about exit codes, logs, and committed artifacts.*

**Opening Scene:** A merge to `develop` triggers a GitHub Actions workflow. The workflow runs `bmad-orch start --headless --config ./orchestrator-config.yaml`. No TUI, no panes — pure subprocess execution with structured log output.

**Rising Action:** The orchestrator executes the playbook sequentially. Each step writes to a structured log file. State updates after every step. Rate limit pauses fire between cycles. A transient API timeout hits during Gemini's review — the orchestrator catches it, logs a warning, waits, retries, and continues.

**Climax:** The full cycle completes. Exit code 0. Logs consolidated into a single file. All artifacts committed and pushed. The pipeline step passes green.

**Resolution:** If something had gone wrong — an impactful error — the orchestrator would have logged the failure, committed the partial state, pushed to the repo, and exited with a non-zero code. The pipeline would fail visibly, and the team would find the exact failure point in the state file and logs.

*Requirements revealed: headless mode, --headless flag, structured logging, exit codes, retry logic for transient errors, non-zero exit on impactful failure, CI/CD integration contract.*

## Journey 4: Community User — First-Time Setup

*Meet Alex. They found BMAD Orchestrator through the BMAD community. They've used BMAD manually but never automated it. They have Claude CLI installed but not Gemini.*

**Opening Scene:** Alex installs the orchestrator and runs `bmad-orch --init`. The wizard detects Claude CLI but not Gemini. It informs Alex: "Only one provider detected. You can run single-model cycles, or install a second provider for adversarial validation." Alex proceeds with Claude only for now.

**Rising Action:** The wizard asks about cycle configuration. Alex doesn't know what to pick. The wizard offers sensible defaults: "Recommended: 1 story creation, 2 review cycles. Accept defaults? [Y/n]". Alex hits enter. Config generated.

**Climax:** Alex runs their first cycle. It works. Single-model, no adversarial validation, but the automation alone saves them significant time. They later install Gemini CLI, run `bmad-orch --init --update`, and the wizard detects the new provider and offers to add adversarial validation cycles.

**Resolution:** Alex is now running multi-model cycles. They share their config with the community Discord. Someone else picks it up and runs it on their project.

*Requirements revealed: graceful single-provider mode, smart defaults, init --update for adding providers, provider detection, progressive disclosure of complexity.*

## Journey Requirements Summary

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
