"""Template variable registry for prompt resolution (FR9)."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import TYPE_CHECKING

from bmad_orch.errors import ConfigError

if TYPE_CHECKING:
    from bmad_orch.config.schema import OrchestratorConfig

# Matches {valid_python_identifier} — single curly braces around identifier names
_VARIABLE_PATTERN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


class TemplateResolver:
    """Resolves template variables in prompt strings from a context mapping.

    Variables use the ``{variable_name}`` syntax. All variables in a prompt
    must be resolvable from the provided context; unresolvable variables
    raise ``ConfigError``.
    """

    def find_variables(self, prompt: str) -> set[str]:
        """Return the set of variable names found in *prompt*."""
        return set(_VARIABLE_PATTERN.findall(prompt))

    def resolve(
        self,
        prompt: str,
        context: Mapping[str, str],
        *,
        step_name: str,
    ) -> str:
        """Resolve all template variables in *prompt* using *context*.

        All variables are validated before any substitution occurs (single-pass,
        no partial resolution).

        Raises:
            ConfigError: If any variable in the prompt is not present in *context*.
        """
        variables = self.find_variables(prompt)
        if not variables:
            return prompt

        missing = variables - set(context.keys())
        if missing:
            sorted_missing = sorted(missing)
            if len(sorted_missing) == 1:
                var_desc = f"'{sorted_missing[0]}'"
                label = "variable"
            else:
                var_desc = ", ".join(f"'{v}'" for v in sorted_missing)
                label = "variables"
            raise ConfigError(
                f"\u2717 Unresolvable template {label} {var_desc} "
                f"in step '{step_name}' \u2014 check prompt template in config"
            )

        def _replacer(match: re.Match[str]) -> str:
            return context[match.group(1)]

        return _VARIABLE_PATTERN.sub(_replacer, prompt)


def resolve_step_prompts(
    config: OrchestratorConfig,
    context: Mapping[str, str],
) -> OrchestratorConfig:
    """Return a copy of *config* with all step prompts resolved.

    Useful for dry-run preview and pre-flight validation (Story 1.5).

    Raises:
        ConfigError: If any prompt contains an unresolvable variable.
    """
    from bmad_orch.config.schema import CycleConfig, StepConfig

    resolver = TemplateResolver()
    resolved_cycles: dict[str, CycleConfig] = {}

    for cycle_id, cycle in config.cycles.items():
        resolved_steps: list[StepConfig] = []
        for i, step in enumerate(cycle.steps):
            resolved_prompt = resolver.resolve(
                step.prompt,
                context,
                step_name=f"{cycle_id}[{i}]",
            )
            resolved_steps.append(step.model_copy(update={"prompt": resolved_prompt}))
        resolved_cycles[cycle_id] = cycle.model_copy(update={"steps": resolved_steps})

    return config.model_copy(update={"cycles": resolved_cycles})
