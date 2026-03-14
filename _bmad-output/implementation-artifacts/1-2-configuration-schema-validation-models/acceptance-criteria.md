# Acceptance Criteria

1. **Given** a valid `bmad-orch.yaml` with providers, cycles, steps, git, pauses, and error_handling sections, **When** the config is loaded into Pydantic models, **Then** `OrchestratorConfig` is created with typed fields for `ProviderConfig`, `CycleConfig`, `StepConfig`, `GitConfig`, `PauseConfig`, and `ErrorConfig`.
2. **Given** a `bmad-orch.yaml` with a missing required field (e.g., no `providers` section), **When** the config is parsed, **Then** a `ConfigError` is raised with a clear message identifying the missing field.
3. **Given** a `bmad-orch.yaml` with an invalid value (e.g., `commit_at: "never"` instead of `step|cycle|end`), **When** the config is parsed, **Then** a `ConfigError` is raised whose message includes the field name, the invalid value, and the list of valid options.
4. **Given** a `StepConfig` entry, **When** it is validated, **Then** it contains `skill` (str), `provider` (int reference), `type` (generative|validation), and `prompt` (str template).
5. **Given** a `CycleConfig` entry, **When** it is validated, **Then** it contains `steps` (ordered list of `StepConfig`, min 1), `repeat` (int >= 1), and optional pause overrides (≥0 when set).
6. **Given** an `OrchestratorConfig`, **When** it is validated, **Then** `providers` has ≥1 entry, `cycles` has ≥1 entry, all string fields are non-empty, all numeric duration/count fields have sane minimums (pauses ≥0, max_retries ≥1, retry_delay ≥0), and `validate_config()` wraps all `ValidationError` in `ConfigError` preserving field name, value, and valid options in the message.
