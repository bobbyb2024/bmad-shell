# Dev Notes

## Architecture Guardrails

- **Layer:** `config` — only imports from `types` and `errors`.
- **Error Format:** Must follow `✗ [What happened] — [What to do next]`.
- **Exit Codes:** 0 (success), 1 (general error), 2 (config error).

## Configuration Discovery Order

1. Explicit `--config` (or `-c`) path.
2. `bmad-orch.yaml` in the current working directory.
