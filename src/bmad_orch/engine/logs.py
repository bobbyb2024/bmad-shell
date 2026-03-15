import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from bmad_orch.state.schema import RunState

logger = logging.getLogger(__name__)


def consolidate_logs(state: RunState, output_dir: Path) -> Path:
    """
    Consolidates all step records from the run history into a single log file.
    
    This function is robust and should not raise exceptions to the caller.
    """
    run_id = state.run_id
    output_path = output_dir / f"{run_id}-cycle.log"
    
    try:
        # 1. Create parent directories
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 2. Collect all StepRecords with their cycle and step indices
        all_steps = []
        for cycle_idx, cycle in enumerate(state.run_history):
            for step_idx, step in enumerate(cycle.steps):
                # Ensure timestamp is UTC aware
                ts = step.timestamp
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                else:
                    ts = ts.astimezone(timezone.utc)
                
                all_steps.append({
                    "cycle_idx": cycle_idx,
                    "step_idx": step_idx,
                    "timestamp": ts,
                    "step": step
                })
        
        # 3. Sort by timestamp, then cycle_idx, then step_idx
        all_steps.sort(key=lambda x: (x["timestamp"], x["cycle_idx"], x["step_idx"]))
        
        # 4. Prepare log content
        lines = []
        # Metadata header
        lines.append(f"Run ID: {run_id}")
        lines.append(f"Config Hash: {state.config_hash or 'N/A'}")
        lines.append(f"Status: {state.status.value}")
        lines.append(f"Started At: {state.run_history[0].started_at.isoformat() if state.run_history else 'N/A'}")
        lines.append("-" * 80)
        
        # Step records
        for entry in all_steps:
            step = entry["step"]
            ts_iso = entry["timestamp"].strftime("%Y-%m-%dT%H:%M:%SZ")
            error_msg = f" {step.error.message}" if step.error else ""
            line = (
                f"[Cycle {entry['cycle_idx']}] "
                f"[{ts_iso}] "
                f"[{step.step_id}] "
                f"[{step.provider_name or 'None'}] "
                f"{step.outcome.value}"
                f"{error_msg}"
            )
            lines.append(line)
        
        content = "\n".join(lines) + "\n"
        
        # 5. Atomic write
        fd, temp_path = tempfile.mkstemp(dir=str(output_dir), prefix=f"{run_id}-", suffix=".tmp")
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(content)
            os.replace(temp_path, str(output_path))
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise
            
    except Exception as e:
        logger.error(f"Failed to consolidate logs for run {run_id}: {e}", exc_info=True)
        # We don't raise here to avoid blocking callers as per AC
        
    return output_path
