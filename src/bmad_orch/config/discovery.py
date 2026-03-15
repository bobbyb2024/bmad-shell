import pathlib
import sys
from typing import Any, cast

import yaml

from bmad_orch.config.schema import OrchestratorConfig, validate_config
from bmad_orch.exceptions import ConfigError, ConfigProviderError

_MAX_CONFIG_SIZE = 1_048_576  # 1 MB


def validate_provider_availability(
    config: OrchestratorConfig,
    registry: dict[str, Any] | None = None,
) -> None:
    """Validate that all providers referenced in the config are available.

    Args:
        config (OrchestratorConfig): The validated configuration.
        registry: Provider adapter class registry. If None, imports from providers.

    Raises:
        ConfigError: If a referenced provider is missing, or if no providers are detected.
    """
    if registry is None:
        msg = "registry must be provided (pass providers.get_registry() from the caller)"
        raise ConfigError(msg)
    # Map provider name -> set of custom CLI paths used in config
    referenced_providers: dict[str, set[str | None]] = {}
    for _pid, pcfg in config.providers.items():
        name = pcfg.name.lower()
        if name not in referenced_providers:
            referenced_providers[name] = set()
        referenced_providers[name].add(pcfg.cli)

    detected_providers: dict[str, dict[str | None, bool]] = {}
    
    # We check ALL registered providers to provide install hints if NONE are found
    for name, adapter_cls in registry.items():
        detected_providers[name] = {}
        adapter: Any = None

        # 1. Check default detection (for AC4 "No providers detected")
        try:
            adapter = adapter_cls()
            detected_providers[name][None] = adapter.detect()
        except Exception as e:
            print(f"WARNING: Unexpected error detecting provider '{name}' (default): {e}", file=sys.stderr)
            detected_providers[name][None] = False

        # 2. Check specific CLI paths referenced in config (for AC1/AC2)
        if name in referenced_providers and adapter is not None:
            for custom_cli in referenced_providers[name]:
                if custom_cli is None:
                    continue
                try:
                    # We can reuse the adapter instance or create a new one,
                    # detect() should be stateless or handle its own caching.
                    if adapter.detect(cli_path=custom_cli):
                        detected_providers[name][custom_cli] = True
                    else:
                        detected_providers[name][custom_cli] = False
                except Exception as e:
                    print(
                        f"WARNING: Unexpected error detecting provider '{name}' (custom: {custom_cli}): {e}",
                        file=sys.stderr,
                    )
                    detected_providers[name][custom_cli] = False

    # AC4: No providers detected at all (check all default and custom detections)
    any_detected = False
    for name in detected_providers:
        if any(detected_providers[name].values()):
            any_detected = True
            break
            
    if not any_detected:
        error_lines: list[str] = ["✗ No CLI providers detected. Please install at least one:"]
        for name, adapter_cls in registry.items():
            error_lines.append(f"  - {name}: {adapter_cls.install_hint}")
        raise ConfigError("\n".join(error_lines))

    # AC1: Missing referenced provider
    missing_referenced: list[tuple[str, str | None]] = []
    for name, custom_paths in referenced_providers.items():
        for path in custom_paths:
            # If path is None, check default. If path is set, check specific.
            if not detected_providers.get(name, {}).get(path, False):
                missing_referenced.append((name, path))

    if missing_referenced:
        error_lines_missing: list[str] = ["✗ Missing referenced provider(s):"]
        for name, path in missing_referenced:
            ref_adapter_cls = registry.get(name)
            hint: str = ref_adapter_cls.install_hint if ref_adapter_cls else "Install the CLI for this provider."
            display_name: str = f"{name} (cli: {path})" if path else name
            error_lines_missing.append(f"  - {display_name}: {hint}")
        error_lines_missing.append("OR update your config to use an available provider.")
        raise ConfigProviderError("\n".join(error_lines_missing))

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

    return cast(dict[str, Any], data)


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
