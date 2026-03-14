from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from bmad_orch.types import StepOutcome


class ErrorRecord(BaseModel):
    """Represents an error that occurred during a step."""
    model_config = ConfigDict(frozen=True)

    message: str
    error_type: str
    traceback: Optional[str] = None


class StepRecord(BaseModel):
    """Represents the execution result of a single step."""
    model_config = ConfigDict(frozen=True)

    step_id: str
    provider_name: str
    outcome: StepOutcome
    timestamp: datetime
    error: Optional[ErrorRecord] = None


class CycleRecord(BaseModel):
    """Represents a collection of steps forming a single execution cycle."""
    model_config = ConfigDict(frozen=True)

    cycle_id: str
    steps: List[StepRecord] = Field(default_factory=list)
    started_at: datetime
    finished_at: Optional[datetime] = None
    outcome: Optional[StepOutcome] = None


class RunState(BaseModel):
    """Represents the complete persistent state of an orchestrator run."""
    model_config = ConfigDict(frozen=True)

    run_id: str
    schema_version: int = 1
    run_history: List[CycleRecord] = Field(default_factory=list)
    config_hash: Optional[str] = Field(default=None, description="MD5 hash of the normalized config file")
