import pathlib
from typing import Any

import yaml

from bmad_orch.config.schema import OrchestratorConfig, validate_config
from bmad_orch.exceptions import ConfigError

_MAX_CONFIG_SIZE = 1_048_576  # 1 MB


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
