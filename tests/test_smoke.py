from typer.testing import CliRunner

from bmad_orch.cli import app

runner = CliRunner()


def test_import_core_modules():
    """Verify that all core modules can be imported."""
    import bmad_orch.cli
    import bmad_orch.errors
    import bmad_orch.types

    assert bmad_orch.cli is not None
    assert bmad_orch.types is not None
    assert bmad_orch.errors is not None


def test_cli_help_smoke():
    """Verify that 'bmad-orch --help' runs and displays expected subcommands."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "start" in result.stdout
    assert "resume" in result.stdout
    assert "status" in result.stdout
    assert "validate" in result.stdout
    assert "--init" in result.stdout


def test_core_types_availability():
    """Verify core types are available in bmad_orch.types."""
    from bmad_orch.types import EscalationState, OutputChunk, ProviderName, StepOutcome, StepType

    assert all([OutputChunk, EscalationState, ProviderName, StepOutcome, StepType])


def test_error_hierarchy_availability():
    """Verify error hierarchy is available in bmad_orch.errors."""
    from bmad_orch.errors import (
        BmadOrchError,
        ConfigError,
        GitError,
        ProviderCrashError,
        ProviderError,
        ProviderNotFoundError,
        ProviderTimeoutError,
        ResourceError,
        StateError,
        WizardError,
    )

    assert issubclass(ConfigError, BmadOrchError)
    assert issubclass(ProviderError, BmadOrchError)
    assert issubclass(ProviderNotFoundError, ProviderError)
    assert issubclass(ProviderTimeoutError, ProviderError)
    assert issubclass(ProviderCrashError, ProviderError)
    assert issubclass(StateError, BmadOrchError)
    assert issubclass(ResourceError, BmadOrchError)
    assert issubclass(GitError, BmadOrchError)
    assert issubclass(WizardError, BmadOrchError)


def test_py_typed_exists():
    """Verify that py.typed exists in the package root."""
    from pathlib import Path

    import bmad_orch

    package_path = Path(bmad_orch.__file__).parent
    assert (package_path / "py.typed").exists()


def test_error_severity_defaults():
    """Verify that error severities are correctly applied."""
    from bmad_orch.errors import BmadOrchError, ConfigError, ErrorSeverity

    err = ConfigError("test")
    assert err.severity == ErrorSeverity.BLOCKING

    err2 = BmadOrchError("test", severity=ErrorSeverity.RECOVERABLE)
    assert err2.severity == ErrorSeverity.RECOVERABLE
