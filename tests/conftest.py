import pathlib
import tomllib

import pytest


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
