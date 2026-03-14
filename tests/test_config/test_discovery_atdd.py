import yaml
import pytest
import copy
from typer.testing import CliRunner
from bmad_orch.cli import app

VALID_CONFIG_DATA = {
    "providers": {1: {"name": "p1", "cli": "c1", "model": "m1"}},
    "cycles": {
        "c1": {
            "steps": [
                {"skill": "s1", "provider": 1, "type": "generative", "prompt": "p1"}
            ]
        }
    },
    "git": {"commit_at": "cycle", "push_at": "end"},
    "pauses": {"between_steps": 1, "between_cycles": 1, "between_workflows": 1},
    "error_handling": {"retry_transient": True, "max_retries": 3, "retry_delay": 10},
}

# Story 1-3: Config File Loading & Discovery
# Acceptance Criteria:
# 1. CWD discovery of bmad-orch.yaml.
# 2. Explicit path overrides CWD.
# 3. Exit code 2 if no config found.
# 4. Success report (exit 0) with valid config.
# 5. YAML syntax error (exit 2).

runner = CliRunner()

@pytest.fixture
def config_factory():
    """Data factory for configuration objects with overrides."""
    def _create(overrides=None):
        # Deep copy to avoid mutating the original
        data = copy.deepcopy(VALID_CONFIG_DATA)
        if overrides:
            # Simple update for flat overrides
            data.update(overrides)
        return data
    return _create

@pytest.mark.skip(reason="RED PHASE: Story 1-3 AC1 - CWD discovery")
def test_config_discovery_cwd(tmp_path, monkeypatch, config_factory):
    """
    AC 1: Given a bmad-orch.yaml exists in the current working directory, 
    When I run bmad-orch validate with no flags, 
    Then the system discovers and loads bmad-orch.yaml from the cwd.
    """
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "bmad-orch.yaml"
    config_data = config_factory()
    config_file.write_text(yaml.dump(config_data))
    
    # We invoke the CLI command 'validate'
    result = runner.invoke(app, ["validate"])
    
    assert result.exit_code == 0
    assert "Configuration is valid" in result.stdout
    # Should report the path it loaded from
    assert str(config_file.resolve()) in result.stdout

@pytest.mark.skip(reason="RED PHASE: Story 1-3 AC2 - Explicit path overrides CWD")
def test_config_discovery_explicit_path_overrides_cwd(tmp_path, monkeypatch, config_factory):
    """
    AC 2: Given a config file exists at /path/to/my-config.yaml, 
    When I run bmad-orch validate --config /path/to/my-config.yaml, 
    Then the system loads the config from the explicit path (overriding cwd discovery).
    """
    # Create invalid config in CWD to prove it's ignored
    monkeypatch.chdir(tmp_path)
    cwd_config = tmp_path / "bmad-orch.yaml"
    cwd_config.write_text("invalid: [yaml: structure")
    
    # Create valid explicit config in another directory
    other_dir = tmp_path / "custom_configs"
    other_dir.mkdir()
    explicit_config = other_dir / "my-config.yaml"
    
    # Use factory with override to distinguish from CWD config
    config_data = config_factory({"providers": {1: {"name": "explicit-provider", "cli": "c1", "model": "m1"}}})
    explicit_config.write_text(yaml.dump(config_data))
    
    result = runner.invoke(app, ["validate", "--config", str(explicit_config)])
    
    assert result.exit_code == 0
    assert "Configuration is valid" in result.stdout
    assert "explicit-provider" in result.stdout
    assert str(explicit_config.resolve()) in result.stdout

@pytest.mark.skip(reason="RED PHASE: Story 1-3 AC3 - Exit code 2 if no config found")
def test_config_discovery_no_config_found(tmp_path, monkeypatch):
    """
    AC 3: Given no bmad-orch.yaml exists in cwd and no --config flag is provided, 
    When I run bmad-orch validate, 
    Then the system exits with code 2 and a clear error.
    """
    monkeypatch.chdir(tmp_path)
    # Ensure directory is empty
    
    result = runner.invoke(app, ["validate"])
    
    assert result.exit_code == 2
    assert "No config found" in result.stdout
    assert "create bmad-orch.yaml or use --config" in result.stdout

@pytest.mark.skip(reason="RED PHASE: Story 1-3 AC4 - Success report with valid config")
def test_config_discovery_success_report(tmp_path, monkeypatch, config_factory):
    """
    AC 4: Given a valid config file, 
    When I run bmad-orch validate, 
    Then the system reports schema correctness and exits with code 0.
    """
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "bmad-orch.yaml"
    # Use factory to ensure valid data
    config_data = config_factory()
    config_file.write_text(yaml.dump(config_data))
    
    result = runner.invoke(app, ["validate"])
    
    assert result.exit_code == 0
    assert "Configuration is valid" in result.stdout
    # Verify specific provider and model from VALID_CONFIG_DATA are in the success report
    assert "p1" in result.stdout 
    assert "m1" in result.stdout

@pytest.mark.skip(reason="RED PHASE: Story 1-3 AC5 - YAML syntax error")
def test_config_discovery_yaml_syntax_error(tmp_path, monkeypatch):
    """
    AC 5: Given a config file with a YAML syntax error, 
    When I run bmad-orch validate, 
    Then the system exits with code 2 and a clear error.
    """
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "bmad-orch.yaml"
    # Malformed YAML: missing closing bracket
    config_file.write_text("invalid: [yaml: structure: {")
    
    result = runner.invoke(app, ["validate"])
    
    assert result.exit_code == 2
    assert "YAML syntax error" in result.stdout
    # Requirement: "clear error identifying the line and nature of the YAML parse failure"
    assert "line" in result.stdout or "column" in result.stdout or "at line" in result.stdout
