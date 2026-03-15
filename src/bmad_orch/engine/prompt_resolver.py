import re
from collections.abc import Mapping

from bmad_orch.exceptions import TemplateVariableError


class PromptResolver:
    """Safe whitelist-based template variable substitution."""
    
    def resolve(self, prompt: str, context: Mapping[str, str]) -> str:
        keys_in_prompt = set(re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", prompt))
        missing = keys_in_prompt - context.keys()
        if missing:
            raise TemplateVariableError(f"Missing required variables: {', '.join(sorted(missing))}")
            
        result = prompt
        for key in keys_in_prompt:
            result = result.replace(f"{{{key}}}", str(context[key]))
            
        return result
