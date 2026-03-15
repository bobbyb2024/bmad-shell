# 4. Adaptations for Epic 3 (Action Items)

## Action Item 1: Full Test Suite Audit (BLOCKING)

**Priority**: Critical — Must be completed before Story 3-6 begins

Run the complete test suite across all Epics (1, 2, and 3 stories completed so far). Fix any failures discovered. Document findings to understand the scope of the pytest-not-installed gap.

**Why**: pytest was not installed during development, meaning tests were written but never executed. Latent failures may exist in foundation code that Epic 3 builds upon. Running blind means we may have passing-on-paper tests that actually fail.

**How to apply**: Before starting Story 3-6, run `pytest` across the full codebase. Any failures found should be triaged and fixed. Results should be documented to establish a clean baseline.

**Owner**: Dev team
**Status**: Not started

## Action Item 2: Dev Environment Pre-Flight Check

**Priority**: High — Process improvement for all future stories

Before any story implementation begins, the dev agent must verify:
1. `pytest` is installed and functional
2. The existing test suite passes (no pre-existing failures)
3. Required development dependencies are available

This check should be built into the dev-story workflow as a mandatory first step.

**Why**: The biggest friction point in Epic 2 was pytest not being available. Tests written without being run led to broken imports, type errors, and inflated review rounds. A pre-flight check would have caught this immediately.

**How to apply**: Add a pre-flight verification step to the dev-story workflow template. The step should run `pytest --co` (collect only) to verify the test runner works and tests are discoverable, then run the full suite to confirm a green baseline before writing new code.

**Owner**: Process improvement
**Status**: Not started

## Action Item 3: Standardize Defensive Parsing

**Priority**: Medium — Technical alignment

Align Claude and Gemini adapters on a consistent defensive parsing strategy:
- Same window size for initial output checking
- Same set of error patterns checked (HTML errors, binary data, proxy errors, permission errors)
- Document the parsing contract in the base adapter class

**Why**: Claude adapter checks first 1KB; Gemini checks first 2KB plus continuous monitoring. This inconsistency could cause different failure behaviors for the same corrupted output, making debugging harder and reducing confidence in the provider abstraction.

**How to apply**: During next available story or tech debt sprint, refactor defensive parsing into the base adapter class with configurable parameters. Both adapters should use the same detection logic.

**Owner**: Next available story or tech debt sprint
**Status**: Not started

## Action Item 4: Address Retry Logic Asymmetry

**Priority**: Medium — Architectural consistency

Either add retry with exponential backoff to the Claude adapter, or extract retry logic from the Gemini adapter into a base-class concern that all adapters inherit.

**Why**: Currently only the Gemini adapter retries on transient failures. If Claude CLI experiences transient issues, it will crash rather than retry. Before multi-cycle orchestration (Story 3-6), this asymmetry should be resolved to ensure consistent resilience behavior across providers.

**How to apply**: Evaluate whether retry belongs in the base class (preferred for consistency) or remains provider-specific. If base class, extract from Gemini adapter and make configurable. If provider-specific, add equivalent logic to Claude adapter.

**Owner**: Next available story or tech debt sprint
**Status**: Not started

## Technical Debt Tracker

| Item | Severity | Source Story | Notes |
|------|----------|-------------|-------|
| `list_models()` partially implemented in Claude adapter | Medium | 2-2 | Only fallback list exists; primary CLI command invocation missing |
| Retry logic only in Gemini adapter | Medium | 2-3 | See Action Item 4 |
| Registry uses internal `_registry` dict | Low | 2-4 | Should be promoted to public API as provider subsystem stabilizes |
| Grace period conversion safety | Low | 2-2 | Non-numeric env var values not handled safely |
| No integration tests with real CLI binaries | Low | All | By design (CI environments), but represents a testing gap |
| Defensive parsing inconsistency | Medium | 2-2, 2-3 | See Action Item 3 |
