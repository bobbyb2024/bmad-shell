import pathlib
import subprocess


def test_gitignore_rules(project_root: pathlib.Path):
    """Verify that .python-version and uv.lock are NOT gitignored (AC2, AC3)."""
    critical_files = [
        ".python-version",
        "uv.lock",
        "pyproject.toml",
    ]
    for file in critical_files:
        result = subprocess.run(["git", "check-ignore", file], cwd=project_root, capture_output=True, text=True)
        # If exit code is 1, it means the file is NOT ignored (this is what we want)
        assert result.returncode == 1, f"File {file} should NOT be gitignored (AC2/AC3)"


def test_gitignore_common_ignores(project_root: pathlib.Path):
    """Verify common things ARE gitignored."""
    common_ignores = [
        "__pycache__/",
        ".venv/",
        ".pytest_cache/",
        ".ruff_cache/",
        ".pyright_cache/",
    ]
    for item in common_ignores:
        result = subprocess.run(["git", "check-ignore", item], cwd=project_root, capture_output=True, text=True)
        # If exit code is 0, it means it IS ignored
        assert result.returncode == 0, f"{item} should be gitignored"
