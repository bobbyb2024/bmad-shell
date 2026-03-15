from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from bmad_orch.exceptions import ConfigError, ConfigProviderError
from bmad_orch.types import StepType


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

    enabled: bool = Field(default=False)
    commit_at: Literal["step", "cycle", "never"] = Field(default="cycle")
    push_at: Literal["cycle", "end", "never"] = Field(default="end")
    remote: str = Field(default="origin")
    branch: str | None = Field(default=None)
    commit_message_template: str | None = Field(default=None)

    @model_validator(mode="after")
    def validate_logic(self) -> "GitConfig":
        if self.commit_at == "never" and self.push_at != "never":
            raise ValueError("push_at must be 'never' if commit_at is 'never'")
        return self


class PauseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    between_steps: float = Field(ge=0)
    between_cycles: float = Field(ge=0)
    between_cycle_types: float = Field(default=0.0, ge=0)
    between_workflows: float = Field(ge=0)


class ErrorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    retry_transient: bool = True
    max_retries: int = Field(default=3, ge=1)
    retry_delay: float = Field(default=10.0, ge=0)


class ResourceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    polling_interval: float = Field(default=1.0)
    cpu_threshold: float = Field(default=80.0)
    memory_threshold: float = Field(default=80.0)

    @field_validator("polling_interval")
    @classmethod
    def validate_polling_interval(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("polling_interval must be > 0")
        return v

    @field_validator("memory_threshold")
    @classmethod
    def validate_memory_threshold(cls, v: float) -> float:
        if not (0.0 < v < 100.0):
            raise ValueError("memory_threshold must be between 0.0 and 100.0 (exclusive)")
        return v

    @field_validator("cpu_threshold")
    @classmethod
    def validate_cpu_threshold(cls, v: float) -> float:
        if v <= 0.0:
            raise ValueError("cpu_threshold must be > 0.0")
        return v


class OrchestratorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    providers: dict[int, ProviderConfig]
    cycles: dict[str, CycleConfig]
    git: GitConfig
    pauses: PauseConfig
    error_handling: ErrorConfig
    resources: ResourceConfig = Field(default_factory=ResourceConfig)

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
                    # We raise ValueError here because it's inside a pydantic validator.
                    # validate_config will handle wrapping/re-raising.
                    raise ValueError(f"Cycle '{cycle_id}' step {i} references nonexistent provider ID: {step.provider}")

        return self


def validate_config(data: dict[str, Any]) -> OrchestratorConfig:
    """Validate a raw configuration dictionary and return an OrchestratorConfig object.

    Raises:
        ConfigError: If the configuration is invalid.
        ConfigProviderError: If a step references a nonexistent provider.
    """
    try:
        return OrchestratorConfig(**data)
    except ValidationError as e:
        # Check if any error is a provider reference error
        for error in e.errors():
            if "references nonexistent provider ID" in error["msg"]:
                raise ConfigProviderError(f"✗ Config validation failed — {error['msg']}") from e

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
