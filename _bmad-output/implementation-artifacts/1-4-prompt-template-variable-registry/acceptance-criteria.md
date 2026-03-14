# Acceptance Criteria

1. **AC1: Resolve `{next_story_id}` variable** — Given a step prompt containing `{next_story_id}`, when the template variable registry resolves it, then the variable is replaced with the correct story identifier from orchestrator state.

2. **AC2: Resolve `{current_story_file}` variable** — Given a step prompt containing `{current_story_file}`, when the template variable registry resolves it, then the variable is replaced with the file path of the current story artifact.

3. **AC3: Error on unknown variables** — Given a step prompt containing an unknown variable `{nonexistent_var}`, when the template variable registry attempts resolution, then the step halts with a `ConfigError`: `✗ Unresolvable template variable '{nonexistent_var}' in step 'create-story' — check prompt template in config`

4. **AC4: Resolve multiple variables in single pass** — Given a step prompt containing multiple variables `{next_story_id}` and `{current_story_file}`, when the template variable registry resolves them, then all variables are replaced in a single pass with no partial resolution.

5. **AC5: Pass through plain text** — Given a step prompt with no template variables (plain text), when the template variable registry processes it, then the prompt is passed through unchanged.
