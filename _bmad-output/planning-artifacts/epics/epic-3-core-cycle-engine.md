# Epic 3: Core Cycle Engine

User runs the orchestrator and it executes multi-step, multi-cycle workflows — distinguishing generative from validation steps, repeating cycles as configured, pausing between steps, tracking state atomically, logging comprehensively, and handling errors as they occur.

## Story 3.1: Event Emitter & Event Types

As a **developer**,
I want a typed event system that decouples the engine from all presentation layers,
So that renderers can subscribe to engine events without the engine knowing or caring which renderers exist.

**Acceptance Criteria:**

**Given** the `engine/events.py` module
**When** I inspect the event types
**Then** it defines frozen dataclasses for `StepStarted`, `StepCompleted`, `CycleStarted`, `CycleCompleted`, `EscalationChanged`, `LogEntry`, `ProviderOutput`, `RunCompleted`, `ErrorOccurred`, and `ResourceThresholdBreached`

**Given** any event dataclass
**When** I attempt to mutate a field after creation
**Then** it raises `FrozenInstanceError` — all events are immutable

**Given** the `EventEmitter` in `engine/emitter.py`
**When** I call `subscribe(event_type, callback)`
**Then** the callback is registered for that event type

**Given** an emitter with subscribers registered
**When** I call `emit(event)`
**Then** all subscribers for that event type are invoked synchronously with the event
**And** events are delivered in subscription order

**Given** a subscriber that raises an exception
**When** an event is emitted
**Then** the emitter catches the exception, logs it, and continues to invoke remaining subscribers — a broken renderer never crashes the engine

**Given** the emitter
**When** I inspect its imports
**Then** it accepts `Callable` subscribers, never imports from `rendering/`, and has no knowledge of any specific renderer

## Story 3.2: State Manager & Atomic Persistence

As a **user**,
I want execution state persisted atomically after every step,
So that a crash at any point leaves a valid, recoverable state file and I never lose completed work.

**Acceptance Criteria:**

**Given** the `state/schema.py` module
**When** I inspect the state models
**Then** it defines Pydantic models for `RunState`, `StepRecord`, `CycleRecord`, and `ErrorRecord` — all immutable with `with_*` update methods

**Given** a step completes successfully
**When** the state manager saves state
**Then** it writes to `.bmad-orch-state.tmp` in the same directory as the state file, then performs atomic `os.rename()` to `bmad-orch-state.json`

**Given** a crash occurs during a state write
**When** the orchestrator restarts
**Then** the previous valid state file remains intact (the temp file is orphaned, not the real state file)

**Given** a completed step
**When** state is recorded
**Then** the `StepRecord` includes which step was completed, which provider executed it, the outcome, and a timestamp

**Given** multiple runs over time
**When** I inspect the state file
**Then** it maintains a running history of all state changes across runs (append to run history, not overwrite)

**Given** the state manager
**When** I call `load()` with no existing state file
**Then** it returns a fresh `RunState` with empty history

**Given** the temp file location
**When** the state manager creates it
**Then** the temp file is always in the same directory as the state file (same-filesystem requirement for atomic rename)

## Story 3.3: Structured Logging Subsystem

As a **user**,
I want comprehensive, structured logs for every step,
So that I can diagnose any failure without reproducing it.

**Acceptance Criteria:**

**Given** the `logging.py` module
**When** `configure_logging(mode)` is called with human mode (TUI/Lite)
**Then** structlog is configured with a processor chain producing `[timestamp] [severity_icon] [context] message` colored text output

**Given** the `logging.py` module
**When** `configure_logging(mode)` is called with machine mode (Headless)
**Then** structlog is configured with a processor chain producing `[ISO-8601 timestamp] [SEVERITY] [context_dict] message` structured plain text

**Given** an async step execution
**When** log calls are made within the step
**Then** `structlog.contextvars` automatically includes the current step identifier, provider name, and cycle context without explicit passing

**Given** two concurrent async tasks (e.g., resource monitor and step execution)
**When** both produce log output
**Then** context does not leak between tasks — resource monitor logs do not inherit step/provider context

