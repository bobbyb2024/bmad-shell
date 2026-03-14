# User Journey Flows

## Flow 1: Init Wizard (Journeys 1 & 4)

**Goal:** Zero to working config in under 5 minutes. Conversational, not form-like.

```mermaid
flowchart TD
    A[bmad-orch --init] --> B{tmux installed?}
    B -->|Yes| C[Detect CLI providers]
    B -->|No| B1["tmux not found. Install with: brew/apt install tmux"]
    B1 --> B2{User installs?}
    B2 -->|Yes| C
    B2 -->|No| B3["No problem — Lite mode available. Continuing..."]
    B3 --> C

    C --> D{Providers found?}
    D -->|None| D1["No AI CLIs detected. Install claude or gemini CLI first."]
    D1 --> D2[Exit with helpful install links]
    D -->|One found| E1["Found Claude CLI — that's all you need to get started.
    Add adversarial validation later with init again."]
    D -->|Multiple found| E2[List detected providers with models]

    E1 --> F[Query available models from detected CLI]
    E2 --> F

    F --> G[Present provider/model selection]
    G --> H{Configure cycles}
    H --> H1["Recommended defaults:
    1 story creation, 2 review cycles.
    Accept defaults? Y/n"]
    H1 -->|Accept| I[Configure git integration]
    H1 -->|Modify| H2[Walk through cycle config conversationally]
    H2 --> I

    I --> I1["Commit per cycle, push at end? Y/n"]
    I1 --> J[Configure pauses]
    J --> J1["Default pauses: 5s between steps, 15s between cycles. OK? Y/n"]
    J1 --> K[Generate bmad-orch.yaml]
    K --> L[Validate generated config]
    L --> M["Config created! Run bmad-orch start to begin.
    Run bmad-orch validate to check config anytime."]
```

**Key UX Decisions:**
- Every question has a sensible default that can be accepted with Enter
- Single-provider detection is framed positively ("that's all you need"), not as a limitation
- Model querying happens automatically — users pick from a list, never type model names
- Config validation runs automatically before saving — user never gets a broken config
- Exit with helpful guidance if no providers found — don't leave users stranded

**Conversational Tone Examples:**
- "I found Claude CLI with opus-4 and sonnet-4. Which model for generative steps?" (not "Select primary provider model:")
- "How many review rounds? Most users do 2 — enough to catch issues without burning credits." (not "Enter cycle repeat count:")
- "All set! Here's your config summary:" (not "Configuration generation complete.")

---

## Flow 2: Happy Path Run (Journey 1)

**Goal:** Start to completion with zero intervention. The "start and forget" experience.

```mermaid
flowchart TD
    A[bmad-orch start] --> B[Load bmad-orch.yaml]
    B --> C{Config valid?}
    C -->|No| C1["Config error: missing model 'opus-5'.
    Run bmad-orch validate for details."]
    C1 --> C2[Exit code 1]
    C -->|Yes| D{First run with this config?}

    D -->|Yes| E[Display pre-flight summary table]
    D -->|No| E2[Brief summary — auto-dismiss after 3s]

    E --> F{User confirms?}
    F -->|Yes / Enter| G[Launch tmux three-pane layout]
    F -->|Modify| F1[Open config in $EDITOR, re-validate on save]
    F1 --> E
    E2 --> G

    G --> H[Model A pane: first step streams]
    H --> H1[Model B pane: Waiting for next step ···]
    H1 --> H2[Status bar: green, step 1/N, provider name]

    H --> I{Step complete?}
    I -->|Yes| J[Update state file atomically]
    J --> K[Log step completion]
    K --> L{Git commit due?}
    L -->|Yes| L1[Commit artifacts]
    L -->|No| M{More steps in cycle?}
    L1 --> M

    M -->|Yes| N[Pause configured duration]
    N --> O[Next step — switch active pane]
    O --> H
    M -->|No| P{More cycles?}

    P -->|Yes| Q[Pause between cycles]
    Q --> H
    P -->|No| R{Git push due?}

    R -->|Yes| R1[Push to remote]
    R -->|No| S[Completion state]
    R1 --> S

    S --> T["Status bar: ✓ Complete | 5 stories | 12 commits | 47m | 0 errors"]
    T --> U{First ever run?}
    U -->|Yes| V["First automated run complete."]
    U -->|No| W[Numbers only]
    V --> W
    W --> X[Panes hold final output — user reviews on return]
```

