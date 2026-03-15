# 2. What Went Well (Successes)

## Clean Architectural Split

The decision to build Story 2-1 as a pure framework story — establishing the PTY utility, exception hierarchy, and adapter registry — before building concrete adapters was highly effective. By the time Stories 2-2 and 2-3 were developed, the infrastructure was stable and adapters could focus entirely on provider-specific logic.

The provider subsystem has clean dependency isolation: `providers` never imports from `engine`, and the adapter ABC ensures new providers can be added by implementing a single contract.

## Adversarial Reviews on Story Specs

Running adversarial reviews on story specifications *before* development caught real issues early:

- **Story 2-1**: 10 spec issues found (ambiguous hierarchy, redundant ACs, competing implementation approaches)
- **Story 2-4**: 11 spec issues found (vague file paths, untestable ACs, hollow tasks, pre-filled-but-empty templates)

These were fixed before any code was written, preventing downstream rework. This practice should be continued and is one of the highest-value quality gates in the pipeline.

## Consistent Metadata Patterns

The `_get_base_metadata()` pattern established in Story 2-1's base class gave all adapters consistent metadata injection (`execution_id`, `model`, `provider`, `version`) with zero boilerplate duplication. This pattern matured across the epic — Story 2-2 initially missed merging adapter-specific metadata (caught in review), and by Story 2-3 it was well-established.

## Epic 1 Retro Action Items Honored

The team fully delivered on the most impactful Epic 1 action item: using `shutil.which()` and Python standard library primitives instead of shell commands. Every adapter's `detect()` method uses `shutil.which()`, the PTY utility uses `os.openpty()` and standard `asyncio` primitives, and the non-POSIX guard raises `NotImplementedError` explicitly.

## 100% Story Completion

All 4 stories reached `done` status with 100% test coverage on new code. The consistent artifact structure (story.md, dev-notes.md, dev-agent-record.md, acceptance-criteria.md, tasks-subtasks.md) matured during the epic, with Story 2-4 additionally producing adversarial reviews and a definition-of-done document.

## Registry Design

The singleton pattern in the adapter registry was a good design decision, with `clear_registry()` exposed as a public function specifically for test isolation via an `autouse` fixture in `conftest.py`. This clean test boundary enabled reliable, isolated test execution.
