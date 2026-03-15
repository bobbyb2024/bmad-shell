import asyncio
import logging
import pathlib
import time
import uuid
from collections.abc import Callable, Mapping
from typing import Any

from bmad_orch.config.schema import OrchestratorConfig
from bmad_orch.engine.cycle import CycleExecutor
from bmad_orch.engine.emitter import EventEmitter
from bmad_orch.engine.events import RunCompleted
from bmad_orch.engine.prompt_resolver import PromptResolver
from bmad_orch.state.manager import StateManager
from bmad_orch.state.schema import RunState
from bmad_orch.types import StepOutcome

logger = logging.getLogger(__name__)

class Runner:
    """The core engine that executes the orchestration plan."""
    
    def __init__(
        self,
        config: OrchestratorConfig,
        state_path: pathlib.Path | None = None,
        adapter_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.config = config
        self.state_path = state_path
        self.state: RunState | None = None
        self.adapter_factory = adapter_factory

        self.emitter = EventEmitter()
        self.state_manager = StateManager()
        self.prompt_resolver = PromptResolver()

    async def run(self, dry_run: bool = False, template_context: Mapping[str, str] | None = None) -> None:
        """Execute the orchestration plan.
        
        If dry_run is true, performs a full walk of the execution plan without calling providers.
        """
        start_time = time.time()
        template_context = template_context or {}
        
        if dry_run:
            from bmad_orch.engine.events import CycleCompleted, CycleStarted, StepCompleted, StepStarted
            from bmad_orch.types import StepType
            
            logger.info("Starting dry run...")
            for _cycle_id, cycle in self.config.cycles.items():
                for rep_idx in range(cycle.repeat):
                    cycle_num = rep_idx + 1
                    provider_name = self.config.providers[cycle.steps[0].provider].name
                    self.emitter.emit(CycleStarted(cycle_number=cycle_num, provider_name=provider_name))
                    
                    for step_idx, step in enumerate(cycle.steps):
                        if rep_idx > 0 and step.type == StepType.GENERATIVE:
                            continue
                            
                        step_name = f"{step.skill}_{step_idx}"
                        self.emitter.emit(StepStarted(step_name=step_name, step_index=step_idx))
                        self.emitter.emit(StepCompleted(step_name=step_name, step_index=step_idx, success=True))
                        
                    self.emitter.emit(CycleCompleted(cycle_number=cycle_num, provider_name=provider_name, success=True))
            return

        if self.state_path:
            self.state = self.state_manager.load(self.state_path)
            new_ctx = dict(self.state.template_context)
            new_ctx.update(template_context)
            self.state = self.state.model_copy(update={"template_context": new_ctx})
        else:
            self.state = RunState(run_id=str(uuid.uuid4()), template_context=dict(template_context))

        executor = CycleExecutor(
            self.emitter,
            self.state_manager,
            self.prompt_resolver,
            self.config,
            self.state_path or pathlib.Path("/dev/null"),
            adapter_factory=self.adapter_factory,
        )

        cycle_keys = list(self.config.cycles.keys())
        run_success = True

        for i, cycle_id in enumerate(cycle_keys):
            cycle_config = self.config.cycles[cycle_id]
            
            # AC7: Crash-resumption
            if self.state.run_history:
                success_reps = sum(
                    1 for r in self.state.run_history 
                    if r.cycle_id.startswith(f"{cycle_id}:") and r.outcome == StepOutcome("success")
                )
                if success_reps == cycle_config.repeat:
                    logger.info(f"Skipping completed cycle type {cycle_id}")
                    continue
                    
            self.state = await executor.execute_cycle(
                cycle_id, 
                cycle_config, 
                self.state, 
                self.state.template_context
            )
            
            if self.state.run_history:
                last_cycle = self.state.run_history[-1]
                if last_cycle.outcome == StepOutcome("failure"):
                    logger.error(f"Cycle type {cycle_id} failed. Aborting remaining cycle types.")
                    run_success = False
                    break
            
            # AC2: pause_between_cycle_types
            if i < len(cycle_keys) - 1 and self.config.pauses.between_cycle_types > 0:
                await asyncio.sleep(self.config.pauses.between_cycle_types)
                
        # AC6: Emit RunCompleted
        elapsed = time.time() - start_time
        total_steps = sum(len(c.steps) for c in self.state.run_history) if self.state else 0
        total_cycles = len(self.state.run_history) if self.state else 0
        
        error_count = 0
        if self.state:
            for c in self.state.run_history:
                for s in c.steps:
                    if s.outcome == StepOutcome("failure"):
                        error_count += 1
        
        self.emitter.emit(RunCompleted(
            success=run_success,
            total_cycles=total_cycles,
            total_step_count=total_steps,
            elapsed_time=elapsed,
            error_count=error_count
        ))
