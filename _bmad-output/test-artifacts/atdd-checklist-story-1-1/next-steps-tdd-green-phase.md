# Next Steps (TDD Green Phase)

After implementing Story 1.1:

1. Remove `@pytest.mark.skip(reason="TDD red phase - not yet implemented")` from all test files.
2. Run tests: `uv run pytest`.
3. Verify tests PASS (green phase).
4. If any tests fail:
   - Either fix implementation (feature bug)
   - Or fix test (test bug)
5. Commit passing tests.
