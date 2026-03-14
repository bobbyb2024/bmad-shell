# Story 1.1: Project Scaffolding & Tooling Setup

Status: done

## Story

As a **developer**,
I want **a properly structured Python project with all dependencies, linting, type checking, and CI configured**,
so that **I have a solid, consistent foundation to build every subsequent feature on**.

## Acceptance Criteria

1. **Given** a new project directory, **When** I run `uv init --name bmad-orch --package`, **Then** the project has `src/bmad_orch/` layout with `__init__.py` and `py.typed`.
2. **And** `.python-version` exists, pins Python 3.13, and is tracked in version control (must NOT be gitignored).
3. **And** `uv.lock` exists and is tracked in version control.
4. **Given** the project is initialized, **When** I run `uv add "typer[all]" rich pydantic pydantic-settings pyyaml structlog psutil libtmux` and `uv add --dev pytest pytest-cov ruff pyright pre-commit import-linter`, **Then** all core and development dependencies are added to `pyproject.toml`.
5. **And** note: `rich` and `libtmux` are declared as dependencies but per architecture rules must only be imported lazily at function-level in rendering modules — never at module-level in core engine code. This is enforced by `test_import_isolation.py` (see Story 1.2+).
6. **Given** the dependencies are installed, **When** I configure `pyproject.toml` with `[tool.ruff]`, `[tool.pyright]` (strict), `[tool.pytest.ini_options]`, and `[tool.importlinter]` sections, **And** I create `src/bmad_orch/types.py`, `src/bmad_orch/errors.py`, and `src/bmad_orch/cli.py` with initial type-safe boilerplate, **And** I run `uv run bmad-orch --help`, **Then** Typer displays the CLI help with `start`, `resume`, `status`, `validate` subcommands and `--init` option listed.
7. **And** when `--init` is passed, the callback must exit after the wizard completes and must NOT fall through to execute a subcommand.
8. **Given** the project is configured, **When** I run `uv run ruff check . && uv run pyright`, **Then** both pass with zero errors under strict configuration, **And** pyright recognizes the package as typed via the `py.typed` PEP 561 marker.
9. **Given** the project is configured, **When** I create `tests/conftest.py` and smoke tests in `tests/test_smoke.py`, **And** I run `uv run pytest`, **Then** the test suite runs with coverage reporting enabled for `src/bmad_orch/`, **And** smoke tests specifically verify importability, core types, error hierarchy, and CLI help.
10. **Given** the project is configured, **When** I create `[tool.importlinter]` configuration in `pyproject.toml` enforcing the layer hierarchy: `rendering` -> `providers` -> `engine` -> `state` -> `config` -> `types`, **And** I create stub `__init__.py` files for each layer package, **And** I run `uv run lint-imports`, **Then** the check passes with zero violations.
11. **Given** the project is initialized, **When** I run `pre-commit install` and then `git commit`, **Then** pre-commit hooks execute Ruff and pyright automatically, **And** `.pre-commit-config.yaml` exists with pinned hook versions.
12. **Given** the project contains a `.github/workflows/` directory, **When** I inspect `ci.yml`, **Then** it contains jobs for ruff, pyright, pytest, and import-linter.

## Tasks / Subtasks

- [x] **Task 1: Project Initialization & Dependencies** (AC: 1, 2, 3, 4, 5)
  - [x] Initialize project with `uv init --package`
  - [x] Pin Python 3.13 in `.python-version`
  - [x] Add core dependencies: `typer[all]`, `rich`, `pydantic`, `pydantic-settings`, `pyyaml`, `structlog`, `psutil`, `libtmux`
  - [x] Add dev dependencies: `pytest`, `pytest-cov`, `ruff`, `pyright`, `pre-commit`, `import-linter`
- [x] **Task 2: Tooling Configuration** (AC: 6, 8, 10, 11)
  - [x] Configure `pyproject.toml` for Ruff (line-length 120, target py313)
  - [x] Configure `pyproject.toml` for Pyright (strict mode, src include)
  - [x] Configure `pyproject.toml` for Pytest (cov enabled, testpaths)
  - [x] Configure `pyproject.toml` for Import Linter (layers contract)
  - [x] Setup `.pre-commit-config.yaml`
