import pathlib
from typing import Any

import yaml

from bmad_orch.config.schema import OrchestratorConfig, validate_config
from bmad_orch.errors import ConfigError


def discover_config_path(explicit_path: str | None = None) -> pathlib.Path:
    """Discover the configuration file path.

    Discovery order: explicit_path > ./bmad-orch.yaml

    Returns:
        pathlib.Path: The discovered config path.

    Raises:
        ConfigError: If no config is found.
    """
    if explicit_path:
        path = pathlib.Path(explicit_path)
        if not path.exists():
            raise ConfigError(f"✗ Explicit config not found at '{explicit_path}' — check the path")
        return path

    cwd_path = pathlib.Path.cwd() / "bmad-orch.yaml"
    if cwd_path.exists():
        return cwd_path

    raise ConfigError("✗ No config found — create bmad-orch.yaml or use --config <path>")


def load_config_file(path: pathlib.Path) -> dict[str, Any]:
    """Load and parse a YAML configuration file.

    Returns:
        dict: The parsed raw configuration.

    Raises:
        ConfigError: If YAML parsing fails.
    """
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        # Try to extract line/nature if possible from YAMLError
        error_msg = str(e)
        raise ConfigError(f"✗ YAML syntax error in '{path}' — {error_msg}") from e
    except Exception as e:
        raise ConfigError(f"✗ Failed to read config file '{path}' — {e}") from e


def get_config(explicit_path: str | None = None) -> OrchestratorConfig:
    """Discover, load, and validate the configuration.

    Returns:
        OrchestratorConfig: The validated configuration object.

    Raises:
        ConfigError: If discovery, loading, or validation fails.
    """
    path = discover_config_path(explicit_path)
    data = load_config_file(path)
    return validate_config(data)