**Key UX Moments:**
- **Pre-flight (3 seconds):** Rich table shows providers, cycles, steps, prompts. Scannable, not readable. Catches config typos before burning API credits.
- **Pane switch:** When execution moves from Model A to Model B, the active pane starts streaming and the status bar updates provider name. The previously active pane retains its output as persistent context.
- **Walking away:** Nothing changes about the UX when the user leaves. The TUI continues updating. tmux session persists. User reattaches later and sees current state instantly.
- **Return:** Status bar and pane borders tell the story in one glance. Green + "Complete" = done. Green + streaming = still running. Red = needs attention.

---

## Flow 3: Intervention & Resume (Journey 2)

**Goal:** Handle mid-run interactions and failure recovery without losing trust.

```mermaid
flowchart TD
    subgraph "Mid-Run Intervention"
        A[Model asks a question] --> B[Pane border turns yellow]
        B --> C["Status bar: ⚠ awaiting input"]
        C --> D["Command pane: ⚠ Claude asks: 'Should I include
        error handling ACs for timeout scenarios?'"]
        D --> E{User present?}
        E -->|Yes| F[User types response in command pane]
        F --> G[Input routed to active model subprocess]
        G --> H[Pane border returns to green]
        H --> I[Execution continues]
        E -->|No / Timeout| J{Timeout config?}
        J -->|Skip step| K[Log timeout, skip to next step]
        J -->|Pause| L[Remain in yellow state until user returns]
        J -->|Auto-respond| M[Send configured default response]
        K --> I
        L --> F
        M --> I
    end

    subgraph "Impactful Error"
        AA[Provider crashes / unrecoverable error] --> BB[Pane border turns red]
        BB --> CC["Status bar: ✗ Gemini subprocess terminated"]
        CC --> DD[State file updated atomically]
        DD --> EE[Emergency git commit + push]
        EE --> FF["Command pane log:
        [14:45:02] ✗ ERROR: Gemini subprocess terminated (exit 137)
        [14:45:02] State saved. Partial work committed and pushed.
        [14:45:02] Run bmad-orch resume to continue."]
        FF --> GG[Execution halted]
    end

    subgraph "Resume Flow"
        RA[bmad-orch resume] --> RB[Load state file]
        RB --> RC["Display resume context:
        Last run: 2026-03-13 14:30
        Stopped at: story cycle, step 3/4 (Gemini review)
        Reason: Gemini subprocess terminated
        Completed: 2/5 stories, steps 1-2 of story 3"]
        RC --> RD{Resume options}
        RD --> RE["[1] Re-run failed step (Gemini review of story 3)"]
        RD --> RF["[2] Skip failed step, continue to step 4"]
        RD --> RG["[3] Restart current cycle (story 3 from step 1)"]
        RD --> RH["[4] Start from scratch (all stories)"]
        RE --> RI[Launch TUI, execute from chosen point]
        RF --> RI
        RG --> RI
        RH --> RI
    end
```

**Key UX Decisions:**
- **Yellow state is patient** — It doesn't escalate to red. It waits. The user might be at lunch. Yellow means "when you get back" not "drop everything."
- **Timeout behavior is configurable** — Some users want auto-skip, some want to pause indefinitely, some want a default response. The config decides, not the tool.
- **Error context is immediate** — The command pane log shows exactly what happened, when, and what to do next. No log file hunting required.
- **Resume is contextual** — The resume screen shows enough state to make a decision: what was running, where it stopped, why, and what's already done. Users pick from numbered options, not guess commands.
- **Emergency commit preserves work** — Impactful errors trigger commit + push before halting. Completed work is never lost.

---

## Flow 4: Headless Contract (Journey 3)

