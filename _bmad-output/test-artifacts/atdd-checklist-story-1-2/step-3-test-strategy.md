# Step 3: Test Strategy

## AC → Test Scenario Mapping

| AC | Scenario | Level | Priority |
|---|---|---|---|
| AC1 | Valid complete YAML → OrchestratorConfig with all typed sub-models | Unit | P0 |
| AC2 | Missing required section → ConfigError with field name (×3 sections) | Unit | P0 |
| AC3 | Invalid enum value → ConfigError with field, value, valid options (×2 enums) | Unit | P0/P1 |
| AC4 | StepConfig enforces typed fields + rejects wrong types | Unit | P1 |
| AC5 | CycleConfig validates steps, repeat, optional pauses (×4 scenarios) | Unit | P1/P2 |
| AC6 | Cross-field validation, validate_config wrapper, extra keys (×5 scenarios) | Unit | P0/P1 |
| Edge | Numeric boundary validation (max_retries, pauses, empty strings) (×6 scenarios) | Unit | P2 |

- **All Unit level** — pure Pydantic model validation, no I/O
- **P0:** 6 tests | **P1:** 7 tests | **P2:** 5 tests + 5 edge = 10 tests
- **Red phase guaranteed:** `schema.py` does not exist