**Given** a step execution
**When** per-step logs are captured
**Then** each log entry includes timestamp, step identifier, provider tag, and severity level

**Given** structured log output
**When** I grep the log files
**Then** the format is grep-friendly with consistent field positions suitable for both human reading and automated parsing

## Story 3.4: Cycle Execution Engine

As a **user**,
I want the orchestrator to execute my configured cycles step by step,
So that my multi-step, multi-model workflows run automatically in the correct order.

**Acceptance Criteria:**

**Given** a cycle with 4 ordered steps
**When** the cycle engine executes
**Then** steps run in configured order (step 1, then 2, then 3, then 4)

**Given** a cycle with generative and validation step types
**When** the cycle runs for the first time
**Then** both generative and validation steps execute

**Given** a cycle with `repeat: 2`
**When** the second repetition runs
**Then** only validation steps execute — generative steps run only on the first cycle

**Given** a cycle with `repeat: 3`
**When** all repetitions complete
**Then** the generative step ran once and validation steps ran 3 times total

**Given** configured pause durations between steps
**When** a step completes
**Then** the engine pauses for the configured duration before starting the next step

**Given** configured pause durations between cycles
**When** a cycle repetition completes
**Then** the engine pauses for the configured duration before starting the next repetition

**Given** the cycle engine executing a step
**When** the step starts and completes
**Then** `StepStarted` and `StepCompleted` events are emitted with step details, provider, and timing

**Given** the cycle engine executing a cycle
**When** the cycle starts and completes
**Then** `CycleStarted` and `CycleCompleted` events are emitted

**Given** the cycle engine
**When** a step completes
**Then** state is persisted atomically before the next step begins

## Story 3.5: Error Detection & Classification

As a **user**,
I want errors automatically classified and handled appropriately,
So that transient issues are retried silently while serious failures are surfaced clearly.

**Acceptance Criteria:**

**Given** a provider returns a rate limit error (HTTP 429 or equivalent CLI error)
**When** the error classification system evaluates it
**Then** it is classified as `RECOVERABLE` with severity `ProviderTimeoutError`

**Given** a recoverable error during step execution
**When** the error handling logic processes it
**Then** the error is logged with full context and execution continues to the next retry or step
**And** the user sees nothing unless they inspect logs

**Given** a provider subprocess crash (unexpected termination, OOM kill)
**When** the error classification system evaluates it
**Then** it is classified as `IMPACTFUL` with severity `ProviderCrashError`

**Given** an impactful error
**When** the error handling logic processes it
**Then** an `ErrorOccurred` event is emitted with the error details, classification, and suggested next action

**Given** an error with structured context
**When** it is logged
**Then** the log entry follows the format `✗ [What happened] — [What to do next]` and includes the error classification, provider name, step identifier, and timestamp

**Given** the error classification system
**When** I inspect the implementation
**Then** the engine checks `error.severity` (the `ErrorSeverity` enum), not `isinstance()` checks against exception subclasses

## Story 3.6: Multi-Cycle Workflow Orchestration

As a **user**,
I want to run a complete workflow (story → atdd → dev) as a single command,
So that multiple cycle types execute in sequence without manual intervention.

**Acceptance Criteria:**

**Given** a config with three cycles defined (story, atdd, dev) in a specific order
**When** the runner executes the workflow
**Then** cycles execute in the configured order: story cycle completes fully, then atdd cycle, then dev cycle

**Given** configured pause durations between workflows
**When** one cycle type completes and the next begins
**Then** the engine pauses for the configured between-workflows duration

**Given** the runner module in `engine/runner.py`
**When** it orchestrates a workflow
**Then** it wires together the cycle engine, provider adapters, state manager, event emitter, and logging subsystem

**Given** a multi-cycle workflow executing
**When** each cycle completes
**Then** the state file reflects the completed cycle and the next cycle to execute

**Given** template variables in step prompts
**When** the runner prepares a step for execution
**Then** it resolves all template variables from current orchestrator state (e.g., `{current_story_file}` reflects the output from the story cycle)

**Given** a `RunCompleted` event
**When** the entire workflow finishes
**Then** the event includes total step count, total cycle count, elapsed time, and error count
