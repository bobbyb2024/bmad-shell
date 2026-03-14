# Acceptance Criteria Coverage

| AC | Scenario | Test File | Status |
|----|----------|-----------|--------|
| AC1 | Project structure (`src/bmad_orch/`, etc.) | `tests/test_project_structure.py` | 🔴 RED (skipped) |
| AC2 | `.python-version` pins 3.13 | `tests/test_project_structure.py` | 🔴 RED (skipped) |
| AC3 | `uv.lock` exists | `tests/test_project_structure.py` | 🔴 RED (skipped) |
| AC4 | Dependencies in `pyproject.toml` | `tests/test_dependencies.py` | 🔴 RED (skipped) |
| AC5 | Dev dependencies in `pyproject.toml` | `tests/test_dependencies.py` | 🔴 RED (skipped) |
| AC6 | Core types instantiation | `tests/test_types.py` | 🔴 RED (skipped) |
| AC7 | Error hierarchy instantiation | `tests/test_errors.py` | 🔴 RED (skipped) |
| AC8 | CLI help and subcommands | `tests/test_cli.py`, `tests/test_smoke.py` | 🔴 RED (skipped) |
| AC9 | `--init` callback behavior | `tests/test_cli.py` | 🔴 RED (skipped) |
| AC10 | Linters and Pyright configuration | `tests/test_tooling.py`, `tests/test_config_sections.py` | 🔴 RED (skipped) |
| AC11 | Layer packages and stubs | `tests/test_layer_packages.py` | 🔴 RED (skipped) |
| AC12 | Import Linter enforcement | `tests/test_tooling.py`, `tests/test_config_sections.py` | 🔴 RED (skipped) |
| AC13 | Pre-commit configuration | `tests/test_ci_workflows.py` | 🔴 RED (skipped) |
| AC14 | CI workflow definitions | `tests/test_ci_workflows.py` | 🔴 RED (skipped) |
| AC15 | Lazy imports for rich/libtmux | `tests/test_smoke.py`, `tests/test_tooling.py` | 🔴 RED (skipped) |
