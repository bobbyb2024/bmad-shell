# Epic 6: Init Wizard & Onboarding

New user goes from zero to a working configuration in under 5 minutes through a guided, conversational setup experience with smart defaults and progressive disclosure.

## Story 6.1: CLI Detection & tmux Discovery

As a **new user**,
I want the init wizard to detect what tools I have installed and guide me accordingly,
So that I know exactly what capabilities are available before configuring anything.

**Acceptance Criteria:**

**Given** a user runs `bmad-orch --init`
**When** the wizard starts
**Then** it first checks for tmux availability before any provider detection

**Given** tmux is not installed on macOS
**When** the wizard detects its absence
**Then** it displays: `tmux not found. Install with: brew install tmux`
**And** asks if the user wants to install now or continue without it

**Given** tmux is not installed on Linux
**When** the wizard detects its absence
**Then** it displays: `tmux not found. Install with: sudo apt install tmux` (or `sudo dnf install tmux`)

**Given** the user declines to install tmux
**When** the wizard continues
**Then** it displays: `No problem — Lite mode available. Install tmux later for the full TUI experience.` and proceeds to provider detection

**Given** the wizard proceeds to provider detection
**When** it scans for installed CLI tools
**Then** it checks for Claude CLI and Gemini CLI (and any other supported providers) and reports what was found

**Given** both Claude and Gemini CLIs are detected
**When** the results are presented
**Then** the wizard lists both with their detected versions conversationally: `Found Claude CLI and Gemini CLI — you're set for adversarial validation.`

**Given** only one CLI is detected (e.g., Claude only)
**When** the results are presented
**Then** the wizard frames it positively: `Found Claude CLI — that's all you need to get started. Add adversarial validation later with --init again.`

**Given** no CLI providers are detected
**When** the wizard reports the result
**Then** it exits with helpful install links for supported CLIs: `No AI CLIs detected. Install Claude CLI or Gemini CLI first.`
**And** the exit is clean with no config generated

## Story 6.2: Provider & Model Selection

As a **new user**,
I want the wizard to show me available models and let me pick which to use,
So that I can configure providers without memorizing model names.

**Acceptance Criteria:**

**Given** one or more CLI providers are detected
**When** the wizard queries each for available models
**Then** it presents a numbered list of models for each provider: `I found Claude CLI with: [1] opus-4 [2] sonnet-4. Which model for generative steps?`

**Given** a numbered model list is displayed
**When** the user types a number and presses Enter
**Then** the corresponding model is selected for the specified role

**Given** a model selection prompt
**When** the user presses Enter with no input
**Then** the default selection (first/recommended model) is accepted

**Given** the user enters an invalid number
**When** the input is validated
**Then** the wizard re-prompts with a hint: `Not a valid choice. Choose from the list above:`

**Given** multiple providers are available
**When** the wizard configures provider assignments
**Then** it asks which provider to use for generative steps and which for validation steps, with sensible defaults

**Given** only one provider is available
**When** the wizard configures provider assignments
**Then** it assigns the single provider to all step types without asking — no unnecessary questions about roles

**Given** any wizard prompt
**When** the user types `b` or `back`
**Then** the wizard returns to the previous question

**Given** any wizard prompt
**When** the user types `q` or presses Ctrl+C
**Then** the wizard exits cleanly with no config generated

## Story 6.3: Cycle & Workflow Configuration

As a **new user**,
I want the wizard to offer smart defaults I can accept with Enter,
So that I get a working config quickly without needing to understand every option.

**Acceptance Criteria:**

**Given** the wizard reaches cycle configuration
**When** it presents defaults
**Then** it offers: `Recommended: 1 story creation, 2 review cycles. Accept defaults? [Y/n]`

**Given** the user presses Enter or types `y`
**When** accepting defaults
**Then** the wizard uses the recommended cycle configuration and moves to the next section

**Given** the user types `n`
**When** declining defaults
**Then** the wizard walks through cycle configuration conversationally: `How many review rounds? Most users do 2 — enough to catch issues without burning credits.`

**Given** the wizard reaches git configuration
**When** it presents defaults
**Then** it offers: `Commit per cycle, push at end? [Y/n]`

**Given** the wizard reaches pause configuration
**When** it presents defaults
**Then** it offers: `Default pauses: 5s between steps, 15s between cycles. OK? [Y/n]`

**Given** the wizard reaches error handling configuration
**When** it presents defaults
**Then** it offers sensible retry defaults: `Retry transient errors up to 3 times with 10s delay? [Y/n]`

**Given** any configuration step
**When** the user accepts the default
**Then** the wizard moves forward immediately — no unnecessary follow-up questions

## Story 6.4: Config Generation & Validation

As a **new user**,
I want the wizard to generate a valid config and confirm it works,
So that I can start running cycles immediately with confidence.

**Acceptance Criteria:**

**Given** all wizard selections are complete
**When** the wizard generates the config
**Then** it creates a valid `bmad-orch.yaml` file in the current working directory with all selected providers, models, cycles, steps, git settings, pauses, and error handling

**Given** the config is generated
**When** the wizard validates it
**Then** it automatically runs the same validation as `bmad-orch validate` before saving — the user never gets a broken config

**Given** validation passes
**When** the wizard completes
**Then** it displays a Rich-formatted summary table showing the generated config: providers, models, cycle structure, git settings
**And** concludes with: `Config created! Run bmad-orch start to begin. Run bmad-orch validate to check config anytime.`

**Given** a `bmad-orch.yaml` already exists in the current directory
**When** the wizard attempts to save
**Then** it prompts: `Config exists. Overwrite? (y/n)` — defaults to `n` (safe option), single keystroke, no Enter required

**Given** the user declines to overwrite
**When** the wizard handles the refusal
**Then** it suggests an alternative: `Save as bmad-orch.backup.yaml instead? (y/n)` or allows the user to specify a different path

**Given** the generated YAML
**When** I inspect its format
**Then** config keys use `snake_case` matching Pydantic field names, and the structure matches the config schema from Epic 1
