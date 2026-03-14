# Adversarial Review 2 — 2026-03-14 (Complete)

## Findings & Fixes Applied

1. **WEAK TEST ASSERTION (Fixed, MEDIUM)** — `test_provider_availability_atdd.py:test_ac1_error_includes_update_config_guidance` used a weak `"Missing" in msg` fallback instead of asserting the actual AC1 guidance string. Now asserts both `"Missing referenced provider"` and `"OR update your config to use an available provider"`.
2. **WEAK CLI TEST ASSERTIONS (Fixed, MEDIUM)** — `test_cli_provider_validation_atdd.py` had 3 assertions with `or` fallbacks (lines 117, 192, 209) that could mask real failures. Replaced with direct, specific assertions.
3. **UNUSED FIXTURE PARAMETERS (Fixed, MEDIUM)** — Removed unused `monkeypatch` parameter from 6 test functions in `test_cli_provider_validation_atdd.py`.
4. **FRAGILE MOCK PATCHING (Fixed, MEDIUM)** — `test_config_discovery.py` used class-level `MagicMock` patching on registry classes (`_registry["claude"].detect = MagicMock(...)`) which worked only because MagicMock ignores the implicit `self` argument. Replaced with proper adapter stubs (`_DetectedClaude`, `_UndetectedGemini`, `_ExplodingClaude`, etc.) matching the pattern used in the ATDD test files. Removed unused `pathlib` import.

**Outcome:** All 4 MEDIUM issues fixed. 23/23 tests passing. Story remains done.

