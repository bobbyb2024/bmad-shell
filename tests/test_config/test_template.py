"""Tests for the template variable registry (Story 1.4)."""

from collections.abc import Mapping

import pytest

from bmad_orch.config.template import TemplateResolver, resolve_step_prompts
from bmad_orch.exceptions import ConfigError


@pytest.fixture
def resolver() -> TemplateResolver:
    return TemplateResolver()


@pytest.fixture
def sample_context() -> Mapping[str, str]:
    return {
        "next_story_id": "1-5",
        "current_story_file": "_bmad-output/implementation-artifacts/1-4-prompt-template-variable-registry.md",
    }


# --- AC1: Resolve {next_story_id} ---


def test_template_resolver_resolves_next_story_id(
    resolver: TemplateResolver, sample_context: Mapping[str, str]
) -> None:
    prompt = "/bmad-create-story for story {next_story_id}"
    result = resolver.resolve(prompt, sample_context, step_name="create-story")
    assert result == "/bmad-create-story for story 1-5"


# --- AC2: Resolve {current_story_file} ---


def test_template_resolver_resolves_current_story_file(
    resolver: TemplateResolver, sample_context: Mapping[str, str]
) -> None:
    prompt = "/bmad-dev-story {current_story_file}"
    result = resolver.resolve(prompt, sample_context, step_name="dev-story")
    assert (
        result
        == "/bmad-dev-story _bmad-output/implementation-artifacts/1-4-prompt-template-variable-registry.md"
    )


# --- AC3: Error on unknown variables ---


def test_template_resolver_raises_config_error_on_unknown_variable(
    resolver: TemplateResolver, sample_context: Mapping[str, str]
) -> None:
    prompt = "do something with {nonexistent_var}"
    with pytest.raises(ConfigError) as excinfo:
        resolver.resolve(prompt, sample_context, step_name="create-story")
    msg = str(excinfo.value)
    expected = (
        "\u2717 Unresolvable template variable 'nonexistent_var' "
        "in step 'create-story' \u2014 check prompt template in config"
    )
    assert msg == expected


def test_template_resolver_reports_all_missing_variables(
    resolver: TemplateResolver,
) -> None:
    prompt = "use {missing_a} and {missing_b}"
    with pytest.raises(ConfigError) as excinfo:
        resolver.resolve(prompt, {}, step_name="some-step")
    msg = str(excinfo.value)
    expected = (
        "\u2717 Unresolvable template variables 'missing_a', 'missing_b' "
        "in step 'some-step' \u2014 check prompt template in config"
    )
    assert msg == expected


# --- AC4: Resolve multiple variables in single pass ---


def test_template_resolver_resolves_multiple_variables_single_pass(
    resolver: TemplateResolver, sample_context: Mapping[str, str]
) -> None:
    prompt = "create {next_story_id} then review {current_story_file}"
    result = resolver.resolve(prompt, sample_context, step_name="multi-step")
    assert result == (
        "create 1-5 then review "
        "_bmad-output/implementation-artifacts/1-4-prompt-template-variable-registry.md"
    )


# --- AC5: Pass through plain text ---


def test_template_resolver_passes_through_plain_text(
    resolver: TemplateResolver, sample_context: Mapping[str, str]
) -> None:
    prompt = "just a plain prompt with no variables"
    result = resolver.resolve(prompt, sample_context, step_name="plain-step")
    assert result == "just a plain prompt with no variables"


def test_template_resolver_passes_through_empty_string(
    resolver: TemplateResolver, sample_context: Mapping[str, str]
) -> None:
    # Edge case: empty prompt (though StepConfig requires min_length=1, test resolver in isolation)
    result = resolver.resolve("", sample_context, step_name="empty-step")
    assert result == ""


# --- find_variables tests ---


def test_find_variables_returns_variable_names(resolver: TemplateResolver) -> None:
    prompt = "use {next_story_id} and {current_story_file} here"
    variables = resolver.find_variables(prompt)
    assert variables == {"next_story_id", "current_story_file"}


def test_find_variables_returns_empty_set_for_plain_text(
    resolver: TemplateResolver,
) -> None:
    assert resolver.find_variables("no variables here") == set()


def test_find_variables_returns_empty_set_for_empty_string(
    resolver: TemplateResolver,
) -> None:
    assert resolver.find_variables("") == set()


# --- Edge cases ---


def test_template_resolver_handles_adjacent_variables(
    resolver: TemplateResolver, sample_context: Mapping[str, str]
) -> None:
    prompt = "{next_story_id}{current_story_file}"
    result = resolver.resolve(prompt, sample_context, step_name="adjacent")
    assert result == (
        "1-5_bmad-output/implementation-artifacts/1-4-prompt-template-variable-registry.md"
    )


def test_template_resolver_handles_prompt_with_only_variable(
    resolver: TemplateResolver, sample_context: Mapping[str, str]
) -> None:
    prompt = "{next_story_id}"
    result = resolver.resolve(prompt, sample_context, step_name="only-var")
    assert result == "1-5"


