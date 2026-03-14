# Non-Functional Requirements

## Reliability

- NFR1: System must maintain consistent state file integrity — a crash or kill at any point must leave the state file in a valid, recoverable condition (atomic writes)
- NFR2: System must complete 10+ consecutive story cycles without requiring human intervention for non-content reasons
- NFR3: System must detect and recover from transient provider failures (rate limits, timeouts, network interruptions) without corrupting state
- NFR4: System must never lose completed work — all successful step outputs must be persisted before the next step begins
- NFR5: System must gracefully handle unexpected provider subprocess termination (crash, OOM kill, signal) without entering an unrecoverable state
- NFR6: Log files must be complete enough to diagnose any failure without reproducing it — every state transition, provider invocation, and error must be logged with timestamps

## Resource Management

- NFR7: The orchestrator process plus all spawned CLI subprocesses must not collectively exceed 80% of system CPU usage; the orchestrator must monitor resource consumption continuously
- NFR8: The orchestrator must monitor memory usage of itself and spawned subprocesses; if combined usage exceeds 80% of system memory, the orchestrator must kill the offending subprocess and log an impactful error
- NFR9: The orchestrator must not leak file handles, subprocess references, or temporary files across step boundaries — each step must clean up fully before the next begins
- NFR10: Resource monitoring must be active in both interactive and headless modes
- NFR11: When a subprocess is killed for resource violation, the orchestrator must treat it as an impactful error (log, commit, push, halt)

## Integration

- NFR12: Provider adapters must tolerate minor CLI output format changes without breaking — parse defensively, fail explicitly when output is unrecognizable
- NFR13: The orchestrator must target current/latest versions of provider CLIs only — no backwards compatibility shims
- NFR14: Provider subprocess invocation must be isolated — a hung or misbehaving provider must not block the orchestrator's ability to log, update state, or respond to user commands
- NFR15: Git operations must handle common failure cases (lock files, network failures, auth issues) with clear error messages rather than silent failures
