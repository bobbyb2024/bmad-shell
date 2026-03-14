# Next Steps (TDD Green Phase)

After confirming implementation is complete:

1. Remove `@pytest.mark.skip(reason="RED PHASE: ...")` from all 18 tests
2. Run: `uv run pytest tests/test_provider_availability_atdd.py tests/test_cli_provider_validation_atdd.py -v --no-cov`
3. Verify all 18 tests **PASS** (green phase)
4. If any tests fail:
   - Either fix implementation (feature bug)
   - Or fix test (test bug — assertion doesn't match actual behavior)
5. Commit passing tests
