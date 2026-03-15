import pytest

from bmad_orch.engine.prompt_resolver import PromptResolver
from bmad_orch.exceptions import TemplateVariableError


def test_prompt_resolver_replaces_whitelist():
    resolver = PromptResolver()
    assert resolver.resolve("Hello {name}", {"name": "World"}) == "Hello World"
    assert resolver.resolve("{greeting} {name}", {"greeting": "Hi", "name": "Alice"}) == "Hi Alice"

def test_prompt_resolver_missing_variable():
    resolver = PromptResolver()
    with pytest.raises(TemplateVariableError) as exc:
        resolver.resolve("Hello {name} {missing}", {"name": "Bob"})
    assert "missing" in str(exc.value)

def test_prompt_resolver_injection_resistance():
    resolver = PromptResolver()
    # It shouldn't run python formatting logic recursively
    assert resolver.resolve("Hello {name}", {"name": "{not_in_context}"}) == "Hello {not_in_context}"

def test_prompt_resolver_missing_variable_names_in_message():
    resolver = PromptResolver()
    with pytest.raises(TemplateVariableError) as exc:
        resolver.resolve("{a} {b} {c}", {"a": "1"})
    assert "b" in str(exc.value)
    assert "c" in str(exc.value)
