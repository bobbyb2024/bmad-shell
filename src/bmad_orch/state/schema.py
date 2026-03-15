from datetime import datetime
from enum import Enum, StrEnum

from pydantic import BaseModel, ConfigDict, Field

from bmad_orch.types import StepOutcome


class RunStatus(StrEnum):
    """Represents the overall status of an orchestrator run."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    HALTED = "HALTED"


class ErrorRecord(BaseModel):
    """Represents an error that occurred during a step."""
    model_config = ConfigDict(frozen=True)

    message: str
    error_type: str
    traceback: str | None = None


class StepRecord(BaseModel):
    """Represents the execution result of a single step."""
    model_config = ConfigDict(frozen=True)

    step_id: str
    provider_name: str
    outcome: StepOutcome
    timestamp: datetime
    error: ErrorRecord | None = None


class CycleRecord(BaseModel):
    """Represents a collection of steps forming a single execution cycle."""
    model_config = ConfigDict(frozen=True)

    cycle_id: str
    steps: list[StepRecord] = []
    started_at: datetime
    finished_at: datetime | None = None
    outcome: StepOutcome | None = None


class RunState(BaseModel):
    """Represents the complete persistent state of an orchestrator run."""
    model_config = ConfigDict(frozen=False)

    run_id: str
    schema_version: int = 1
    status: RunStatus = RunStatus.PENDING
    run_history: list[CycleRecord] = []
    config_hash: str | None = None
    template_context: dict[str, str] = Field(
        default_factory=lambda: {},
        description="Cumulative context from completed cycles",
    )
    halted_at: datetime | None = None
    failure_point: str | None = None
    failure_reason: str | None = None
    error_type: str | None = None

    def update_status(self, new_status: RunStatus) -> None:
        """Updates the status with transition validation."""
        valid_transitions = {
            RunStatus.PENDING: [RunStatus.RUNNING],
            RunStatus.RUNNING: [RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.HALTED],
            RunStatus.FAILED: [RunStatus.RUNNING],
            RunStatus.HALTED: [RunStatus.RUNNING],
            RunStatus.COMPLETED: [],
        }
        if new_status != self.status and new_status not in valid_transitions.get(self.status, []):
             raise ValueError(f"Invalid status transition: {self.status} -> {new_status}")
        self.status = new_status
