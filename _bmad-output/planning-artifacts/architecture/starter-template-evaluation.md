# Starter Template Evaluation

## Primary Technology Domain

Python CLI Tool / Subprocess Orchestrator — based on PRD classification and project requirements analysis.

## Starter Options Considered

**Third-party starter templates evaluated and rejected:**
- `copier` Python templates — add unnecessary scaffolding opinions and template maintenance dependency
- Community `uv-example-project` templates — useful for reference but add non-standard structure choices

**Selected approach: `uv init --package`** — Python's standard packaging toolchain with zero third-party template dependencies. For a CLI tool distributed via PyPI, the native `src/` layout with `[project.scripts]` entry points is the cleanest foundation.

## Selected Starter: uv init --package

**Rationale for Selection:**
Standard Python packaging with no template bloat. `uv init --package` creates the exact structure a PyPI-distributed CLI tool needs: `src/` layout, `pyproject.toml` with build system, and entry point configuration. All additional tooling is added as explicit dependencies with clear rationale.

**Initialization Command:**

```bash
uv init --package bmad-orch
cd bmad-orch
uv add typer rich pydantic pydantic-settings pyyaml
uv add --dev pytest pytest-cov pytest-asyncio pytest-timeout ruff pyright pre-commit
```

**Project Structure:**

```
bmad-orch/
├── src/
│   └── bmad_orch/
│       └── __init__.py
├── pyproject.toml
├── .python-version         # Pins Python 3.13
├── README.md
└── uv.lock
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:**
- Python 3.13 (latest stable) with `requires-python = ">=3.13"` floor
- `src/` layout for clean import separation and standard Python packaging

**CLI Framework:**
- Typer (latest, supports Python 3.10-3.13) — most popular modern CLI framework, type-hint driven, built on Click, native Rich integration for `--help` rendering, auto-completion for bash/zsh/fish

**Terminal Formatting:**
- Rich (latest) — formatting layer only (no TUI framework), as specified in UX design

**Configuration & Validation:**
- Pydantic v2 (2.12.x stable) — config schema validation, typed Python objects from YAML
- pydantic-settings — environment variable overrides for headless/CI mode
- PyYAML — YAML parsing into Pydantic models

**Build Tooling:**
- uv — package management, virtual environment, lockfile, dependency resolution
- hatchling — build backend (uv default), modern and fast
- All configuration in `pyproject.toml` — no scattered config files

**Testing Framework:**
- pytest 9.x — standard Python testing
- pytest-cov — coverage measurement (required by reliability NFRs)
- pytest-asyncio — async subprocess management testing
- pytest-timeout — prevents subprocess test hangs in CI
- Consider pytest-subprocess for subprocess invocation mocking

**Linting, Formatting & Type Checking:**
- Ruff 0.15.x (Astral, same team as uv) — replaces Black + isort + flake8, 2026 style guide, configured strict from day one
- pyright (latest) — 3-5x faster than mypy, implements newest typing features first, strict mode from day one
- pre-commit — runs Ruff + pyright on every commit

**Code Organization:**
- `pyproject.toml` as single configuration source for all tools (Ruff, pytest, pyright)
- `[project.scripts]` defines `bmad-orch` CLI entry point → Typer app
- `uv.lock` checked into version control for reproducible installs

**Note:** Project initialization using this command should be the first implementation story.
