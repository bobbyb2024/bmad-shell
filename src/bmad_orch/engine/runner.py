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
from bmad_orch.exceptions import GitError, classify_error
from bmad_orch.git import GitClient
from bmad_orch.state.manager import StateManager
from bmad_orch.state.schema import RunState, RunStatus
from bmad_orch.types import ErrorSeverity, StepOutcome

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
        self.git_client: GitClient | None = None
        self._executor: CycleExecutor | None = None
        self._in_emergency_flow = False

    @property
    def in_emergency_flow(self) -> bool:
        """Whether the runner is currently executing the emergency halt sequence."""
        return self._in_emergency_flow

    async def _init_git(self) -> None:
        """Initialize GitClient if enabled and validate environment."""
        if not self.config.git.enabled:
            return

        # Initialize GitClient with repo validation
        self.git_client = await GitClient.create()
        
        # AC10: Validate dynamic output paths are within the git repo
        repo_root = self.git_client.repo_path.resolve()
        
        output_paths = [pathlib.Path("_bmad-output").resolve()]
        if self.state_path:
            output_paths.append(self.state_path.parent.resolve())

        for path in output_paths:
            if repo_root not in path.parents and path != repo_root:
                from bmad_orch.exceptions import ConfigError
                raise ConfigError(f"Output path '{path}' is outside the git repository root '{repo_root}'")

    async def run(self, dry_run: bool = False, template_context: Mapping[str, str] | None = None) -> None:
        """Execute the orchestration plan.
        
        If dry_run is true, performs a full walk of the execution plan without calling providers.
        """
        try:
            await self._run_internal(dry_run, template_context)
        except asyncio.CancelledError:
            logger.info("Execution cancelled by user.")
            await self._handle_impactful_error(None, is_abort=True)
            raise
        except Exception as e:
            classification = classify_error(e)
            if classification.severity == ErrorSeverity.IMPACTFUL:
                logger.error(f"Impactful error detected: {e}")
                await self._handle_impactful_error(e)
            raise

    async def _run_internal(self, dry_run: bool = False, template_context: Mapping[str, str] | None = None) -> None:
        """Internal run logic."""
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

        # Initialize git if enabled
        await self._init_git()

        if self.state_path:
            self.state = self.state_manager.load(self.state_path)
            new_ctx = dict(self.state.template_context)
            new_ctx.update(template_context)
            self.state = self.state.model_copy(update={"template_context": new_ctx})
        else:
            self.state = RunState(run_id=str(uuid.uuid4()), template_context=dict(template_context))

        self.state.update_status(RunStatus.RUNNING)

        executor = CycleExecutor(
            self.emitter,
            self.state_manager,
            self.prompt_resolver,
            self.config,
            self.state_path or pathlib.Path("/dev/null"),
            adapter_factory=self.adapter_factory,
            git_client=self.git_client,
        )
        self._executor = executor

        from bmad_orch.engine.resources import ResourceMonitor
        monitor = ResourceMonitor(self.config.resources, self.emitter)
        await monitor.start(executor)

        cycle_keys = list(self.config.cycles.keys())
        run_success = True

        try:
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
                        
                # Wrap execute_cycle in a task so we can wait for it along with the monitor
                cycle_task = asyncio.create_task(executor.execute_cycle(
                    cycle_id, 
                    cycle_config, 
                    self.state, 
                    self.state.template_context
                ))
                
                # If monitor is active, wait for either to finish
                tasks_to_wait = {cycle_task}
                if monitor._task:
                    tasks_to_wait.add(monitor._task)
                
                done, pending = await asyncio.wait(
                    tasks_to_wait,
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                if cycle_task in done:
                    self.state = await cycle_task
                else:
                    # Monitor task must have failed (it's a loop)
                    # We cancel the cycle task and raise the monitor error
                    cycle_task.cancel()
                    try:
                        await cycle_task
                    except asyncio.CancelledError:
                        pass
                    
                    if monitor._task in done:
                        exc = monitor._task.exception()
                        if exc:
                            raise exc
                        else:
                            raise RuntimeError("ResourceMonitor task finished unexpectedly")

                if self.state.run_history:
                    last_cycle = self.state.run_history[-1]
                    if last_cycle.outcome == StepOutcome("failure"):
                        logger.error(f"Cycle type {cycle_id} failed. Aborting remaining cycle types.")
                        run_success = False
                        break
                
                # AC2: pause_between_cycle_types
                if i < len(cycle_keys) - 1 and self.config.pauses.between_cycle_types > 0:
                    await asyncio.sleep(self.config.pauses.between_cycle_types)
        finally:
            await monitor.stop()
                
        # AC6: Emit RunCompleted
        self._emit_run_completed(start_time, run_success)

        # AC5: Handle git push at end
        if self.git_client and self.config.git.push_at == "end":
            try:
                await self.git_client.push(
                    remote=self.config.git.remote,
                    branch=self.config.git.branch
                )
            except Exception as e:
                logger.warning(f"Git push failed at end: {e}")

    def _emit_run_completed(self, start_time: float, run_success: bool) -> None:
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

    async def _handle_impactful_error(self, error: Exception | None, is_abort: bool = False) -> None:
        """Handles emergency halt sequence when an impactful error or abort occurs."""
        if self._in_emergency_flow:
            return
        
        self._in_emergency_flow = True
        try:
            # Shield ensures that once the emergency flow starts, it won't be cancelled
            # by a second SIGINT or task cancellation.
            await asyncio.shield(self._emergency_halt(error, is_abort))
        finally:
            self._in_emergency_flow = False

    async def _emergency_halt(self, error: Exception | None, is_abort: bool = False) -> None:
        """Internal emergency halt logic protected by shield."""
        failure_point = "cycle:1/step:initialization"
        if self.state and self.state.run_history:
            last_cycle = self.state.run_history[-1]
            if last_cycle.steps:
                last_step = last_cycle.steps[-1]
                failure_point = f"cycle:{last_cycle.cycle_id}/step:{last_step.step_id}"
            else:
                failure_point = f"cycle:{last_cycle.cycle_id}/step:start"

        error_type = "UserAbort" if is_abort else (type(error).__name__ if error else "UnknownError")
        failure_reason = str(error) if error else ("Execution Halted by User" if is_abort else "Unknown failure")

        # 1. Record halt in state and save atomically
        if self.state and self.state_path:
            try:
                self.state = self.state_manager.record_halt(
                    state=self.state,
                    failure_point=failure_point,
                    failure_reason=failure_reason,
                    error_type=error_type,
                    path=self.state_path,
                    is_abort=is_abort
                )
            except Exception as e:
                logger.error(f"Failed to record halt in state: {e}")

        # 2. Kill subprocesses
        if self._executor:
             await self._executor.cleanup_processes()

        # 3. Git emergency commit + push
        if self.git_client and self.config.git.enabled and not isinstance(error, GitError):
            try:
                # Sequential git ops, skip remaining if one fails
                await self.git_client.add(["."])
                await self.git_client.commit(
                    message=f"chore(bmad-orch): emergency commit — {failure_point} — {error_type}"
                )
                await self.git_client.push(
                    remote=self.config.git.remote,
                    branch=self.config.git.branch
                )
            except Exception as e:
                logger.error(f"Emergency git operation failed: {e}", exc_info=True)
