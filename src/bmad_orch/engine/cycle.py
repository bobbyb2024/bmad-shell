import asyncio
import logging
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from string import Template
from typing import Any

from structlog.contextvars import bind_contextvars, unbind_contextvars

from bmad_orch.config.schema import CycleConfig, OrchestratorConfig, StepConfig
from bmad_orch.engine.emitter import EventEmitter
from bmad_orch.engine.events import (
    CycleCompleted,
    CycleStarted,
    ErrorOccurred,
    EscalationChanged,
    EscalationLevel,
    ProviderOutput,
    StepCompleted,
    StepStarted,
)
from bmad_orch.engine.prompt_resolver import PromptResolver
from bmad_orch.exceptions import classify_error
from bmad_orch.git import GitClient
from bmad_orch.state.manager import StateManager
from bmad_orch.state.schema import ErrorRecord, RunState, StepRecord
from bmad_orch.types import StepOutcome, StepType

logger = logging.getLogger(__name__)

class CycleExecutor:
    def __init__(
        self,
        emitter: EventEmitter,
        state_manager: StateManager,
        prompt_resolver: PromptResolver,
        config: OrchestratorConfig,
        state_path: Path,
        adapter_factory: Callable[..., Any] | None = None,
        git_client: GitClient | None = None,
    ) -> None:
        self.emitter = emitter
        self.state_manager = state_manager
        self.prompt_resolver = prompt_resolver
        self.config = config
        self.state_path = state_path
        self.adapter_factory = adapter_factory
        self.git_client = git_client

    def log_error(self, error: Exception, next_action: str) -> None:
        classification = classify_error(error)
        log_msg = f"✗ [{str(error)}] — [{next_action}]"
        if classification.is_recoverable:
            logger.warning(log_msg, extra={"error_classification": classification.severity.name})
        else:
            logger.error(log_msg, extra={"error_classification": classification.severity.name})

    async def handle_error_async(self, error: Exception, process: 'asyncio.subprocess.Process | None' = None) -> None:
        classification = classify_error(error)
        if process:
            try:
                process.kill()
            except OSError:
                pass
            await process.wait()

        if not classification.is_recoverable:
            self.log_error(error, "Check provider configuration and logs")
            self.emitter.emit(ErrorOccurred(
                error_type=error.__class__.__name__,
                message=str(error),
                source="CycleExecutor",
                recoverable=False,
                suggested_action="Check provider configuration and logs",
            ))
        else:
            self.log_error(error, "Execution continues to the next retry or step")

    async def _handle_git_commit(self, granularity: str, name: str, success: bool) -> None:
        """Handle git commit based on configuration."""
        if not self.git_client or self.config.git.commit_at != granularity:
            return

        status = "success" if success else "failure"
        
        # Default template
        default_msg = "chore(bmad-orch): auto-commit after $granularity ($status) — $name"
        template_str = self.config.git.commit_message_template or default_msg
        template = Template(template_str)
        message = template.safe_substitute(granularity=granularity, status=status, name=name)

        try:
            paths_to_add = ["_bmad-output", "logs"]
            if self.state_path and self.state_path.exists():
                paths_to_add.append(str(self.state_path))
            
            await self.git_client.add(paths_to_add)
            await self.git_client.commit(message)
        except Exception as e:
            # Story AC8: log failure rather than failing silently, and don't fail the whole runner
            logger.warning(f"Git commit failed: {e}")

    async def _handle_git_push(self, granularity: str) -> None:
        """Handle git push based on configuration."""
        if not self.git_client or self.config.git.push_at != granularity:
            return

        try:
            await self.git_client.push(
                remote=self.config.git.remote,
                branch=self.config.git.branch
            )
        except Exception as e:
            # Story AC8: log failure as warning to prevent failing the entire orchestrator
            logger.warning(f"Git push failed: {e}")

    async def execute_cycle(
        self,
        cycle_id: str,
        cycle_config: CycleConfig,
        state: RunState,
        template_context: Mapping[str, str],
    ) -> RunState:
        bind_contextvars(cycle_id=cycle_id)
        try:
            # AC11 Upfront Validation
            if not cycle_config.steps:
                self.emitter.emit(ErrorOccurred(
                    error_type="ConfigError",
                    message="Cycle has zero steps",
                    source=cycle_id,
                    recoverable=False,
                    suggested_action="Add at least one step to the cycle configuration",
                ))
                return state

            # AC12 Upfront Provider Validation
            for i, step in enumerate(cycle_config.steps):
                step_name = f"{step.skill}_{i}"
                provider_config = self.config.providers.get(step.provider)
                if not provider_config or not provider_config.name:
                    error_msg = f"Provider {step.provider} not found or has no name"
                    self.emitter.emit(ErrorOccurred(
                        error_type="ConfigError",
                        message=error_msg,
                        source=step_name,
                        recoverable=False,
                        suggested_action="Verify provider exists in configuration",
                    ))
                    # AC12: Halt following AC10 failure protocol
                    # Start cycle for state tracking, but do NOT emit CycleStarted
                    # per AC6 (CycleStarted fires only AFTER upfront validation passes)
                    rep_id = f"{cycle_id}:1"
                    state = self.state_manager.start_cycle(state, rep_id)
                    state = await self._record_failure(state, rep_id, step_name, "unknown", error_msg)
                    self.emitter.emit(CycleCompleted(cycle_number=1, provider_name="unknown", success=False))
                    return state

            # AC11: Generative-only cycles on repetitions
            has_validation = any(s.type == StepType.VALIDATION for s in cycle_config.steps)
            if not has_validation and cycle_config.repeat > 1:
                self.emitter.emit(ErrorOccurred(
                    error_type="ConfigError",
                    message="Cycle has only generative steps but repeat > 1; iterations 1+ would be no-ops",
                    source=cycle_id,
                    recoverable=False,
                    suggested_action="Add a validation step or set repeat to 1",
                ))
                return state

            # AC3: Repeat loop runtime guard
            if cycle_config.repeat <= 0:
                self.emitter.emit(ErrorOccurred(
                    error_type="ConfigError",
                    message=f"Invalid repeat value: {cycle_config.repeat}",
                    source=cycle_id,
                    recoverable=False,
                    suggested_action="Set repeat to a positive integer",
                ))
                return state

            # AC6: provider_name for CycleStarted/CycleCompleted is always from first step
            first_provider_name = self.config.providers[cycle_config.steps[0].provider].name

            for cycle_idx in range(cycle_config.repeat):
                cycle_num = cycle_idx + 1
                rep_id = f"{cycle_id}:{cycle_num}"

                # AC7: Skip already successful repetition
                already_success = any(
                    r.cycle_id == rep_id and r.outcome == StepOutcome("success")
                    for r in state.run_history
                )
                if already_success:
                    logger.info(f"Skipping already successful cycle repetition {rep_id}")
                    continue

                state = self.state_manager.start_cycle(state, rep_id)
                self.emitter.emit(CycleStarted(cycle_number=cycle_num, provider_name=first_provider_name))

                # Step loop
                for step_idx, step in enumerate(cycle_config.steps):
                    # AC2: Step Type Logic
                    if cycle_idx > 0 and step.type == StepType.GENERATIVE:
                        continue

                    step_name = f"{step.skill}_{step_idx}"
                    provider_name = self.config.providers[step.provider].name
                    
                    bind_contextvars(step_name=step_name, provider_name=provider_name)
                    try:
                        self.emitter.emit(StepStarted(step_name=step_name, step_index=step_idx))

                        # AC8: Prompt Resolution
                        try:
                            resolved_prompt = self.prompt_resolver.resolve(
                                step.prompt, template_context
                            )
                        except Exception as e:
                            self.emitter.emit(ErrorOccurred(
                                error_type="ConfigError",
                                message=str(e),
                                source=step_name,
                                recoverable=False,
                                suggested_action="Fix the prompt template configuration",
                            ))
                            state = await self._record_failure(
                                state, rep_id, step_name, provider_name, str(e),
                            )
                            self.emitter.emit(CycleCompleted(
                                cycle_number=cycle_num, provider_name=first_provider_name, success=False,
                            ))
                            return state

                        # Execute Step
                        success, output, recoverable = await self._execute_step(step, resolved_prompt)

                        # Extract output variables
                        if success:
                            import re
                            # Common generic extraction: file path heuristic
                            paths = re.findall(r"(_bmad-output/\S+\.(?:md|yaml|yml|json|txt))", output)
                            if paths:
                                new_ctx = dict(state.template_context)
                                if "story" in cycle_id.lower() or "story" in step_name.lower():
                                    new_ctx["current_story_file"] = paths[-1]
                                elif "atdd" in cycle_id.lower() or "atdd" in step_name.lower():
                                    new_ctx["current_atdd_file"] = paths[-1]
                                state = state.model_copy(update={"template_context": new_ctx})

                        # AC6: Escalation detection
                        if "ESCALATE: ATTENTION" in output:
                            self.emitter.emit(EscalationChanged(
                                step_name=step_name, previous_level=None,
                                new_level=EscalationLevel.ATTENTION,
                            ))
                        elif "ESCALATE: ACTION" in output:
                            self.emitter.emit(EscalationChanged(
                                step_name=step_name, previous_level=None,
                                new_level=EscalationLevel.ACTION,
                            ))

                        # AC7, AC10: Record & Persist
                        outcome = StepOutcome("success") if success else StepOutcome("failure")
                        step_record = StepRecord(
                            step_id=step_name,
                            provider_name=provider_name,
                            outcome=outcome,
                            timestamp=datetime.now(UTC)
                        )
                        state = self.state_manager.record_step(state, rep_id, step_record)
                        self.state_manager.save(state, self.state_path)

                        self.emitter.emit(StepCompleted(step_name=step_name, step_index=step_idx, success=success))

                        # Handle git commit (step granularity)
                        await self._handle_git_commit("step", step_name, success)

                        if not success:
                            if recoverable:
                                # AC2: Recoverable error — logged already, continue to next step
                                continue
                            self.emitter.emit(ErrorOccurred(
                                error_type="StepError",
                                message=f"Step {step_name} failed: {output}",
                                source=step_name,
                                recoverable=False,
                                suggested_action="Check provider configuration and logs",
                            ))
                            state = self.state_manager.finish_cycle(state, rep_id, StepOutcome("failure"))
                            self.state_manager.save(state, self.state_path)
                            self.emitter.emit(CycleCompleted(
                                cycle_number=cycle_num, provider_name=first_provider_name, success=False,
                            ))
                            # Handle git commit and push (cycle granularity) on failure
                            await self._handle_git_commit("cycle", rep_id, False)
                            await self._handle_git_push("cycle")
                            return state

                        # AC4: Step Pauses
                        if step_idx < len(cycle_config.steps) - 1 and cycle_config.pause_between_steps:
                            # Check if ANY remaining steps will be executed in this repetition
                            remaining_steps = cycle_config.steps[step_idx+1:]
                            will_execute_more = False
                            for s in remaining_steps:
                                if not (cycle_idx > 0 and s.type == StepType.GENERATIVE):
                                    will_execute_more = True
                                    break
                            
                            if will_execute_more:
                                await asyncio.sleep(cycle_config.pause_between_steps)

                    finally:
                        unbind_contextvars("step_name", "provider_name")

                # AC6: CycleCompleted
                state = self.state_manager.finish_cycle(state, rep_id, StepOutcome("success"))
                self.state_manager.save(state, self.state_path)
                self.emitter.emit(CycleCompleted(
                    cycle_number=cycle_num, provider_name=first_provider_name, success=True,
                ))

                # Handle git commit and push (cycle granularity)
                await self._handle_git_commit("cycle", rep_id, True)
                await self._handle_git_push("cycle")

                # AC5: Cycle Pauses
                if cycle_idx < cycle_config.repeat - 1 and cycle_config.pause_between_cycles:
                    await asyncio.sleep(cycle_config.pause_between_cycles)

            return state
        finally:
            unbind_contextvars("cycle_id")

    async def _execute_step(self, step: StepConfig, resolved_prompt: str) -> tuple[bool, str, bool]:
        """Execute the step using the configured provider adapter.

        Returns (success, output, recoverable) where recoverable indicates
        whether a failure was transient and execution can continue.
        """
        provider_config = self.config.providers[step.provider]
        if self.adapter_factory is None:
            msg = "adapter_factory must be provided to execute steps"
            raise RuntimeError(msg)
        adapter = self.adapter_factory(
            provider_config.name, **provider_config.model_dump(exclude={"name"}),
        )

        full_output: list[str] = []
        try:
            async for chunk in adapter.execute(resolved_prompt):
                full_output.append(chunk.content)
                self.emitter.emit(ProviderOutput(
                    provider_name=provider_config.name,
                    content=chunk.content,
                    is_partial=True
                ))

            final_content = "".join(full_output)
            self.emitter.emit(ProviderOutput(
                provider_name=provider_config.name,
                content=final_content,
                is_partial=False
            ))
            return True, final_content, False
        except Exception as e:
            classification = classify_error(e)
            await self.handle_error_async(e, None)
            return False, str(e), classification.is_recoverable

    async def _record_failure(
        self, state: RunState, rep_id: str, step_id: str, provider_name: str, message: str,
    ) -> RunState:
        step_record = StepRecord(
            step_id=step_id,
            provider_name=provider_name,
            outcome=StepOutcome("failure"),
            timestamp=datetime.now(UTC),
            error=ErrorRecord(message=message, error_type="ConfigError"),
        )
        state = self.state_manager.record_step(state, rep_id, step_record)
        state = self.state_manager.finish_cycle(state, rep_id, StepOutcome("failure"))
        self.state_manager.save(state, self.state_path)
        return state
