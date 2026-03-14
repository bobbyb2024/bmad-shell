import pathlib


def test_pre_commit_config_exists(project_root: pathlib.Path):
    """Verify that .pre-commit-config.yaml exists (AC11)."""
    assert (project_root / ".pre-commit-config.yaml").exists()


def test_github_actions_ci_config_exists(project_root: pathlib.Path):
    """Verify that .github/workflows/ci.yml exists (AC12)."""
    assert (project_root / ".github/workflows/ci.yml").exists()


def test_ci_workflow_jobs(project_root: pathlib.Path):
    """Verify that ci.yml contains the required jobs (AC12)."""
    ci_path = project_root / ".github/workflows/ci.yml"
    content = ci_path.read_text().lower()
    assert "ruff" in content
    assert "pyright" in content
    assert "pytest" in content
    assert "import-linter" in content or "lint-imports" in content