def test_template_resolver_ignores_non_identifier_braces(
    resolver: TemplateResolver, sample_context: Mapping[str, str]
) -> None:
    # Braces with non-identifier content are not treated as variables
    prompt = "json: {123} and {}"
    result = resolver.resolve(prompt, sample_context, step_name="json-step")
    assert result == "json: {123} and {}"


def test_template_resolver_is_case_sensitive(
    resolver: TemplateResolver, sample_context: Mapping[str, str]
) -> None:
    prompt = "{Next_Story_Id}"
    with pytest.raises(ConfigError) as excinfo:
        resolver.resolve(prompt, sample_context, step_name="case-step")
    assert "Next_Story_Id" in str(excinfo.value)


def test_template_resolver_error_format_single_variable(
    resolver: TemplateResolver,
) -> None:
    prompt = "use {bad_var}"
    with pytest.raises(ConfigError) as excinfo:
        resolver.resolve(prompt, {}, step_name="my-step")
    msg = str(excinfo.value)
    assert msg.startswith("\u2717")  # starts with ✗
    assert "bad_var" in msg
    assert "my-step" in msg
    assert "check prompt template in config" in msg


def test_template_resolver_error_format_multiple_variables(
    resolver: TemplateResolver,
) -> None:
    prompt = "use {var_a} and {var_b}"
    with pytest.raises(ConfigError) as excinfo:
        resolver.resolve(prompt, {}, step_name="multi-step")
    msg = str(excinfo.value)
    assert "var_a" in msg
    assert "var_b" in msg
    assert msg.startswith("\u2717")  # starts with ✗


def test_template_resolver_no_partial_resolution(
    resolver: TemplateResolver, sample_context: Mapping[str, str]
) -> None:
    """When one variable is resolvable and another is not, no resolution happens."""
    prompt = "{next_story_id} and {nonexistent}"
    with pytest.raises(ConfigError):
        resolver.resolve(prompt, sample_context, step_name="partial-step")


# --- resolve_step_prompts tests ---


def test_resolve_step_prompts_resolves_all_prompts(
    sample_context: Mapping[str, str],
) -> None:
    from bmad_orch.config.schema import validate_config

    data = {
        "providers": {1: {"name": "claude", "cli": "claude", "model": "opus-4"}},
        "cycles": {
            "story": {
                "steps": [
                    {
                        "skill": "create",
                        "provider": 1,
                        "type": "generative",
                        "prompt": "/create {next_story_id}",
                    },
                    {
                        "skill": "review",
                        "provider": 1,
                        "type": "validation",
                        "prompt": "/review {current_story_file}",
                    },
                ],
            },
        },
        "git": {"commit_at": "cycle", "push_at": "end"},
        "pauses": {"between_steps": 1, "between_cycles": 1, "between_workflows": 1},
        "error_handling": {"retry_transient": True, "max_retries": 3, "retry_delay": 10},
    }
    config = validate_config(data)
    resolved = resolve_step_prompts(config, dict(sample_context))

    assert resolved.cycles["story"].steps[0].prompt == "/create 1-5"
    assert resolved.cycles["story"].steps[1].prompt == (
        "/review _bmad-output/implementation-artifacts/1-4-prompt-template-variable-registry.md"
    )
    # Original config is unchanged (immutability)
    assert config.cycles["story"].steps[0].prompt == "/create {next_story_id}"


def test_resolve_step_prompts_raises_on_unknown_variable() -> None:
    from bmad_orch.config.schema import validate_config

    data = {
        "providers": {1: {"name": "p", "cli": "c", "model": "m"}},
        "cycles": {
            "dev": {
                "steps": [
                    {
                        "skill": "s",
                        "provider": 1,
                        "type": "generative",
                        "prompt": "/run {unknown_var}",
                    },
                ],
            },
        },
        "git": {"commit_at": "cycle", "push_at": "end"},
        "pauses": {"between_steps": 1, "between_cycles": 1, "between_workflows": 1},
        "error_handling": {"retry_transient": True, "max_retries": 3, "retry_delay": 10},
    }
    config = validate_config(data)
    with pytest.raises(ConfigError) as excinfo:
        resolve_step_prompts(config, {})
    assert "unknown_var" in str(excinfo.value)
    assert "dev[0]" in str(excinfo.value)


def test_resolve_step_prompts_passes_through_plain_prompts() -> None:
    from bmad_orch.config.schema import validate_config

    data = {
        "providers": {1: {"name": "p", "cli": "c", "model": "m"}},
        "cycles": {
            "c1": {
                "steps": [
                    {
                        "skill": "s",
                        "provider": 1,
                        "type": "generative",
                        "prompt": "plain prompt no vars",
                    },
                ],
            },
        },
        "git": {"commit_at": "cycle", "push_at": "end"},
        "pauses": {"between_steps": 1, "between_cycles": 1, "between_workflows": 1},
        "error_handling": {"retry_transient": True, "max_retries": 3, "retry_delay": 10},
    }
    config = validate_config(data)
    resolved = resolve_step_prompts(config, {})
    assert resolved.cycles["c1"].steps[0].prompt == "plain prompt no vars"
