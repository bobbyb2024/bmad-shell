import pathlib
import subprocess


def test_ruff_configuration(project_root: pathlib.Path):
    """Verify that Ruff is configured and runs without errors."""
    result = subprocess.run(["uv", "run", "ruff", "check", "."], cwd=project_root, capture_output=True, text=True)
    assert result.returncode == 0


def test_pyright_configuration(project_root: pathlib.Path):
    """Verify that Pyright is configured and runs without errors (AC8)."""
    result = subprocess.run(["uv", "run", "pyright"], cwd=project_root, capture_output=True, text=True)
    assert result.returncode == 0


def test_import_linter_configuration(project_root: pathlib.Path):
    """Verify that import-linter is configured and runs without violations (AC10)."""
    result = subprocess.run(["uv", "run", "lint-imports"], cwd=project_root, capture_output=True, text=True)
    assert result.returncode == 0
    assert "0 broken" in result.stdout.lower()
