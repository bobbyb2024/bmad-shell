# Acceptance Criteria

1. **Given** a `bmad-orch.yaml` exists in the current working directory, **When** I run `bmad-orch validate` with no flags, **Then** the system discovers and loads `bmad-orch.yaml` from the cwd.
2. **Given** a config file exists at `/path/to/my-config.yaml`, **When** I run `bmad-orch validate --config /path/to/my-config.yaml`, **Then** the system loads the config from the explicit path (overriding cwd discovery).
3. **Given** no `bmad-orch.yaml` exists in cwd and no `--config` flag is provided, **When** I run `bmad-orch validate`, **Then** the system exits with code 2 and a clear error: `✗ No config found — create bmad-orch.yaml or use --config <path>`.
4. **Given** a valid config file, **When** I run `bmad-orch validate`, **Then** the system reports schema correctness and exits with code 0, and the output confirms provider names and model names from the config.
5. **Given** a config file with a YAML syntax error, **When** I run `bmad-orch validate`, **Then** the system exits with code 2 and a clear error identifying the line and nature of the YAML parse failure.
