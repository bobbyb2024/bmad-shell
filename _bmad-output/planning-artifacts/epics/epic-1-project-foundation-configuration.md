# Epic 1: Project Foundation & Configuration

User can install the tool and define, validate, and preview orchestrator configurations — seeing exactly what will execute before spending API credits.

## Story 1.1: Project Scaffolding & Tooling Setup

As a **developer**,
I want a properly structured Python project with all dependencies, linting, type checking, and CI configured,
So that I have a solid, consistent foundation to build every subsequent feature on.

**Acceptance Criteria:**

**Given** a new project directory
**When** I run `uv init --name bmad-orch --package`
**Then** the project has `src/bmad_orch/` layout with `__init__.py` and `py.typed`
**And** `.python-version` exists, pins Python 3.13, and is tracked in version control (must NOT be gitignored)
**And** `uv.lock` exists and is tracked in version control

**Given** the project is initialized
**When** I run `uv add "typer[all]" rich pydantic pydantic-settings pyyaml structlog psutil libtmux` and `uv add --dev pytest pytest-cov ruff pyright pre-commit import-linter`
**Then** all core and development dependencies are added to `pyproject.toml`
**And** note: `rich` and `libtmux` are declared as dependencies but per architecture rules must only be imported lazily at function-level in rendering modules — never at module-level in core engine code. This is enforced by `test_import_isolation.py` (see Story 1.2+).

**Given** the dependencies are installed
**When** I configure `pyproject.toml` with `[tool.ruff]`, `[tool.pyright]` (strict), `[tool.pytest.ini_options]`, and `[tool.importlinter]` sections
**And** I create `src/bmad_orch/types.py`, `src/bmad_orch/errors.py`, and `src/bmad_orch/cli.py` with initial type-safe boilerplate
**And** I run `uv run bmad-orch --help`
**Then** Typer displays the CLI help with `start`, `resume`, `status`, `validate` subcommands and `--init` option listed
**And** when `--init` is passed, the callback must exit after the wizard completes and must NOT fall through to execute a subcommand

**Given** the project is configured
**When** I run `uv run ruff check . && uv run pyright`
**Then** both pass with zero errors under strict configuration
**And** pyright recognizes the package as typed via the `py.typed` PEP 561 marker

**Given** the project is configured
**When** I create `tests/conftest.py` and smoke tests in `tests/test_smoke.py`
**And** I run `uv run pytest`
**Then** the test suite runs with coverage reporting enabled for `src/bmad_orch/`
**And** smoke tests specifically verify:
    - `bmad_orch` is importable
    - `OutputChunk`, `ErrorSeverity`, and `StepType` can be instantiated from `types.py`
    - `BmadOrchError` and its subclasses can be instantiated with appropriate `severity` from `errors.py`
    - `bmad-orch --help` exits with status 0 and lists all 4 subcommands (`start`, `resume`, `status`, `validate`)

**Given** the project is configured
**When** I create `[tool.importlinter]` configuration in `pyproject.toml` enforcing the layer hierarchy: `rendering` -> `providers` -> `engine` -> `state` -> `config` -> `types`
**And** I create stub `__init__.py` files for each layer package (`rendering/`, `providers/`, `engine/`, `state/`, `config/`) so import-linter can resolve them
**And** I run `uv run lint-imports`
**Then** the check passes with zero violations against real (non-vacuous) module resolution

**Given** the project is initialized
**When** I run `pre-commit install` and then `git commit`
**Then** pre-commit hooks execute Ruff and pyright automatically
**And** `.pre-commit-config.yaml` exists with pinned hook versions

**Given** the project contains a `.github/workflows/` directory
**When** I inspect `ci.yml`
**Then** it contains jobs for `ruff`, `pyright`, `pytest`, and `import-linter` triggered on PRs to `main`
**And** `release.yml` contains a job to publish to PyPI using `pypa/gh-action-pypi-publish` on tagged releases

**Given** the project is initialized
**When** I create a `.gitignore`
**Then** it excludes `__pycache__/`, `.venv/`, `.ruff_cache/`, `dist/`, `*.egg-info/`, `.pyright_cache/`, `bmad-orch-state.json`, `bmad-orch-state.tmp`, and `coverage.xml`
**And** it does NOT exclude `.python-version` (which must be tracked in version control)

**Given** the project contains `src/bmad_orch/__init__.py`
**When** I inspect its contents
**Then** it exports a `__version__` string and defines `__all__`

**Given** the project contains `types.py` and `errors.py`
**When** I inspect their contents
**Then** `types.py` defines `OutputChunk` (frozen dataclass), `EscalationState` (enum: ok/attention/action/complete/idle), `ProviderName` (NewType over str), `StepOutcome` (enum: `PASSED`, `FAILED`, `SKIPPED`, `ERROR`), `ErrorSeverity` (enum: `BLOCKING`, `RECOVERABLE`, `IMPACTFUL`), and `StepType` (enum: generative/validation) with zero internal dependencies
**And** `errors.py` defines the `BmadOrchError` hierarchy with `ConfigError` (BLOCKING), `ProviderError` with subclasses `ProviderNotFoundError` (BLOCKING) / `ProviderTimeoutError` (RECOVERABLE) / `ProviderCrashError` (IMPACTFUL), `StateError` (IMPACTFUL), `GitError` (IMPACTFUL), `ResourceError` (IMPACTFUL), `WizardError` (BLOCKING) — each carrying its assigned `ErrorSeverity`
**And** `severity` must be an instance attribute set in `__init__`, not a mutable class variable — subclasses override via `__init__` default, not class-level assignment
**And** every exception class references `ErrorSeverity` from `types.py` through a clean, non-circular import

