# Dev Notes

- **Lazy Imports:** `rich` and `libtmux` MUST be imported lazily at function-level in rendering modules. [Source: Architecture#Cross-Cutting Concerns]
- **Type Safety:** Use Pydantic V2 for all configuration and state models.
- **CLI Framework:** Typer with `rich` for formatting.
- **Python Version:** 3.13 is mandatory.

## Project Structure Notes

- Uses standard `src/` layout.
- Layered architecture enforced by `import-linter`.

## References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Starter Template Evaluation]
- [Source: _bmad-output/planning-artifacts/prd.md#Success Criteria]
