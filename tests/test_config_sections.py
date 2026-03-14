def test_ruff_config_section(pyproject_content):
    """Verify [tool.ruff] section in pyproject.toml (AC6)."""
    assert "ruff" in pyproject_content.get("tool", {})


def test_pyright_config_section(pyproject_content):
    """Verify [tool.pyright] section in pyproject.toml (AC6)."""
    pyright_config = pyproject_content.get("tool", {}).get("pyright", {})
    assert pyright_config is not None
    assert pyright_config.get("typeCheckingMode") == "strict"


def test_pytest_config_section(pyproject_content):
    """Verify [tool.pytest.ini_options] section in pyproject.toml (AC6, AC9)."""
    pytest_config = pyproject_content.get("tool", {}).get("pytest", {}).get("ini_options", {})
    assert pytest_config is not None
    assert "addopts" in pytest_config
    assert "--cov=bmad_orch" in pytest_config["addopts"]


def test_importlinter_config_section(pyproject_content):
    """Verify [tool.importlinter] section in pyproject.toml (AC6, AC10)."""
    assert "importlinter" in pyproject_content.get("tool", {})
