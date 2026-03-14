import pathlib
import tomllib

import pytest
import yaml

VALID_CONFIG_DATA = {
    "providers": {1: {"name": "p1", "cli": "c1", "model": "m1"}},
    "cycles": {
        "c1": {
            "steps": [
                {"skill": "s1", "provider": 1, "type": "generative", "prompt": "p1"}
            ]
        }
    },
    "git": {"commit_at": "cycle", "push_at": "end"},
    "pauses": {"between_steps": 1, "between_cycles": 1, "between_workflows": 1},
    "error_handling": {"retry_transient": True, "max_retries": 3, "retry_delay": 10},
}


@pytest.fixture
def project_root() -> pathlib.Path:
    """Fixture to get the project root directory."""
    return pathlib.Path(__file__).parent.parent


@pytest.fixture
def pyproject_content(project_root: pathlib.Path):
    """Fixture to read and parse pyproject.toml."""
    path = project_root / "pyproject.toml"
    with path.open("rb") as f:
        return tomllib.load(f)


@pytest.fixture
def valid_config_file(tmp_path):
    """Create a valid bmad-orch.yaml in tmp_path and return its Path."""
    config_file = tmp_path / "bmad-orch.yaml"
    config_file.write_text(yaml.dump(VALID_CONFIG_DATA))
    return config_file
