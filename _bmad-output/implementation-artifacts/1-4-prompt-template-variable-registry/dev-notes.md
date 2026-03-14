# Dev Notes

## Architecture Requirements

- **Module location:** `src/bmad_orch/config/template.py` — template resolution is a config-layer concern, not engine
- **Layer rule (strict):** `config/` can only import from `types` and `errors`. Enforced by `import-linter` in `pyproject.toml`
- **TemplateResolver must NOT import from:** `engine/`, `state/`, `providers/`, `rendering/`
- **The resolver receives context as a `Mapping[str, str]`** — it does not know where values come from. The engine/runner will construct the context dict at runtime (Epic 3). Story 1.4 only builds the resolution mechanism.

## Variable Syntax & Resolution Rules

- **Variable pattern:** `{variable_name}` — single curly braces (NOT double `{{}}`)
- **Regex pattern:** `r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'` — matches valid Python identifier names inside braces
- **Single-pass resolution:** Collect ALL variables first, validate ALL are resolvable, then substitute ALL at once. Never partial-resolve.
- **Case-sensitive:** `{next_story_id}` and `{Next_Story_Id}` are different variables
- **No nested resolution:** `{var_{name}}` is NOT supported — only flat variable references
- **Literal braces:** If users need literal `{` or `}` in prompts, this is NOT required for Story 1.4 (can be addressed in future stories if needed)

## Known Template Variables (for test context)

From PRD config examples, these variables will exist at runtime:
- `next_story_id` — e.g., `"1-5"` (next story to create)
- `current_story_file` — e.g., `"_bmad-output/implementation-artifacts/1-4-prompt-template-variable-registry.md"`

## Error Handling Pattern

- **Error class:** `ConfigError` from `bmad_orch.errors` (severity: `BLOCKING`)
- **Error message format:** `✗ Unresolvable template variable '{var}' in step '{step}' — check prompt template in config`
- **Multiple missing vars:** Report ALL in one error: `✗ Unresolvable template variables '{var1}', '{var2}' in step '{step}' — check prompt template in config`
- **Exit code:** 2 (config validation failure, inherited from ConfigError handling in cli.py)

## Coding Conventions (from Stories 1.1-1.3)

- **Type annotations:** Full pyright strict mode compliance. Use `collections.abc.Mapping`, not `dict`, for read-only mappings
- **Pydantic patterns:** `ConfigDict(extra="forbid")`, `Field()` validators where applicable
- **Naming:** `snake_case` functions/vars, `PascalCase` classes, `UPPER_SNAKE_CASE` constants
- **Test naming:** `test_<unit>_<behavior>()` — e.g., `test_template_resolver_resolves_single_variable()`
- **Error format:** Always `✗ [What happened] — [What to do next]`
- **Imports:** Relative within package (`from .schema import ...`), absolute across packages (`from bmad_orch.types import ...`)
- **No bare except:** Always catch specific exception types
- **Logging:** Use `structlog` context binding (not f-strings) when adding logging

## Testing Standards

- **Framework:** pytest 9.x with pytest-cov
- **Test location:** `tests/test_config/test_template.py` (mirrors source structure)
- **Coverage target:** 100% on `config/template.py`
- **Fixture scope:** Function-scoped (default) for all new fixtures
- **Pattern:** Arrange (fixtures) → Act → Assert. No arrange in test body.
- **Error testing:** `pytest.raises(ConfigError) as excinfo:` then assert on `str(excinfo.value)`
- **Existing fixtures in `tests/conftest.py`:** `VALID_CONFIG_DATA`, `project_root`, `valid_config_file`

## Files to Create

| File | Purpose |
|------|---------|
| `src/bmad_orch/config/template.py` | `TemplateResolver` class with `resolve()` and `find_variables()` |
| `tests/test_config/test_template.py` | Comprehensive unit tests |

## Files to Modify

| File | Change |
|------|--------|
| `src/bmad_orch/config/__init__.py` | Add `TemplateResolver`, `resolve_step_prompts` to exports and `__all__` |

## Files NOT to Touch

- `config/schema.py` — No schema changes needed. `StepConfig.prompt` is already `str`
- `config/discovery.py` — Discovery/loading is separate from template resolution
- `cli.py` — Template resolution is called by engine at runtime, not by validate command (validate only checks schema, not runtime state)
- `errors.py` — `ConfigError` already exists with correct severity

## Previous Story Intelligence (from Story 1-3)

**Patterns to follow:**
- ATDD-first: Write failing tests, then implement to pass
- Separate unit tests from integration tests
- Use `tmp_path` and `monkeypatch` fixtures for isolation
- Assert exact error message text in exception tests
- 100% test coverage on new modules

**Patterns established in codebase:**
- `discover_config_path()`, `load_config_file()`, `get_config()` in `config/discovery.py`
- Pydantic V2 models with `ConfigDict(extra="forbid")` in `config/schema.py`
- `ConfigError` wrapping with formatted messages in `config/discovery.py`
- CLI error handling: `try/except BmadOrchError` → exit code 2

**Import pattern from `config/__init__.py`:**
```python
from bmad_orch.config.template import TemplateResolver, resolve_step_prompts
```

## Project Structure Notes

- Story 1.4 adds a new file (`template.py`) to the existing `config/` package — consistent with the established pattern of one-concern-per-file
- No new packages or directories needed
- Import linter layers already permit `config/` imports from `types` and `errors`
- No new dependencies required — uses only Python stdlib (`re` module) plus existing `bmad_orch.errors`

## References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic-1, Story 1.4, lines 377-403]
- [Source: _bmad-output/planning-artifacts/architecture.md — config/loader.py TemplateResolver note, line 566]
- [Source: _bmad-output/planning-artifacts/prd.md — FR9 template variable resolution]
- [Source: _bmad-output/planning-artifacts/prd.md — Config example with {next_story_id} and {current_story_file}, lines 190-230]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Error message format: "What happened — What to do next"]
- [Source: _bmad-output/implementation-artifacts/1-3-config-file-loading-discovery.md — Previous story patterns and learnings]
