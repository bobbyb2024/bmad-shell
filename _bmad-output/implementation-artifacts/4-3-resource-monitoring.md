---
status: done
stepsCompleted: [1, 2, 3, 4, 5]
---

# Story 4.3: Resource Monitoring

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **user**,
I want the orchestrator to prevent runaway processes from consuming all system resources,
so that my machine remains responsive even when AI CLI subprocesses misbehave.

## Acceptance Criteria

1. **Given** the `resources.py` module
   **When** the resource monitor starts
   **Then** it launches an async periodic polling task using `psutil` at a configurable interval (default 1.0 seconds).

2. **Given** the resource monitor is active
   **When** it polls
   **Then** it tracks CPU and memory usage for the orchestrator process and all spawned subprocess PIDs currently managed by the `CycleExecutor`, including any child process trees spawned by those subprocesses.

3. **Given** the sum of CPU percentages across all tracked processes (orchestrator + spawned subprocesses) exceeds the configured CPU threshold (default 80%), or the sum of their RSS memory divided by total system memory exceeds the configured memory threshold (default 80%)
   **When** the threshold is breached
   **Then** the resource monitor emits a `ResourceThresholdBreached` event, identifies the offending subprocess tree (the one with the highest usage, excluding the main orchestrator process), terminates it, and triggers a `ResourceError`. If the orchestrator itself is the sole offender, it directly triggers a fatal `ResourceError`.

4. **Given** a `ResourceError` is triggered by the monitor's background task
   **When** it occurs
   **Then** it must be properly propagated to the runner's main event loop, where the runner treats it as an impactful error (severity=IMPACTFUL) — triggering the emergency flow (commit + push + halt).

5. **Given** the resource monitor
   **When** it is active
   **Then** it runs in both interactive and headless modes with identical behavior (the monitor has no UI-dependent code paths — it uses only async polling and logging, so mode parity is achieved by construction).

6. **Given** a step completes normally
   **When** the next step has not yet started
   **Then** the resource monitor does not leak tracking of previously completed subprocess PIDs — it must query the `CycleExecutor` for the currently active set.

7. **Given** the `psutil` library is unavailable in the environment
   **When** the monitor initializes
   **Then** it logs a warning and gracefully degrades to a no-op mode without crashing the orchestrator.

## Tasks / Subtasks

- [x] 1. Update Configuration Schema (AC: 1)
  - [x] Add `ResourceConfig` model to `src/bmad_orch/config/schema.py` with `polling_interval: float = 1.0`, `cpu_threshold: float = 80.0`, and `memory_threshold: float = 80.0`. Add Pydantic validators: `polling_interval` must be > 0. `memory_threshold` must be between 0.0 and 100.0 (exclusive). `cpu_threshold` must be > 0.0 (can exceed 100.0 for multi-core systems).
  - [x] Add `resources: ResourceConfig = Field(default_factory=ResourceConfig)` to `OrchestratorConfig`.
- [x] 2. Implement Resource Monitor (AC: 1, 2, 3, 5, 7)
  - [x] Create `src/bmad_orch/engine/resources.py` with `ResourceMonitor` class.
  - [x] Guard `import psutil` with `try/except`; set a flag to enable no-op mode if unavailable.
  - [x] Implement `start(executor: CycleExecutor)` and `stop()` methods. `start` should launch a background `asyncio` task.
  - [x] Implement `_poll_loop()` using `psutil` with `await asyncio.sleep(self.config.polling_interval)`. 
  - [x] Gather metrics for the current process (`os.getpid()`) and all PIDs from `executor.running_pids`. Resolve full process trees using `psutil.Process(pid).children(recursive=True)`. Handle `psutil.NoSuchProcess`, `psutil.AccessDenied`, and `psutil.ZombieProcess` during metric gathering.
  - [x] If thresholds are breached:
    - Emit `ResourceThresholdBreached` event asynchronously without blocking the loop.
    - Identify the subprocess with the highest usage (the "offender", ignoring `os.getpid()`). If no subprocess exists, designate the orchestrator as the offender.
    - Kill the offender's entire process tree and propagate a `ResourceError` to the runner. Set a flag in `CycleExecutor` *before* killing to prevent race conditions in error handling.
  - [x] Log at WARNING level on threshold breach, at ERROR level on process kill, and at INFO level on monitor start/stop.
- [x] 3. Update Cycle Executor (AC: 2, 6)
  - [x] Add a `running_pids` property to `CycleExecutor` in `src/bmad_orch/engine/cycle.py` that extracts `.pid` from each `asyncio.subprocess.Process` in `self._running_processes` and returns a list of integer PIDs.
  - [x] Add a mechanism (e.g., flag or callback) to allow the monitor to signal that a subprocess is being intentionally killed due to resource constraints.
- [x] 4. Integrate with Runner (AC: 4, 5)
  - [x] In `src/bmad_orch/engine/runner.py`, initialize and start `ResourceMonitor` at the beginning of `_run_internal`.
  - [x] Establish a mechanism for the runner to catch or await the `ResourceError` from the background monitor task (e.g., using `asyncio.FIRST_COMPLETED` with `asyncio.wait`).
  - [x] Ensure `ResourceMonitor` is stopped cleanly in the `finally` block of `_run_internal`. Explicitly catch `asyncio.CancelledError` in `stop()` to prevent warning leaks.
  - [x] Coordinate with `CycleExecutor` error handling to prevent duplicate error flows. The runner must skip normal subprocess error handling when the resource kill flag is set.
