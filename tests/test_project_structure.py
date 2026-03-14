import pathlib


def test_project_layout(project_root: pathlib.Path):
    """Verify the expected project directory layout (AC1)."""
    expected_paths = [
        "src/bmad_orch/__init__.py",
        "src/bmad_orch/py.typed",
        "src/bmad_orch/types/__init__.py",
        "src/bmad_orch/exceptions.py",
        "src/bmad_orch/cli.py",
        "pyproject.toml",
    ]
    for path in expected_paths:
        assert (project_root / path).exists(), f"Missing required file: {path}"


def test_python_version_pin(project_root: pathlib.Path):
    """Verify that .python-version pins 3.13 (AC2)."""
    version_file = project_root / ".python-version"
    assert version_file.exists()
    assert "3.13" in version_file.read_text().strip()


def test_uv_lock_exists(project_root: pathlib.Path):
    """Verify that uv.lock exists (AC3)."""
    assert (project_root / "uv.lock").exists()


def test_pep561_marker(project_root: pathlib.Path):
    """Verify that the package is marked as typed via py.typed (AC8)."""
    assert (project_root / "src/bmad_orch/py.typed").exists()
