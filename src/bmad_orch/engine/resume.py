import logging
import pathlib
from datetime import UTC, datetime

from bmad_orch.engine.logs import consolidate_logs
from bmad_orch.state.manager import StateManager
from bmad_orch.state.schema import RunState, RunStatus
from bmad_orch.types import StepOutcome

logger = logging.getLogger(__name__)

def prepare_rerun(state: RunState) -> tuple[str, int, dict[str, str]]:
    """Option 1: Prepare state to re-run from the failure point.
    
    Returns (start_cycle_id, start_step_index, template_context).
    """
    if not state.failure_point:
        raise ValueError("Cannot re-run: failure_point is missing in state.")
    
    # failure_point format: cycle:cycle_id:rep_num/step:step_id_index
    # Example: cycle:story:1/step:implement_0
    try:
        parts = state.failure_point.split("/")
        cycle_part = parts[0].split(":")
        cycle_id = cycle_part[1]
        
        step_part = parts[1].split(":")
        # The step_id_index usually looks like "skill_0", we want the 0
        step_id = step_part[1]
        step_index = int(step_id.split("_")[-1])
        
        # Restore template_context from state
        return cycle_id, step_index, dict(state.template_context)
    except (IndexError, ValueError) as e:
        raise ValueError(f"Invalid failure_point format: {state.failure_point}") from e

def prepare_skip(state: RunState, config_cycles: list[str]) -> tuple[str, int, dict[str, str]]:
    """Option 2: Prepare state to skip the failed step.

    Records a SKIPPED outcome in the state history and returns
    (start_cycle_id, start_step_index, template_context).
    """
    if not state.failure_point:
        raise ValueError("Cannot skip: failure_point is missing in state.")

    try:
        parts = state.failure_point.split("/")
        cycle_part = parts[0].split(":")
        cycle_id = cycle_part[1]
        rep_num = int(cycle_part[2])

        step_part = parts[1].split(":")
        step_id = step_part[1]
        step_index = int(step_id.split("_")[-1])

        # Record SKIPPED entry in state for the failure point (AC4)
        rep_id = f"{cycle_id}:{rep_num}"
        from bmad_orch.state.schema import StepRecord
        skipped_step = StepRecord(
            step_id=step_id,
            provider_name="[Skipped]",
            outcome=StepOutcome.SKIPPED,
            timestamp=datetime.now(UTC),
        )

        # Persist the SKIPPED record into the cycle's step history
        state_mgr = StateManager()
        try:
            updated_state = state_mgr.record_step(state, rep_id, skipped_step)
            # Update the in-memory state so callers see the change
            state.run_history = updated_state.run_history
            
            # Consolidate logs after modifying state in the resume flow
            consolidate_logs(state, pathlib.Path("_bmad-output/implementation-artifacts"))
        except Exception:
            logger.warning(f"Could not record SKIPPED step for {rep_id} (cycle may not exist in history)")

        return cycle_id, step_index + 1, dict(state.template_context)
    except (IndexError, ValueError) as e:
        raise ValueError(f"Invalid failure_point format: {state.failure_point}") from e

def prepare_restart_cycle(state: RunState) -> tuple[str, int, dict[str, str]]:
    """Option 3: Prepare state to restart the failed cycle from step 1.
    
    Returns (start_cycle_id, start_step_index, template_context).
    """
    if not state.failure_point:
        raise ValueError("Cannot restart cycle: failure_point is missing in state.")

    try:
        parts = state.failure_point.split("/")
        cycle_part = parts[0].split(":")
        cycle_id = cycle_part[1]
        rep_num = int(cycle_part[2])
        rep_id = f"{cycle_id}:{rep_num}"
        
        # Find the cycle record to get context_snapshot
        snapshot = None
        for cycle in state.run_history:
            if cycle.cycle_id == rep_id:
                snapshot = cycle.context_snapshot
                break
        
        if snapshot is None:
            logger.warning(f"No context_snapshot found for {rep_id}, using current template_context.")
            snapshot = dict(state.template_context)
            
        return cycle_id, 0, snapshot
    except (IndexError, ValueError) as e:
        raise ValueError(f"Invalid failure_point format: {state.failure_point}") from e

def prepare_start_fresh(state_path: pathlib.Path) -> None:
    """Option 4: Backup existing state and prepare for fresh start.
    
    This actually modifies the file system.
    """
    if state_path.exists():
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        # AC6: bmad-orch-state-[timestamp].json.bak
        bak_name = f"{state_path.stem}-{timestamp}{state_path.suffix}.bak"
        bak_path = state_path.parent / bak_name
        state_path.rename(bak_path)
        logger.info(f"Backed up state to {bak_path}")

def get_resume_context(state: RunState) -> dict[str, str]:
    """Extracts context for the resume screen."""
    return {
        "halted_at": state.halted_at.isoformat() if state.halted_at else "[Unknown]",
        "failure_point": state.failure_point or "[Unknown]",
        "failure_reason": state.failure_reason or "[Unknown]",
        "error_type": state.error_type or "[Unknown]",
        "completed_cycles": str(len([c for c in state.run_history if c.outcome == StepOutcome.SUCCESS])),
        "completed_steps": str(sum(len([s for s in c.steps if s.outcome == StepOutcome.SUCCESS]) for c in state.run_history)),
    }
