from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from bmad_orch.types import StepOutcome


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
    model_config = ConfigDict(frozen=True)

    run_id: str
    schema_version: int = 1
    run_history: list[CycleRecord] = []
    config_hash: str | None = None
    template_context: dict[str, str] = Field(
        default_factory=lambda: {},
        description="Cumulative context from completed cycles",
    )
