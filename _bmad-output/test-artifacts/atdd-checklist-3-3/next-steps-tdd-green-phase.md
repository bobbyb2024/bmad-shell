# Next Steps (TDD Green Phase)

After implementing `src/bmad_orch/logging.py`:

1. Remove `pytest.mark.skip` from each test class as its AC is implemented
2. Run tests: `pytest tests/test_logging.py -v`
3. Verify tests PASS (green phase)
4. If any tests fail:
   - Fix implementation (feature bug) OR
   - Fix test (test bug — update helper capture functions)
5. Commit passing tests