- [x] 5. Verification and Testing (AC: 1-7)
  - [x] Create `tests/test_resources.py` to verify threshold detection, polling interval, and event emission.
  - [x] Mock `psutil` and `asyncio.subprocess.Process` to simulate resource breaches. Ensure mocking handles both enabled and no-op modes explicitly.
  - [x] Verify that `ResourceError` correctly propagates from the background task to the runner and triggers `_handle_impactful_error`.
  - [x] Test race condition: `process.kill()` on an already-exited process should catch `NoSuchProcess` gracefully.
  - [x] Test the no-op fallback behavior when `psutil` raises `ImportError`.
  - [x] Test that `stop()` properly cancels and awaits the polling task without leaking asyncio task warnings, even when cancelled externally.
  - [x] Test metric gathering robustly handles `psutil.NoSuchProcess`, `psutil.AccessDenied`, and `psutil.ZombieProcess`.

## Dev Notes

### Technical Requirements
- **Psutil Async Pattern:** Use `psutil.cpu_percent(interval=None)`. The first call for *each specific process* will return 0.0 and should be used to initialize the state; subsequent calls in the poll loop will return usage since the last poll. Ensure newly spawned subprocesses are initialized immediately before being included in the aggregate sum.
- **Process Tree Monitoring:** Direct `psutil` calls are acceptable for 1-2 provider subprocesses, but you must recursively query `.children(recursive=True)` to catch nested runaway processes.
- **Memory Tracking:** Use `proc.memory_info().rss` for resident set size. Sum RSS across all tracked processes (orchestrator + subprocesses trees) and compare `(total_rss / psutil.virtual_memory().total) * 100` against the configured threshold. (Note: This measures host memory. In containerized environments, this will monitor host thresholds, which is acceptable for this iteration).
- **CPU Aggregation:** Sum `cpu_percent(interval=None)` across all tracked processes. Note this can exceed 100% on multi-core systems. The threshold applies to the aggregate sum, hence validation must allow > 100.0.
- **Event Emission:** Emit `ResourceThresholdBreached(resource_name="cpu", current_value=usage, threshold=80.0)` asynchronously (e.g., via `asyncio.create_task()` or equivalent non-blocking mechanism).
- **Exception Propagation:** An unawaited background asyncio task will swallow exceptions. You must explicitly route the `ResourceError` to the main loop either via an asyncio Event, an exception queue, or by running the cycle execution and the monitor task concurrently using `asyncio.wait(..., return_when=asyncio.FIRST_COMPLETED)`.

### Architecture Compliance
- **Dependency Isolation:** `src/bmad_orch/engine/resources.py` is part of the core engine and should only import from allowed core modules (psutil is allowed).
- **Subprocess Cleanup:** When a violation occurs, the monitor kills the specific offending subprocess tree. The `Runner`'s emergency flow will then clean up any remaining processes. Handle `psutil.NoSuchProcess` and related exceptions when the target process exits between detection and kill.
- **Async Safety:** The polling task must be properly cancelled during `stop()` and awaited (to suppress `Task was destroyed but it is pending` warnings). Wrap the await in try/except `asyncio.CancelledError`.
- **Import Safety:** Guard `import psutil` with a try/except. If psutil is unavailable, the monitor should log a warning and operate in a disabled/no-op mode rather than crashing the orchestrator.
- **Double Error Flow Prevention:** When the monitor kills a subprocess, the CycleExecutor will observe the process exit. The runner must distinguish monitor-initiated kills from unexpected subprocess failures to avoid triggering two independent error flows. Set a shared flag *before* the kill to inform the executor to expect the termination.

### Design Decisions
- **CPU monitoring scope expansion:** NFR8 only mandates memory monitoring. This story adds CPU threshold monitoring as a complementary safeguard. This is a deliberate design decision beyond NFR8's requirements.
- **Control flow:** The monitor both emits a `ResourceThresholdBreached` event (for observability) AND raises/propagates a `ResourceError` (for control flow). The runner catches the error and triggers the emergency flow. These are complementary mechanisms, not alternatives.

### Project Structure Notes
- **Resource Monitor:** `src/bmad_orch/engine/resources.py` (New file)
- **Config Schema:** `src/bmad_orch/config/schema.py`
- **Cycle Executor:** `src/bmad_orch/engine/cycle.py`
- **Runner:** `src/bmad_orch/engine/runner.py`
- **Tests:** `tests/test_resources.py`

### References
- [Source: _bmad-output/planning-artifacts/epics/epic-4-reliable-unattended-execution.md#Story 4.3]
- [Source: _bmad-output/planning-artifacts/architecture/core-architectural-decisions.md#Resource Monitoring]
- [Source: _bmad-output/planning-artifacts/prd/non-functional-requirements.md#Resource Management]
- [Source: src/bmad_orch/engine/events.py#ResourceThresholdBreached]

## Dev Agent Record

### Agent Model Used
Gemini 2.0 Flash

### Debug Log References
- Implementation of ResourceMonitor with psutil.
- Integration with CycleExecutor and Runner.
- Verification via unit and integration tests.

### Completion Notes List
- All tasks completed.
- AC 1-7 satisfied.
- CPU and Memory thresholds monitored.
- Offending processes terminated on breach.
- ResourceError propagated to Runner for emergency flow.
- Graceful degradation if psutil is missing.

### File List
- `src/bmad_orch/config/schema.py`
- `src/bmad_orch/engine/resources.py`
- `src/bmad_orch/engine/cycle.py`
- `src/bmad_orch/engine/runner.py`
- `tests/test_config/test_resource_schema.py`
- `tests/test_resources.py`

## Change Log
- Implement resource monitoring subsystem. (Date: 2026-03-15)
- Code review fixes: Added psutil.ZombieProcess to all exception handlers, implemented CPU initialization tracking for new subprocess PIDs to prevent under-reporting on first poll, added ZombieProcess test, fixed mock exception base classes in tests. (Date: 2026-03-15)

## Status
done