## Story 1.2: Configuration Schema & Validation Models

As a **user**,
I want a well-defined configuration schema that validates my `bmad-orch.yaml` file,
So that I know my config is correct before I run any cycles.

**Acceptance Criteria:**

**Given** a valid `bmad-orch.yaml` with providers, cycles, steps, git, pauses, and error_handling sections
**When** the config is loaded into Pydantic models
**Then** `OrchestratorConfig` is created with typed fields for `ProviderConfig`, `CycleConfig`, `StepConfig`, `GitConfig`, `PauseConfig`, and `ErrorConfig`

**Given** a `bmad-orch.yaml` with a missing required field (e.g., no `providers` section)
**When** the config is parsed
**Then** a `ConfigError` is raised with a clear message identifying the missing field

**Given** a `bmad-orch.yaml` with an invalid value (e.g., `commit_at: "never"` instead of `step|cycle|end`)
**When** the config is parsed
**Then** a `ConfigError` is raised identifying the invalid value and listing valid options

**Given** a `StepConfig` entry
**When** it is validated
**Then** it contains `skill` (str), `provider` (int reference), `type` (generative|validation), and `prompt` (str template)

**Given** a `CycleConfig` entry
**When** it is validated
**Then** it contains `steps` (ordered list of `StepConfig`), `repeat` (int >= 1), and optional pause overrides

## Story 1.3: Config File Loading & Discovery

As a **user**,
I want to load my config from a file using either a flag or convention,
So that I can validate my setup before running cycles.

**Acceptance Criteria:**

**Given** a `bmad-orch.yaml` exists in the current working directory
**When** I run `bmad-orch validate` with no flags
**Then** the system discovers and loads `bmad-orch.yaml` from the cwd

**Given** a config file exists at `/path/to/my-config.yaml`
**When** I run `bmad-orch validate --config /path/to/my-config.yaml`
**Then** the system loads the config from the explicit path (overriding cwd discovery)

**Given** no `bmad-orch.yaml` exists in cwd and no `--config` flag is provided
**When** I run `bmad-orch validate`
**Then** the system exits with code 2 and a clear error: `✗ No config found — create bmad-orch.yaml or use --config <path>`

**Given** a valid config file
**When** I run `bmad-orch validate`
**Then** the system reports schema correctness and exits with code 0
**And** the output confirms provider names and model names from the config

**Given** a config file with a YAML syntax error
**When** I run `bmad-orch validate`
**Then** the system exits with code 2 and a clear error identifying the line and nature of the YAML parse failure

## Story 1.4: Prompt Template Variable Registry

As a **user**,
I want prompt templates in my config to support dynamic variables,
So that each step receives context-aware prompts with the correct story IDs, file paths, and other run-time values.

**Acceptance Criteria:**

**Given** a step prompt containing `{next_story_id}`
**When** the template variable registry resolves it
**Then** the variable is replaced with the correct story identifier from orchestrator state

**Given** a step prompt containing `{current_story_file}`
**When** the template variable registry resolves it
**Then** the variable is replaced with the file path of the current story artifact

**Given** a step prompt containing an unknown variable `{nonexistent_var}`
**When** the template variable registry attempts resolution
**Then** the step halts with a `ConfigError` identifying the unresolvable variable: `✗ Unresolvable template variable '{nonexistent_var}' in step 'create-story' — check prompt template in config`

**Given** a step prompt containing multiple variables `{next_story_id}` and `{current_story_file}`
**When** the template variable registry resolves them
**Then** all variables are replaced in a single pass with no partial resolution

**Given** a step prompt with no template variables (plain text)
**When** the template variable registry processes it
**Then** the prompt is passed through unchanged

## Story 1.5: Playbook Summary & Dry Run

As a **user**,
I want to preview exactly what the orchestrator will execute before it starts,
So that I can catch config mistakes before spending API credits.

**Acceptance Criteria:**

**Given** a valid config file
**When** I run `bmad-orch start --dry-run`
**Then** the system displays the complete execution plan showing all cycles, their steps, assigned providers/models, step types (generative/validation), repeat counts, and prompt templates
**And** no providers are invoked
**And** the system exits with code 0

**Given** a valid config and first run with this config
**When** I run `bmad-orch start`
**Then** a pre-flight summary table is displayed showing providers, cycles, steps, and prompts
**And** the system waits for user confirmation (Enter to proceed) before execution begins

**Given** a valid config and a previous successful run exists with this config
**When** I run `bmad-orch start`
**Then** the pre-flight summary displays briefly (auto-dismiss after 3 seconds) or is skippable

**Given** the pre-flight summary is displayed on first run
**When** the user chooses to modify
**Then** the system opens the config file in `$EDITOR`, and re-validates on save before re-displaying the summary

**Given** a config file with an invalid provider reference
**When** I run `bmad-orch start --dry-run`
**Then** the system reports the config error with exit code 2 and does not display the execution plan
