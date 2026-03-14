from typer.testing import CliRunner

from bmad_orch.cli import app

runner = CliRunner()


def test_cli_validate_no_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 2
    assert "No config found" in result.stdout


def test_cli_validate_cwd(valid_config_file, monkeypatch):
    monkeypatch.chdir(valid_config_file.parent)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0
    assert "Configuration is valid" in result.stdout
    assert "p1" in result.stdout
    assert "m1" in result.stdout
    assert "loaded from" in result.stdout


def test_cli_validate_explicit(valid_config_file):
    result = runner.invoke(app, ["validate", "--config", str(valid_config_file)])
    assert result.exit_code == 0
    assert "Configuration is valid" in result.stdout


def test_cli_validate_explicit_not_found(tmp_path):
    result = runner.invoke(app, ["validate", "--config", str(tmp_path / "nope.yaml")])
    assert result.exit_code == 2
    assert "Explicit config not found" in result.stdout


def test_cli_validate_invalid_yaml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "bmad-orch.yaml"
    config_file.write_text("invalid: [yaml: structure")
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 2
    assert "YAML syntax error" in result.stdout


def test_cli_validate_empty_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "bmad-orch.yaml"
    config_file.touch()
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 2
    assert "empty" in result.stdout
