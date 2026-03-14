# Story 1.2: Configuration Schema & Validation Models

Status: done

## Story

As a **user**,
I want **a well-defined configuration schema that validates my `bmad-orch.yaml` file**,
so that **I know my config is correct before I run any cycles**.

## Acceptance Criteria

1. **Given** a valid `bmad-orch.yaml` with providers, cycles, steps, git, pauses, and error_handling sections, **When** the config is loaded into Pydantic models, **Then** `OrchestratorConfig` is created with typed fields for `ProviderConfig`, `CycleConfig`, `StepConfig`, `GitConfig`, `PauseConfig`, and `ErrorConfig`.
2. **Given** a `bmad-orch.yaml` with a missing required field (e.g., no `providers` section), **When** the config is parsed, **Then** a `ConfigError` is raised with a clear message identifying the missing field.
3. **Given** a `bmad-orch.yaml` with an invalid value (e.g., `commit_at: "never"` instead of `step|cycle|end`), **When** the config is parsed, **Then** a `ConfigError` is raised whose message includes the field name, the invalid value, and the list of valid options.
4. **Given** a `StepConfig` entry, **When** it is validated, **Then** it contains `skill` (str), `provider` (int reference), `type` (generative|validation), and `prompt` (str template).
5. **Given** a `CycleConfig` entry, **When** it is validated, **Then** it contains `steps` (ordered list of `StepConfig`, min 1), `repeat` (int >= 1), and optional pause overrides (≥0 when set).
6. **Given** an `OrchestratorConfig`, **When** it is validated, **Then** `providers` has ≥1 entry, `cycles` has ≥1 entry, all string fields are non-empty, all numeric duration/count fields have sane minimums (pauses ≥0, max_retries ≥1, retry_delay ≥0), and `validate_config()` wraps all `ValidationError` in `ConfigError` preserving field name, value, and valid options in the message.

## Tasks / Subtasks

- [x] Task 1: Define new enum types (AC: 1, 3)
  - [x] Add `Timing` enum (`step`, `cycle`, `end`) to `src/bmad_orch/types/__init__.py` — single enum for both commit and push timing (identical values, no justification for separate types)
  - [x] `StepType` already exists — DO NOT recreate
- [x] Task 2: Create Pydantic models in `src/bmad_orch/config/schema.py` (AC: 1, 4, 5)
  - [x] `ProviderConfig(BaseModel)`: `name: str` (min_length=1), `cli: str` (min_length=1), `model: str` (min_length=1)
  - [x] `StepConfig(BaseModel)`: `skill: str` (min_length=1), `provider: int`, `type: StepType`, `prompt: str` (min_length=1)
  - [x] `CycleConfig(BaseModel)`: `steps: list[StepConfig]` (min_length=1), `repeat: int = 1` (≥1), `pause_between_steps: float | None = None` (≥0 if set), `pause_between_cycles: float | None = None` (≥0 if set)
  - [x] `GitConfig(BaseModel)`: `commit_at: Timing`, `push_at: Timing`
  - [x] `PauseConfig(BaseModel)`: `between_steps: float` (≥0), `between_cycles: float` (≥0), `between_workflows: float` (≥0)
  - [x] `ErrorConfig(BaseModel)`: `retry_transient: bool = True`, `max_retries: int = 3` (≥1), `retry_delay: float = 10.0` (≥0)
  - [x] `OrchestratorConfig(BaseModel)`: `providers: dict[int, ProviderConfig]` (min 1 entry), `cycles: dict[str, CycleConfig]` (min 1 entry), `git: GitConfig`, `pauses: PauseConfig`, `error_handling: ErrorConfig`
  - [x] `validate_config(data: dict) -> OrchestratorConfig`: entry-point function that wraps `ValidationError` in `ConfigError`
