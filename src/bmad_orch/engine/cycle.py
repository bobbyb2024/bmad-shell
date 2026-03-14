import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from structlog.contextvars import bind_contextvars, unbind_contextvars

from bmad_orch.config.schema import CycleConfig, OrchestratorConfig, StepConfig
from bmad_orch.config.template import TemplateResolver
from bmad_orch.engine.emitter import EventEmitter
from bmad_orch.engine.events import (
    CycleCompleted,
    CycleStarted,
    EscalationChanged,
    EscalationLevel,
    ErrorOccurred,
    ProviderOutput,
    StepCompleted,
    StepStarted,
)
from bmad_orch.exceptions import ConfigError
from bmad_orch.providers import get_adapter
from bmad_orch.state.manager import StateManager
from bmad_orch.state.schema import ErrorRecord, RunState, StepRecord
from bmad_orch.types import StepOutcome, StepType

logger = logging.getLogger(__name__)

class CycleExecutor:
    def __init__(
        self,
        emitter: EventEmitter,
        state_manager: StateManager,
        template_resolver: TemplateResolver,
        config: OrchestratorConfig,
        state_path: Path,
    ) -> None:
        self.emitter = emitter
        self.state_manager = state_manager
        self.template_resolver = template_resolver
        self.config = config
        self.state_path = state_path

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
                    recoverable=False
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
                        recoverable=False
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
                    recoverable=False
                ))
                return state

            # AC3: Repeat loop runtime guard
            if cycle_config.repeat <= 0:
                self.emitter.emit(ErrorOccurred(
                    error_type="ConfigError",
                    message=f"Invalid repeat value: {cycle_config.repeat}",
                    source=cycle_id,
                    recoverable=False
                ))
                return state

            # AC6: provider_name for CycleStarted/CycleCompleted is always from first step
            first_provider_name = self.config.providers[cycle_config.steps[0].provider].name

            for cycle_idx in range(cycle_config.repeat):
                cycle_num = cycle_idx + 1
                rep_id = f"{cycle_id}:{cycle_num}"

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
                            resolved_prompt = self.template_resolver.resolve(
                                step.prompt, template_context, step_name=step_name
                            )
                        except ConfigError as e:
                            self.emitter.emit(ErrorOccurred(
                                error_type="ConfigError",
                                message=str(e),
                                source=step_name,
                                recoverable=False
                            ))
                            state = await self._record_failure(state, rep_id, step_name, provider_name, str(e))
                            self.emitter.emit(CycleCompleted(cycle_number=cycle_num, provider_name=first_provider_name, success=False))
                            return state

                        # Execute Step
                        success, output = await self._execute_step(step, resolved_prompt)

                        # AC6: Escalation detection
                        if "ESCALATE: ATTENTION" in output:
                            self.emitter.emit(EscalationChanged(step_name=step_name, previous_level=None, new_level=EscalationLevel.ATTENTION))
                        elif "ESCALATE: ACTION" in output:
                            self.emitter.emit(EscalationChanged(step_name=step_name, previous_level=None, new_level=EscalationLevel.ACTION))

                        # AC7, AC10: Record & Persist
                        outcome = StepOutcome("success") if success else StepOutcome("failure")
                        step_record = StepRecord(
                            step_id=step_name,
                            provider_name=provider_name,
                            outcome=outcome,
                            timestamp=datetime.now(timezone.utc)
                        )
                        state = self.state_manager.record_step(state, rep_id, step_record)
                        self.state_manager.save(state, self.state_path)
                        
                        self.emitter.emit(StepCompleted(step_name=step_name, step_index=step_idx, success=success))

                        if not success:
                            self.emitter.emit(ErrorOccurred(
                                error_type="StepError",
                                message=f"Step {step_name} failed: {output}",
                                source=step_name,
                                recoverable=False,
                            ))
                            state = self.state_manager.finish_cycle(state, rep_id, StepOutcome("failure"))
                            self.state_manager.save(state, self.state_path)
                            self.emitter.emit(CycleCompleted(cycle_number=cycle_num, provider_name=first_provider_name, success=False))
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
                self.emitter.emit(CycleCompleted(cycle_number=cycle_num, provider_name=first_provider_name, success=True))

                # AC5: Cycle Pauses
                if cycle_idx < cycle_config.repeat - 1 and cycle_config.pause_between_cycles:
                    await asyncio.sleep(cycle_config.pause_between_cycles)

            return state
        finally:
            unbind_contextvars("cycle_id")

    async def _execute_step(self, step: StepConfig, resolved_prompt: str) -> tuple[bool, str]:
        """Execute the step using the configured provider adapter."""
        provider_config = self.config.providers[step.provider]
        adapter = get_adapter(provider_config.name, **provider_config.model_dump())
        
        full_output = []
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
            return True, final_content
        except Exception as e:
            logger.error(f"Step execution failed: {e}")
            return False, str(e)

    async def _record_failure(self, state: RunState, rep_id: str, step_id: str, provider_name: str, message: str) -> RunState:
        step_record = StepRecord(
            step_id=step_id,
            provider_name=provider_name,
            outcome=StepOutcome("failure"),
            timestamp=datetime.now(timezone.utc),
            error=ErrorRecord(message=message, error_type="ConfigError"),
        )
        state = self.state_manager.record_step(state, rep_id, step_record)
        state = self.state_manager.finish_cycle(state, rep_id, StepOutcome("failure"))
        self.state_manager.save(state, self.state_path)
        return state
