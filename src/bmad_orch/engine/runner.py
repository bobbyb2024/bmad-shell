import pathlib
import logging
import uuid
from typing import Optional, Mapping

from bmad_orch.config.schema import OrchestratorConfig
from bmad_orch.config.template import TemplateResolver
from bmad_orch.engine.emitter import EventEmitter
from bmad_orch.engine.cycle import CycleExecutor
from bmad_orch.state.manager import StateManager
from bmad_orch.state.schema import RunState
from bmad_orch.types import StepOutcome

logger = logging.getLogger(__name__)

class Runner:
    """The core engine that executes the orchestration plan."""
    
    def __init__(self, config: OrchestratorConfig, state_path: Optional[pathlib.Path] = None) -> None:
        self.config = config
        self.state_path = state_path
        # If state_path is None, the runner should operate in-memory without persistence (Task 3.1)
        self.state: Optional[RunState] = None
        
        # Initialize support subsystems
        self.emitter = EventEmitter()
        self.state_manager = StateManager()
        self.template_resolver = TemplateResolver()

    async def run(self, dry_run: bool = False, template_context: Optional[Mapping[str, str]] = None) -> None:
        """Execute the orchestration plan.
        
        If dry_run is true, performs a full walk of the execution plan without calling providers.
        """
        template_context = template_context or {}
        
        if dry_run:
            from bmad_orch.engine.events import CycleStarted, StepStarted, StepCompleted, CycleCompleted
            from bmad_orch.types import StepType
            
            logger.info("Starting dry run...")
            for cycle_id, cycle in self.config.cycles.items():
                for rep_idx in range(cycle.repeat):
                    cycle_num = rep_idx + 1
                    provider_name = self.config.providers[cycle.steps[0].provider].name
                    self.emitter.emit(CycleStarted(cycle_number=cycle_num, provider_name=provider_name))
                    
                    for step_idx, step in enumerate(cycle.steps):
                        if rep_idx > 0 and step.type == StepType.GENERATIVE:
                            continue
                            
                        step_name = f"{step.skill}_{step_idx}"
                        self.emitter.emit(StepStarted(step_name=step_name, step_index=step_idx))
                        # In dry run, we assume success
                        self.emitter.emit(StepCompleted(step_name=step_name, step_index=step_idx, success=True))
                        
                    self.emitter.emit(CycleCompleted(cycle_number=cycle_num, provider_name=provider_name, success=True))
            return

        # Real execution logic
        # Load or initialize state
        if self.state_path:
            self.state = self.state_manager.load(self.state_path)
        else:
            # In-memory fresh state if no path
            self.state = RunState(run_id=str(uuid.uuid4()))

        executor = CycleExecutor(
            self.emitter,
            self.state_manager,
            self.template_resolver,
            self.config,
            self.state_path or pathlib.Path("/dev/null") # Dummy path if in-memory
        )

        for cycle_id, cycle_config in self.config.cycles.items():
            self.state = await executor.execute_cycle(
                cycle_id, 
                cycle_config, 
                self.state, 
                template_context
            )
            
            # AC10: Determine cycle failure by inspecting last CycleRecord
            if self.state.run_history:
                last_cycle = self.state.run_history[-1]
                if last_cycle.outcome == StepOutcome("failure"):
                    # Abort remaining cycles on failure
                    logger.error(f"Cycle {cycle_id} failed. Aborting remaining cycles.")
                    break
