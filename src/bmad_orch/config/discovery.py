import pathlib
import sys
from typing import Any

import yaml

from bmad_orch.config.schema import OrchestratorConfig, validate_config
from bmad_orch.exceptions import ConfigError
from bmad_orch.providers import get_adapter, _registry

_MAX_CONFIG_SIZE = 1_048_576  # 1 MB


def validate_provider_availability(config: OrchestratorConfig) -> None:
    """Validate that all providers referenced in the config are available.

    Args:
        config (OrchestratorConfig): The validated configuration.

    Raises:
        ConfigError: If a referenced provider is missing, or if no providers are detected.
    """
    referenced_providers = set()
    for pid, pcfg in config.providers.items():
        referenced_providers.add(pcfg.name.lower())

    detected_providers = {}
    
    # We check ALL registered providers to provide install hints if NONE are found
    for name, adapter_cls in _registry.items():
        try:
            # We instantiate without config just for detection
            adapter = get_adapter(name)
            if adapter.detect():
                detected_providers[name] = True
            else:
                detected_providers[name] = False
        except Exception as e:
            # AC5: Handle detection failure
            # In a real app we would use a logger, but here we'll use print/sys.stderr
            # since the Story doesn't define a logging subsystem yet (it's in Epic 3).
            print(f"WARNING: Unexpected error detecting provider '{name}': {e}", file=sys.stderr)
            detected_providers[name] = False

    # AC4: No providers detected at all
    if not any(detected_providers.values()):
        error_lines = ["✗ No CLI providers detected. Please install at least one:"]
        for name, adapter_cls in _registry.items():
            error_lines.append(f"  - {name}: {adapter_cls.install_hint}")
        raise ConfigError("\n".join(error_lines))

    # AC1: Missing referenced provider
    missing_referenced = []
    for name in referenced_providers:
        if not detected_providers.get(name, False):
            missing_referenced.append(name)

    if missing_referenced:
        error_lines = ["✗ Missing referenced provider(s):"]
        for name in missing_referenced:
            adapter_cls = _registry.get(name)
            hint = adapter_cls.install_hint if adapter_cls else "Install the CLI for this provider."
            error_lines.append(f"  - {name}: {hint}")
        raise ConfigError("\n".join(error_lines))

    # AC2 & AC3: Single-provider or all referenced providers present - validation passes.


def discover_config_path(explicit_path: str | None = None) -> pathlib.Path:
    """Discover the configuration file path.

    Discovery order: explicit_path > ./bmad-orch.yaml

    Returns:
        pathlib.Path: The resolved config path.

    Raises:
        ConfigError: If no config is found.
    """
    if explicit_path is not None:
        if not explicit_path.strip():
            raise ConfigError("✗ Empty config path provided — pass a valid file path or omit the flag")
        path = pathlib.Path(explicit_path).resolve()
        if not path.exists():
            raise ConfigError(f"✗ Explicit config not found at '{explicit_path}' — check the path")
        if not path.is_file():
            raise ConfigError(f"✗ Config path '{explicit_path}' is not a file — provide a YAML file path")
        return path

    cwd_path = (pathlib.Path.cwd() / "bmad-orch.yaml").resolve()
    if cwd_path.exists():
        if not cwd_path.is_file():
            raise ConfigError("✗ 'bmad-orch.yaml' exists but is not a file — remove it and create a valid config file")
        return cwd_path

    raise ConfigError("✗ No config found — create bmad-orch.yaml or use --config <path>")


def load_config_file(path: pathlib.Path) -> dict[str, Any]:
    """Load and parse a YAML configuration file.

    Returns:
        dict: The parsed raw configuration.

    Raises:
        ConfigError: If YAML parsing fails or the file is empty/too large.
    """
    try:
        file_size = path.stat().st_size
    except OSError as e:
        raise ConfigError(f"✗ Failed to read config file '{path}' — {e}") from e

    if file_size == 0:
        raise ConfigError(f"✗ Config file '{path}' is empty — add configuration content")

    if file_size > _MAX_CONFIG_SIZE:
        raise ConfigError(
            f"✗ Config file '{path}' is too large ({file_size} bytes) — maximum is {_MAX_CONFIG_SIZE} bytes"
        )

    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        error_msg = str(e)
        raise ConfigError(f"✗ YAML syntax error in '{path}' — {error_msg}") from e
    except Exception as e:
        raise ConfigError(f"✗ Failed to read config file '{path}' — {e}") from e

    if not isinstance(data, dict):
        raise ConfigError(f"✗ Config file '{path}' does not contain a YAML mapping — check the file structure")

    return data


def get_config(explicit_path: str | None = None) -> tuple[OrchestratorConfig, pathlib.Path]:
    """Discover, load, and validate the configuration.

    Returns:
        Tuple of (validated config, resolved source path).

    Raises:
        ConfigError: If discovery, loading, or validation fails.
    """
    path = discover_config_path(explicit_path)
    data = load_config_file(path)
    return validate_config(data), path