- [x] Task 3: Add cross-field validation (AC: 1, 2, 3, 6)
  - [x] `@model_validator` on `OrchestratorConfig`: validate all `StepConfig.provider` references exist in `providers` dict
  - [x] `@field_validator` on `CycleConfig.repeat`: enforce `>= 1`
  - [x] `@model_validator` on `OrchestratorConfig`: enforce `providers` has ≥1 entry and `cycles` has ≥1 entry
  - [x] `@field_validator` on `ErrorConfig.max_retries`: enforce `>= 1`
  - [x] `@field_validator` on `PauseConfig` float fields: enforce `>= 0`
  - [x] `@field_validator` on `CycleConfig` optional pause fields: enforce `>= 0` when set
  - [x] `@field_validator` on `ErrorConfig.retry_delay`: enforce `>= 0`
  - [x] Wrap Pydantic `ValidationError` in `ConfigError` with clear, actionable messages — must preserve field name, invalid value, and valid options (for enums) in the wrapped message
  - [x] Set `model_config = ConfigDict(extra="forbid")` on all models to catch YAML typos
- [x] Task 4: Update `config/__init__.py` exports (AC: 1)
  - [x] Export all models and `validate_config` from `config/__init__.py` with explicit `__all__` list
- [x] Task 5: Write tests in `tests/test_config/test_schema.py` (AC: 1-5)
  - [x] Test valid complete config creates `OrchestratorConfig` with all typed fields
  - [x] Test missing required section raises `ConfigError` with field name in message
  - [x] Test invalid enum value raises `ConfigError` listing valid options
  - [x] Test `StepConfig` field types enforced
  - [x] Test `CycleConfig` with `repeat < 1` raises error
  - [x] Test `CycleConfig` with default `repeat=1` works
  - [x] Test extra/unknown YAML keys raise validation error
  - [x] Test provider reference in step pointing to nonexistent provider raises `ConfigError`
  - [x] Test valid config with optional pause overrides in cycle
  - [x] Test wrong-type value in nested model (e.g., `provider: "one"` instead of int in `StepConfig`) raises `ConfigError`
  - [x] Test empty `providers` dict raises `ConfigError`
  - [x] Test empty `steps` list in `CycleConfig` raises `ConfigError`
  - [x] Test `max_retries: 0` and `max_retries: -1` raise `ConfigError`
  - [x] Test negative pause values raise `ConfigError`
  - [x] Test `ConfigError` message for invalid enum contains field name, bad value, and valid options
  - [x] Test `validate_config()` wrapper function returns `OrchestratorConfig` on valid input
  - [x] Test `validate_config()` wrapper raises `ConfigError` (not raw `ValidationError`) on invalid input

## Dev Notes

### Architecture Guardrails

- **Layer:** `config` — can import from `types` and `errors` ONLY. Cannot import from `engine`, `state`, `providers`, or `rendering`. Enforced by `import-linter` in pyproject.toml.
- **File:** Create `src/bmad_orch/config/schema.py` (NOT `models.py` — architecture specifies `schema.py`).
- **Pydantic V2:** Use `pydantic.BaseModel` with `model_config = ConfigDict(extra="forbid")` on every model.
- **Error wrapping:** Provide a `validate_config(data: dict) -> OrchestratorConfig` function in `schema.py` that catches `pydantic.ValidationError` and re-raises as `ConfigError` from `bmad_orch.errors`. This is the single entry point for config validation — consumers call this function, not `OrchestratorConfig(...)` directly. Export it from `config/__init__.py`.

### Existing Code to Reuse — DO NOT RECREATE

- `StepType` enum in `src/bmad_orch/types/__init__.py` — already has `GENERATIVE = "generative"` and `VALIDATION = "validation"`
- `ConfigError` in `src/bmad_orch/errors.py` — already exists with `default_severity = ErrorSeverity.BLOCKING`
- `ErrorSeverity` enum in `src/bmad_orch/errors.py`

### PRD Config Example (canonical field names)