**Goal:** Zero-interaction execution with machine-parseable output for CI/CD.

```mermaid
flowchart TD
    A["bmad-orch start --headless --config ./bmad-orch.yaml"] --> B[Load and validate config]
    B --> C{Config valid?}
    C -->|No| C1["stderr: Config error: specific issue"]
    C1 --> C2["Exit code 2 (config error)"]
    C -->|Yes| D[Execute playbook sequentially]

    D --> E[Per-step structured log to stdout]
    E --> E1["[2026-03-13T14:30:01Z] [INFO] [story/1] [claude/opus-4]
    Step started: create story 1"]
    E1 --> F{Step outcome}

    F -->|Success| G[State file updated]
    G --> H{More steps?}
    H -->|Yes| I[Pause, continue]
    I --> D
    H -->|No| J[Consolidate logs]

    F -->|Transient error| K[Retry per config]
    K --> K1{Retry success?}
    K1 -->|Yes| G
    K1 -->|No, max retries| L[Impactful error path]

    F -->|Impactful error| L
    L --> L1["stderr: [ERROR] Step failed: details"]
    L1 --> L2[Commit partial state + push]
    L2 --> L3["Exit code 3 (runtime error)"]

    J --> M[Final git commit + push]
    M --> N["stdout: Run complete. 5 stories, 12 commits, 0 errors, 47m"]
    N --> O["Exit code 0 (success)"]
```

**Exit Code Contract:**

| Code | Meaning | CI/CD Action |
|---|---|---|
| 0 | Success — all cycles completed | Pipeline passes |
| 1 | Usage error — bad flags, missing args | Fix invocation |
| 2 | Config error — invalid yaml, missing provider, bad model | Fix config |
| 3 | Runtime error — impactful failure during execution | Check state file + logs |
| 4 | Provider error — all retries exhausted for a provider | Check provider status |

**Structured Log Format:**
```
[ISO-8601 timestamp] [SEVERITY] [cycle/step] [provider/model] Message
```

**Headless Differences from TUI:**
- No tmux, no Rich, no ANSI colors
- All output to stdout (operational) and stderr (errors)
- State file is the primary status mechanism — external tools poll it
- Retries handled silently with log entries (no user intervention possible)
- Same state file format — a headless run can be resumed in TUI mode and vice versa

---

## Journey Patterns

**Pattern: Escalation Communication**
Used across all flows. State changes are communicated through the same escalation system regardless of mode:
- TUI: pane border color + status bar + command pane log
- Lite: Rich-styled status line + inline log
- Headless: structured log severity + exit code

**Pattern: Graceful Degradation**
Every flow has a degraded path that still delivers value:
- No tmux → Lite mode (still visual)
- No second provider → single-model cycles (still automated)
- Model timeout → configurable fallback (skip/pause/auto-respond)
- Crash → emergency commit (work preserved)

**Pattern: Contextual Decision Points**
Every decision point shows enough context to decide without external investigation:
- Pre-flight: full playbook visible before confirming
- Intervention: the model's question visible in command pane
- Resume: last run state, failure reason, and completed work visible before choosing
- Init wizard: detected providers and models visible before selecting

**Pattern: State as Source of Truth**
The JSON state file is the single source of truth across all modes:
- TUI reads state to render status bar
- Resume reads state to present options
- Headless writes state for external monitoring
- State survives crashes (atomic writes)
- State is human-readable (audit trail) AND machine-parseable (tooling)

## Flow Optimization Principles

1. **Minimum steps to value** — Init wizard: 5 questions with defaults → working config. Happy path run: 1 command → walk away. Resume: 1 command → numbered choice → running.
2. **No dead ends** — Every error state has a clear next action. Every flow has a recovery path. No screen ever leaves the user without guidance on what to do.
3. **Progressive context** — Show less by default, more on demand. Status bar shows headline, log file has the story. Pre-flight shows the plan, `--dry-run` shows every detail.
4. **Mode portability** — A run started in TUI can be resumed in headless and vice versa. A config created by Bobby works for Sarah without modification. State files are portable across modes and users.
