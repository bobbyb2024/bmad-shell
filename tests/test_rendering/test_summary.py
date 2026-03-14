import pytest
from rich.console import Console
from bmad_orch.config.schema import validate_config
from bmad_orch.rendering.summary import render_playbook_summary

@pytest.fixture
def valid_config():
    data = {
        "providers": {
            1: {"name": "claude", "cli": "claude", "model": "opus-4"},
            2: {"name": "gemini", "cli": "gemini", "model": "gemini-2.5-pro"},
        },
        "cycles": {
            "story": {
                "steps": [
                    {"skill": "create-story", "provider": 1, "type": "generative", "prompt": "p1"},
                    {"skill": "review-story", "provider": 2, "type": "validation", "prompt": "p2"},
                ],
                "repeat": 2,
            }
        },
        "git": {"commit_at": "cycle", "push_at": "end"},
        "pauses": {"between_steps": 5.0, "between_cycles": 15.0, "between_workflows": 30.0},
        "error_handling": {"retry_transient": True, "max_retries": 3, "retry_delay": 10.0},
    }
    return validate_config(data)

def test_render_playbook_summary_smoke(valid_config):
    # Smoke test to ensure it doesn't crash
    render_playbook_summary(valid_config, dry_run=False)
    render_playbook_summary(valid_config, dry_run=True)

def test_render_playbook_summary_output(valid_config, capsys):
    # Check if key elements are present in output
    render_playbook_summary(valid_config, dry_run=False)
    captured = capsys.readouterr()
    assert "PRE-FLIGHT SUMMARY" in captured.out
    assert "Providers Registry" in captured.out
    assert "Execution Plan" in captured.out
    assert "claude" in captured.out
    assert "gemini" in captured.out
    assert "create-story" in captured.out

def test_render_playbook_summary_dry_run_output(valid_config, capsys):
    render_playbook_summary(valid_config, dry_run=True)
    captured = capsys.readouterr()
    assert "DRY RUN: PLAYBOOK EXECUTION PLAN" in captured.out
    assert "Dry run complete" in captured.out
