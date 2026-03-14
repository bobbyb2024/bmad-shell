def test_core_dependencies(pyproject_content):
    """Verify core dependencies are in pyproject.toml (AC4)."""
    dependencies = pyproject_content.get("project", {}).get("dependencies", [])
    expected = [
        "typer",
        "rich",
        "pydantic",
        "pydantic-settings",
        "pyyaml",
        "structlog",
        "psutil",
        "libtmux",
    ]
    for dep in expected:
        assert any(dep in d for d in dependencies), f"Missing core dependency: {dep}"


def test_dev_dependencies(pyproject_content):
    """Verify development dependencies are in pyproject.toml (AC4)."""
    # uv uses [dependency-groups] or [tool.uv.dev-dependencies]
    dev_deps = pyproject_content.get("dependency-groups", {}).get("dev", [])
    expected = [
        "pytest",
        "pytest-cov",
        "ruff",
        "pyright",
        "pre-commit",
        "import-linter",
    ]
    for dep in expected:
        assert any(dep in d for d in dev_deps), f"Missing dev dependency: {dep}"