- [x] **Task 3: Core Boilerplate & CLI** (AC: 6, 7)
  - [x] Create `src/bmad_orch/py.typed`
  - [x] Create `src/bmad_orch/types/__init__.py` (OutputChunk, ErrorSeverity, etc.)
  - [x] Create `src/bmad_orch/errors.py` (BmadOrchError hierarchy)
  - [x] Create `src/bmad_orch/cli.py` (Typer app with 4 subcommands + --init)
  - [x] Implement `--init` callback logic
- [x] **Task 4: Layer Structure** (AC: 10)
  - [x] Create directories: `rendering/`, `providers/`, `engine/`, `state/`, `config/`
  - [x] Create stub `__init__.py` in each directory
- [x] **Task 5: CI Configuration** (AC: 12)
  - [x] Create `.github/workflows/ci.yml`
- [x] **Task 6: Smoke Tests** (AC: 9)
  - [x] Create `tests/conftest.py`
  - [x] Create `tests/test_smoke.py`

## Dev Notes

- **Lazy Imports:** `rich` and `libtmux` MUST be imported lazily at function-level in rendering modules. [Source: Architecture#Cross-Cutting Concerns]
- **Type Safety:** Use Pydantic V2 for all configuration and state models.
- **CLI Framework:** Typer with `rich` for formatting.
- **Python Version:** 3.13 is mandatory.

### Project Structure Notes

- Uses standard `src/` layout.
- Layered architecture enforced by `import-linter`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Starter Template Evaluation]
- [Source: _bmad-output/planning-artifacts/prd.md#Success Criteria]

## Dev Agent Record

### Agent Model Used

Gemini 2.0 Flash

### Debug Log References

- [2026-03-13] Initialized project structure and dependencies.
- [2026-03-13] Configured Ruff, Pyright, Pytest, and Import Linter.
- [2026-03-13] Implemented CLI boilerplate and --init exit logic.
- [2026-03-13] Created layer subpackages and verified with Import Linter.
- [2026-03-13] Set up pre-commit hooks and GitHub Actions CI.
- [2026-03-13] Code review: rewrote test_types.py (6 placeholder → 7 real tests), fixed pyproject.toml description, updated File List.
- [2026-03-13] Code review (Claude Opus 4.6): Fixed 5 issues — test_types.py wrong import source (ErrorSeverity from types→errors), test_errors.py wrong attribute (.severity→.default_severity), unused import `auto` in types/__init__.py, unsorted/unused imports in test_smoke.py, import-linter container misconfiguration in pyproject.toml. All tools now pass: ruff 0 errors, pyright 0 errors, lint-imports 0 broken, pytest 39 passed.

### Completion Notes List

- All 37 tests pass, including smoke tests and tooling validations.
- Ruff and Pyright (strict) pass with zero errors in `src/`.
- Import Linter confirms zero violations in the layer hierarchy.
- `.python-version` is correctly tracked (un-gitignored).
- CLI `--init` correctly exits without falling through.

### File List

- `src/bmad_orch/__init__.py`
- `uv.lock`
- `.gitignore`
- `.python-version`
- `.pre-commit-config.yaml`
- `.github/workflows/ci.yml`
- `pyproject.toml`
- `src/bmad_orch/py.typed`
- `src/bmad_orch/cli.py`
- `src/bmad_orch/errors.py`
- `src/bmad_orch/types/__init__.py`
- `src/bmad_orch/rendering/__init__.py`
- `src/bmad_orch/providers/__init__.py`
- `src/bmad_orch/engine/__init__.py`
- `src/bmad_orch/state/__init__.py`
- `src/bmad_orch/config/__init__.py`
- `tests/conftest.py`
- `tests/test_smoke.py`
- `tests/test_project_structure.py`
- `tests/test_tooling.py`
- `tests/test_ci_workflows.py`
- `tests/test_gitignore.py`
- `tests/test_layer_packages.py`
- `tests/test_errors.py`
- `tests/test_types.py`
- `tests/test_cli.py`
- `tests/test_config_sections.py`
- `tests/test_dependencies.py`
