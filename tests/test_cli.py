from typer.testing import CliRunner

from bmad_orch.cli import app

runner = CliRunner()


def test_cli_help():
    """Verify that CLI help displays expected subcommands."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "start" in result.stdout
    assert "resume" in result.stdout
    assert "status" in result.stdout
    assert "validate" in result.stdout
    assert "--init" in result.stdout


def test_cli_init_no_fall_through():
    """Verify that --init exits after wizard and doesn't fall through (AC7)."""
    # Invoke --init with a subcommand; --init should exit before the subcommand runs
    result = runner.invoke(app, ["--init", "start"])
    assert result.exit_code == 0
    # The start command prints "Starting bmad-orch..." — this must NOT appear
    assert "Starting bmad-orch" not in result.stdout


def test_cli_subcommands_exist():
    """Verify subcommands can be invoked (even if they fail or do nothing yet)."""
    for cmd in ["start", "resume", "status", "validate"]:
        result = runner.invoke(app, [cmd, "--help"])
        assert result.exit_code == 0
