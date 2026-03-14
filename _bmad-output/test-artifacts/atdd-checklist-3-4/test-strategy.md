# Test Strategy

| AC | Priority | Level | Test Count | Description |
|----|----------|-------|------------|-------------|
| AC1 | P0 | Unit | 1 | Ordered step execution |
| AC2 | P0 | Unit | 2 | Step type logic (first rep both, subsequent skip generative) |
| AC3 | P0 | Unit | 3 | Cycle repetition (N iterations, repeat=0, repeat=-1) |
| AC4 | P1 | Unit | 1 | Step pauses (between steps, not after last) |
| AC5 | P1 | Unit | 1 | Cycle pauses (between reps, not after last) |
| AC6 | P0 | Unit | 4 | Event emission (CycleStarted, StepStarted/Completed, CycleCompleted, ErrorOccurred) |
| AC7 | P0 | Unit | 2 | Atomic state persistence (record_step + save, UTC timestamp) |
| AC8 | P1 | Unit | 2 | Prompt resolution (TemplateResolver called, ConfigError handled) |
| AC9 | P1 | Unit | 2 | Logging context (bind_contextvars, clear in finally) |
| AC10 | P0 | Unit | 2 | Step failure handling (ErrorOccurred, CycleCompleted(false), failure outcome) |
| AC11 | P1 | Unit | 2 | Empty/no-op cycle (zero steps, generative-only repeat>1) |
| AC12 | P0 | Unit | 2 | Provider validation (missing key, empty name) |

**Total: 24 tests** | P0: 16 | P1: 8
