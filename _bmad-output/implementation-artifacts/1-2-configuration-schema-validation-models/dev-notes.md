# Dev Notes

## Architecture Guardrails

- **Layer:** `config` — can import from `types` and `errors` ONLY. Cannot import from `engine`, `state`, `providers`, or `rendering`. Enforced by `import-linter` in pyproject.toml.
- **File:** Create `src/bmad_orch/config/schema.py` (NOT `models.py` — architecture specifies `schema.py`).
- **Pydantic V2:** Use `pydantic.BaseModel` with `model_config = ConfigDict(extra="forbid")` on every model.
- **Error wrapping:** Provide a `validate_config(data: dict) -> OrchestratorConfig` function in `schema.py` that catches `pydantic.ValidationError` and re-raises as `ConfigError` from `bmad_orch.errors`. This is the single entry point for config validation — consumers call this function, not `OrchestratorConfig(...)` directly. Export it from `config/__init__.py`.

## Existing Code to Reuse — DO NOT RECREATE

- `StepType` enum in `src/bmad_orch/types/__init__.py` — already has `GENERATIVE = "generative"` and `VALIDATION = "validation"`
- `ConfigError` in `src/bmad_orch/errors.py` — already exists with `default_severity = ErrorSeverity.BLOCKING`
- `ErrorSeverity` enum in `src/bmad_orch/errors.py`

## PRD Config Example (canonical field names)

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

## Duration Format (DECIDED)

All pause and delay values are **numeric seconds as `float`** (e.g., `5`, `15.0`, `30`). NOT duration strings like `"5s"`. The YAML example above reflects this decision. Architecture does not mandate format; this is the binding MVP decision.

## Testing Standards

- Framework: pytest 9.x with pytest-cov
- Test location: `tests/test_config/test_schema.py` (create `test_config/` directory with `__init__.py`)
- Naming: `test_<unit>_<behavior>()` — e.g., `test_orchestrator_config_rejects_missing_providers()`
- No `test_should_*` names
- Tests can use `S101` (assert), skip `ANN` and `S603/S607` per Ruff per-file-ignores
- Run: `uv run pytest tests/test_config/`

## Tooling

- Ruff: line-length 120, target py313, rules: E, F, B, I, N, UP, ANN, S, PT, ARG, PTH, TD, FIX
- Pyright: strict mode, src-only
- Pre-commit: ruff check --fix, ruff format, pyright
- Run all checks: `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest`

## Project Structure Notes

- Config module path: `src/bmad_orch/config/schema.py`
- Test path: `tests/test_config/test_schema.py`
- Types live in `src/bmad_orch/types/__init__.py` — add new shared enums here
- Errors live in `src/bmad_orch/errors.py` — `ConfigError` class already exists; validation wrapping logic goes in `schema.py` via `validate_config()`

## Previous Story Intelligence (1.1)

- Code review fixed 5 issues: wrong imports, wrong attribute names, unused imports, unsorted imports, import-linter misconfiguration
- All 37 tests pass, Ruff 0 errors, Pyright 0 errors, Import Linter 0 violations
- `uv run pytest` is the test runner — do not use bare `pytest`
- `--init` callback uses `raise typer.Exit()` pattern for early exit
- Empty `__init__.py` files exist in all layer packages (config, engine, providers, rendering, state)

## References

- [Source: _bmad-output/planning-artifacts/architecture.md — Module Layout, config/schema.py]
- [Source: _bmad-output/planning-artifacts/architecture.md — 5 Immutable Architectural Rules]
- [Source: _bmad-output/planning-artifacts/architecture.md — Exception Hierarchy]
- [Source: _bmad-output/planning-artifacts/prd.md — FR1-FR7 Config Requirements]
- [Source: _bmad-output/planning-artifacts/prd.md — Config Schema Example]
- [Source: _bmad-output/planning-artifacts/architecture.md — Testing Standards]
- [Source: pyproject.toml — import-linter layers contract]
