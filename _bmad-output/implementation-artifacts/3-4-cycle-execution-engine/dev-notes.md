# Dev Notes

- **File Location:** `src/bmad_orch/engine/cycle.py`.
- **Naming:** Class `CycleExecutor`. Update `engine/__init__.py` exports accordingly.
- **Constructor:** `CycleExecutor.__init__(self, emitter: EventEmitter, state_manager: StateManager, template_resolver: TemplateResolver, config: OrchestratorConfig, state_path: Path)`.
- **Events:** `CycleStarted` and `CycleCompleted` use the `provider_name` of the first step (index 0 in the step list). `StepStarted` and `StepCompleted` MUST use `step_name` (matching the field name in `events.py`). `cycle_number` for cycle events is 1-indexed.
- **State:** `StepRecord` requires `step_id` (generated as `{step.skill}_{step_index}`), `provider_name`, `outcome` (`StepOutcome("success")` or `StepOutcome("failure")`), and current UTC `timestamp` (as a `datetime` object).
- **Prompts:** Build context for `TemplateResolver` from a caller-provided `Mapping[str, str]`. **Note:** `RunState` does NOT have a `status` field. Failure is communicated by the `StepRecord.outcome` being `StepOutcome("failure")` and the `CycleCompleted(success=False)` event. The caller inspects `run_history` to determine success/failure.
- **Step Type Field:** `StepConfig` uses the field name `type` (not `step_type`) with values from the `StepType` enum (`StepType.GENERATIVE`, `StepType.VALIDATION`). Access via `step.type`.
- **Step Execution:** The engine MUST validate `StepConfig.provider` exists in `OrchestratorConfig.providers` and has a non-empty (truthy) `name` before execution (AC12). Provider validation should happen upfront for all steps before emitting `CycleStarted`. Note: actual step execution (provider API call / subprocess) is **out of scope** for this story — the engine calls a placeholder `async _execute_step(step: StepConfig, resolved_prompt: str) -> bool` method that returns `True` for success and will be implemented in a later story.
- **Logging Teardown:** Inner step `finally` blocks MUST use `unbind_contextvars("step_name", "provider_name")` (not `clear_contextvars()`). Only the outer cycle `finally` should use `unbind_contextvars("cycle_id")` to preserve global context (e.g., `run_id`).
- **Pauses:** `pause_between_steps` applies *between* steps. `pause_between_cycles` applies *between* repetitions. Do not double-pause or pause after the final operation.

## Project Structure Notes

- `src/bmad_orch/engine/cycle.py` (New)
- `src/bmad_orch/engine/runner.py` (Update)
- `tests/test_engine/test_cycle.py` (New)

## References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.4]
- [Source: _bmad-output/planning-artifacts/architecture.md#Engine Architecture]
- [Source: _bmad-output/implementation-artifacts/3-1-event-emitter-event-types/]
- [Source: _bmad-output/implementation-artifacts/3-2-state-manager-atomic-persistence/]
- [Source: _bmad-output/implementation-artifacts/3-3-structured-logging-subsystem/]
- [Source: _bmad-output/implementation-artifacts/1-4-prompt-template-variable-registry/]
