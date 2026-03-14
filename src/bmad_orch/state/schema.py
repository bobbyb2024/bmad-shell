from pydantic import BaseModel, Field

class OrchestratorState(BaseModel):
    """Represents the persistent state of an orchestrator run."""
    config_hash: str = Field(description="MD5 hash of the normalized config file")
    # Additional fields for tracking progress will be added in later stories (e.g., Story 3.2)
