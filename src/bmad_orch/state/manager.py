import json
import logging
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from bmad_orch.exceptions import StateError
from bmad_orch.state.schema import CycleRecord, RunState, StepRecord
from bmad_orch.types import StepOutcome

logger = logging.getLogger(__name__)

class StateManager:
    """Manages persistent state with atomic write strategy."""

    DEFAULT_STATE_FILE = "bmad-orch-state.json"
    EXPECTED_SCHEMA_VERSION = 1

    @staticmethod
    def _fresh_state(expected_hash: str | None = None) -> RunState:
        """Create a fresh RunState with a new run_id."""
        return RunState(run_id=str(uuid.uuid4()), config_hash=expected_hash)

    @staticmethod
    def load(path: Path | None = None, expected_hash: str | None = None) -> RunState:
        """Loads state from file, returning fresh state if file doesn't exist."""
        path = path or Path(StateManager.DEFAULT_STATE_FILE)

        # Cleanup stale temp files
        StateManager._cleanup_stale_temp_files(path)

        if not path.exists():
            return StateManager._fresh_state(expected_hash)

        # AC8: 0-byte file is a validation failure
        if path.stat().st_size == 0:
            logger.warning(f"State file {path} is empty. Treating as corrupt.")
            if StateManager._handle_corrupt_file(path):
                raise StateError(f"State file is empty (0-byte): {path}")
            return StateManager._fresh_state(expected_hash)

        try:
            with path.open(encoding="utf-8") as f:
                state = RunState.model_validate_json(f.read())

            # AC8: Schema version mismatch is a validation failure
            if state.schema_version != StateManager.EXPECTED_SCHEMA_VERSION:
                logger.error(
                    f"Schema version mismatch: expected {StateManager.EXPECTED_SCHEMA_VERSION}, "
                    f"got {state.schema_version}"
                )
                if StateManager._handle_corrupt_file(path):
                    raise StateError(
                        f"Schema version mismatch in {path}: "
                        f"expected {StateManager.EXPECTED_SCHEMA_VERSION}, got {state.schema_version}"
                    )
                return StateManager._fresh_state(expected_hash)

            if expected_hash and state.config_hash != expected_hash:
                logger.warning(
                    f"Configuration hash mismatch! State has {state.config_hash}, "
                    f"but current config has {expected_hash}."
                )
            return state
        except StateError:
            raise
        except (ValidationError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Failed to validate state file {path}: {e}")
            # AC8: raise StateError if rename succeeds, return fresh if rename fails
            if StateManager._handle_corrupt_file(path):
                raise StateError(f"State validation failed for {path}") from e
            return StateManager._fresh_state(expected_hash)
        except Exception as e:
            logger.error(f"Unexpected error loading state from {path}: {e}")
            raise StateError(f"Failed to load state from {path}") from e

    @staticmethod
    def save(state: RunState, path: Path) -> None:
        """Saves state atomically using temp file and rename."""
        temp_path: Path | None = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)

            # Create unique temp file in same directory
            temp_path = path.parent / f".{path.name}.{uuid.uuid4()}.tmp"

            with temp_path.open("w", encoding="utf-8") as f:
                f.write(state.model_dump_json(indent=2))

            # Atomic replace
            temp_path.replace(path)
        except Exception as e:
            logger.error(f"Failed to save state to {path}: {e}")
            if temp_path is not None and temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    logger.debug(f"Failed to clean up temp file {temp_path}")
            raise StateError(f"Failed to save state to {path}: {e}") from e

    @staticmethod
    def record_step(state: RunState, cycle_id: str, step_record: StepRecord) -> RunState:
        """Helper to record a step result into the given state instance."""
        new_history: list[CycleRecord] = []
        found_cycle = False
        
        for cycle in state.run_history:
            if cycle.cycle_id == cycle_id:
                # Add step to this cycle
                new_steps = list(cycle.steps) + [step_record]
                new_history.append(cycle.model_copy(update={"steps": new_steps}))
                found_cycle = True
            else:
                new_history.append(cycle)
        
        if not found_cycle:
            raise StateError(f"Cycle {cycle_id} not found in state history.")
            
        return state.model_copy(update={"run_history": new_history})

    @staticmethod
    def start_cycle(state: RunState, cycle_id: str, started_at: datetime | None = None) -> RunState:
        """Creates and appends a new CycleRecord to the run history."""
        started_at = started_at or datetime.now(UTC)
        new_cycle = CycleRecord(cycle_id=cycle_id, started_at=started_at)
        new_history: list[CycleRecord] = [*state.run_history, new_cycle]
        return state.model_copy(update={"run_history": new_history})

    @staticmethod
    def finish_cycle(
        state: RunState,
        cycle_id: str,
        outcome: StepOutcome,
        finished_at: datetime | None = None
    ) -> RunState:
        """Updates an existing CycleRecord with outcome and finish time."""
        finished_at = finished_at or datetime.now(UTC)
        new_history: list[CycleRecord] = []
        found_cycle = False
        
        for cycle in state.run_history:
            if cycle.cycle_id == cycle_id:
                new_history.append(cycle.model_copy(update={
                    "outcome": outcome,
                    "finished_at": finished_at
                }))
                found_cycle = True
            else:
                new_history.append(cycle)
        
        if not found_cycle:
            raise StateError(f"Cycle {cycle_id} not found in state history.")
            
        return state.model_copy(update={"run_history": new_history})

    @staticmethod
    def _handle_corrupt_file(path: Path) -> bool:
        """Renames a corrupt state file with a timestamp suffix.

        Returns True if the rename succeeded (caller should raise StateError),
        False if the rename failed (caller should return fresh state per AC8).
        """
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        corrupt_path = path.with_suffix(f"{path.suffix}.corrupt.{timestamp}")
        try:
            path.replace(corrupt_path)
            logger.info(f"Renamed corrupt state file to {corrupt_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to rename corrupt state file {path}: {e}")
            return False

    @staticmethod
    def _cleanup_stale_temp_files(state_path: Path) -> None:
        """Removes .tmp files older than 24 hours in the state file's directory."""
        directory = state_path.parent
        pattern = f".{state_path.name}.*.tmp"
        now = time.time()
        one_day_seconds = 24 * 3600
        
        for p in directory.glob(pattern):
            try:
                if now - p.stat().st_mtime > one_day_seconds:
                    p.unlink()
                    logger.info(f"Cleaned up stale temp file: {p}")
            except Exception as e:
                logger.warning(f"Failed to cleanup stale temp file {p}: {e}")
