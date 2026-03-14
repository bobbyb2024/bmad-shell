from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from bmad_orch.errors import ConfigError
from bmad_orch.types import StepType, Timing


class ProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    cli: str = Field(min_length=1)
    model: str = Field(min_length=1)


class StepConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill: str = Field(min_length=1)
    provider: int
    type: StepType
    prompt: str = Field(min_length=1)


class CycleConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    steps: list[StepConfig] = Field(min_length=1)
    repeat: int = Field(default=1)
    pause_between_steps: float | None = Field(default=None)
    pause_between_cycles: float | None = Field(default=None)

    @field_validator("repeat")
    @classmethod
    def validate_repeat(cls, v: int) -> int:
        if v < 1:
            raise ValueError("repeat must be >= 1")
        return v

    @field_validator("pause_between_steps", "pause_between_cycles")
    @classmethod
    def validate_pauses(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError("pause values must be >= 0")
        return v


class GitConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    commit_at: Timing
    push_at: Timing


class PauseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    between_steps: float = Field(ge=0)
    between_cycles: float = Field(ge=0)
    between_workflows: float = Field(ge=0)


class ErrorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    retry_transient: bool = True
    max_retries: int = Field(default=3, ge=1)
    retry_delay: float = Field(default=10.0, ge=0)


class OrchestratorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    providers: dict[int, ProviderConfig]
    cycles: dict[str, CycleConfig]
    git: GitConfig
    pauses: PauseConfig
    error_handling: ErrorConfig

    @model_validator(mode="after")
    def validate_structure(self) -> "OrchestratorConfig":
        if not self.providers:
            raise ValueError("providers dict must have at least one entry")
        if not self.cycles:
            raise ValueError("cycles dict must have at least one entry")

        # Validate step.provider references exist in providers
        provider_ids = set(self.providers.keys())
        for cycle_id, cycle in self.cycles.items():
            for i, step in enumerate(cycle.steps):
                if step.provider not in provider_ids:
                    raise ValueError(f"Cycle '{cycle_id}' step {i} references nonexistent provider ID: {step.provider}")

        return self


def validate_config(data: dict[str, Any]) -> OrchestratorConfig:
    """Validate a raw configuration dictionary and return an OrchestratorConfig object.

    Raises:
        ConfigError: If the configuration is invalid, wrapping the Pydantic ValidationError.
    """
    try:
        return OrchestratorConfig(**data)
    except ValidationError as e:
        # Pydantic v2 ValidationError messages can be quite detailed.
        # We need to wrap them in ConfigError as per requirements.
        # The requirement asks to preserve field name, invalid value, and valid options (for enums).
        # Pydantic's default __str__ often contains these.

        # Let's format a slightly nicer message for ConfigError
        errors = e.errors()
        msg_parts: list[str] = []
        for err in errors:
            loc = " -> ".join(str(x) for x in err["loc"])
            msg = err["msg"]
            input_val = err.get("input")
            part = f"{loc}: {msg}"
            if input_val is not None:
                part += f" (input: {input_val})"
            msg_parts.append(part)

        full_msg = "✗ Config validation failed — fix the following:\n" + "\n".join(msg_parts)
        raise ConfigError(full_msg) from e
