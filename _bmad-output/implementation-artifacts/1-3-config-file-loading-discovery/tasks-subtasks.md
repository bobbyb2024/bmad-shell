# Tasks / Subtasks

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
