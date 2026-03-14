# Epic List

## Epic 1: Project Foundation & Configuration
User can install the tool and define, validate, and preview orchestrator configurations — seeing exactly what will execute before spending API credits.
**FRs covered:** FR1-FR8, FR38, FR46, FR47

## Epic 2: Provider Detection & Execution
The orchestrator detects installed AI CLIs (Claude, Gemini), queries their available models, and executes prompts with full streaming output capture via PTY.
**FRs covered:** FR10-FR14

## Epic 3: Core Cycle Engine
User runs the orchestrator and it executes multi-step, multi-cycle workflows — distinguishing generative from validation steps, repeating cycles as configured, pausing between steps, tracking state atomically, logging comprehensively, and handling errors as they occur.
**FRs covered:** FR9, FR15-FR21, FR24-FR25, FR28, FR39, FR40

## Epic 4: Reliable Unattended Execution
User runs `bmad-orch start --headless` and returns to completed, committed, auditable work — with git integration, resume capability, resource monitoring, emergency error handling, structured headless output, and CI/CD exit code contract.
**FRs covered:** FR22-FR23, FR26-FR27, FR29-FR31, FR41, FR48
**NFRs addressed:** NFR1-NFR15

## Epic 5: Interactive TUI *(parallel with Epics 6 & 7)*
User observes and controls live execution in a three-pane tmux TUI — watching model output stream in real-time, glancing at the status bar, using keyboard shortcuts, and sending input to models via the command pane.
**FRs covered:** FR32-FR37, FR32a, FR33, FR49

## Epic 6: Init Wizard & Onboarding *(parallel with Epics 3, 4, 5 & 7)*
New user goes from zero to a working configuration in under 5 minutes through a guided, conversational setup experience with smart defaults and progressive disclosure.
**FRs covered:** FR42-FR45

## Epic 7: Lite Mode Experience *(parallel with Epics 5 & 6)*
Users without tmux get a styled single-stream experience with Rich-formatted status, colored escalation, and formatted tables — the tool adapts automatically to the environment.
**FRs covered:** Cross-cutting UX (UX-DR1, UX-DR20)
