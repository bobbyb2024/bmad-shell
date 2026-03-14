# Story 1.3: Config File Loading & Discovery

Status: done

## Story

As a **user**,
I want to load my config from a file using either a flag or convention,
So that I can validate my setup before running cycles.

## Acceptance Criteria

1. **Given** a `bmad-orch.yaml` exists in the current working directory, **When** I run `bmad-orch validate` with no flags, **Then** the system discovers and loads `bmad-orch.yaml` from the cwd.
2. **Given** a config file exists at `/path/to/my-config.yaml`, **When** I run `bmad-orch validate --config /path/to/my-config.yaml`, **Then** the system loads the config from the explicit path (overriding cwd discovery).
3. **Given** no `bmad-orch.yaml` exists in cwd and no `--config` flag is provided, **When** I run `bmad-orch validate`, **Then** the system exits with code 2 and a clear error: `✗ No config found — create bmad-orch.yaml or use --config <path>`.
4. **Given** a valid config file, **When** I run `bmad-orch validate`, **Then** the system reports schema correctness and exits with code 0, and the output confirms provider names and model names from the config.
5. **Given** a config file with a YAML syntax error, **When** I run `bmad-orch validate`, **Then** the system exits with code 2 and a clear error identifying the line and nature of the YAML parse failure.

## Tasks / Subtasks

- [x] Task 1: Create configuration discovery and loading logic in `src/bmad_orch/config/discovery.py`
  - [x] Implement `discover_config_path(explicit_path)`
  - [x] Implement `load_config_file(path)`
  - [x] Implement `get_config(explicit_path)` as a high-level entry point
- [x] Task 2: Update `src/bmad_orch/config/__init__.py` to export discovery functions
- [x] Task 3: Implement `validate` command in `src/bmad_orch/cli.py`
  - [x] Support `--config` / `-c` flag
  - [x] Call `get_config()` and handle `BmadOrchError`
  - [x] Use `Rich` to display validation success and configuration summary
  - [x] Enforce exit codes 0 and 2
- [x] Task 4: Write comprehensive tests
  - [x] `tests/test_config/test_discovery.py` for unit tests of the discovery logic
  - [x] `tests/test_cli_discovery.py` for integration tests of the CLI `validate` command

## Dev Notes

### Architecture Guardrails

- **Layer:** `config` — only imports from `types` and `errors`.
- **Error Format:** Must follow `✗ [What happened] — [What to do next]`.
- **Exit Codes:** 0 (success), 1 (general error), 2 (config error).

### Configuration Discovery Order

1. Explicit `--config` (or `-c`) path.
2. `bmad-orch.yaml` in the current working directory.