```yaml
providers:
  1:
    name: claude
    cli: claude
    model: opus-4
  2:
    name: gemini
    cli: gemini
    model: gemini-2.5-pro

cycles:
  story:
    steps:
      - skill: create-story
        provider: 1
        type: generative
        prompt: "/bmad-create-story for story {next_story_id}"
      - skill: adversarial-story-review
        provider: 1
        type: validation
        prompt: "/bmad-review-adversarial-general review story {current_story_file}"
    repeat: 2
    pause_between_steps: 5
    pause_between_cycles: 15

git:
  commit_at: cycle
  push_at: end

pauses:
  between_steps: 5
  between_cycles: 15
  between_workflows: 30

error_handling:
  retry_transient: true
  max_retries: 3
  retry_delay: 10
```

### Duration Format (DECIDED)

All pause and delay values are **numeric seconds as `float`** (e.g., `5`, `15.0`, `30`). NOT duration strings like `"5s"`. The YAML example above reflects this decision. Architecture does not mandate format; this is the binding MVP decision.

### Testing Standards

- Framework: pytest 9.x with pytest-cov
- Test location: `tests/test_config/test_schema.py` (create `test_config/` directory with `__init__.py`)
- Naming: `test_<unit>_<behavior>()` — e.g., `test_orchestrator_config_rejects_missing_providers()`
- No `test_should_*` names
- Tests can use `S101` (assert), skip `ANN` and `S603/S607` per Ruff per-file-ignores
- Run: `uv run pytest tests/test_config/`

### Tooling

- Ruff: line-length 120, target py313, rules: E, F, B, I, N, UP, ANN, S, PT, ARG, PTH, TD, FIX
- Pyright: strict mode, src-only
- Pre-commit: ruff check --fix, ruff format, pyright
- Run all checks: `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest`

### Project Structure Notes

- Config module path: `src/bmad_orch/config/schema.py`
- Test path: `tests/test_config/test_schema.py`
- Types live in `src/bmad_orch/types/__init__.py` — add new shared enums here
- Errors live in `src/bmad_orch/errors.py` — `ConfigError` class already exists; validation wrapping logic goes in `schema.py` via `validate_config()`

### Previous Story Intelligence (1.1)

- Code review fixed 5 issues: wrong imports, wrong attribute names, unused imports, unsorted imports, import-linter misconfiguration
- All 37 tests pass, Ruff 0 errors, Pyright 0 errors, Import Linter 0 violations
- `uv run pytest` is the test runner — do not use bare `pytest`
- `--init` callback uses `raise typer.Exit()` pattern for early exit
- Empty `__init__.py` files exist in all layer packages (config, engine, providers, rendering, state)

### References

- [Source: _bmad-output/planning-artifacts/architecture.md — Module Layout, config/schema.py]
- [Source: _bmad-output/planning-artifacts/architecture.md — 5 Immutable Architectural Rules]
- [Source: _bmad-output/planning-artifacts/architecture.md — Exception Hierarchy]
- [Source: _bmad-output/planning-artifacts/prd.md — FR1-FR7 Config Requirements]
- [Source: _bmad-output/planning-artifacts/prd.md — Config Schema Example]
- [Source: _bmad-output/planning-artifacts/architecture.md — Testing Standards]
- [Source: pyproject.toml — import-linter layers contract]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

N/A

### Completion Notes List

- All 5 tasks implemented and verified
- 23 tests passing, 100% coverage on schema.py
- Ruff 0 errors, Pyright 0 errors
- Code review found 2 issues: missing test scenarios and unchecked tasks — both fixed

### File List

- `src/bmad_orch/types/__init__.py` — Added `Timing` enum
- `src/bmad_orch/config/schema.py` — Created: all Pydantic models + `validate_config()`
- `src/bmad_orch/config/__init__.py` — Updated: exports all models with `__all__`
- `tests/test_config/__init__.py` — Created: package marker
- `tests/test_config/test_schema.py` — Created: 23 tests covering all 6 ACs
