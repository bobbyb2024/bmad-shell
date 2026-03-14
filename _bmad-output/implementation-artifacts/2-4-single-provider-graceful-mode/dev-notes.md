# Dev Notes

- **Provider Registry:** Use the `ProviderAdapter.detect()` method from each registered adapter. Each adapter now exposes an `install_hint` class attribute (e.g., `"npm install -g @google/gemini-cli"`) used by AC4 error output.
- **Error Format (AC1):** `"✗ Missing referenced provider(s):\n  - {name}: {install_hint}\nOR update your config to use an available provider."`

## Project Structure Notes

- Update: `src/bmad_orch/config/discovery.py` — added `validate_provider_availability()`.
- Update: `src/bmad_orch/cli.py` — call validation during `validate` and `start` commands.
- Update: `src/bmad_orch/providers/base.py`, `claude.py`, `gemini.py` — added `install_hint`.
- Create: `tests/test_config_discovery.py` — discovery and validation tests.

## Dependencies

- **Story 2.2** (Claude CLI Adapter) — provides `ClaudeAdapter.detect()`.
- **Story 2.3** (Gemini CLI Adapter) — provides `GeminiAdapter.detect()`.

## References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic-2, Story 2.4]
- [Source: _bmad-output/planning-artifacts/prd.md — FR14]
