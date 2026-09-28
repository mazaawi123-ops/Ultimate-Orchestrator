Perfect! Task completed successfully.

**STATUS:** DONE

**Commits:** b52ffd1

**Tests:** `python3 -m pytest -q` → 40 passed, 41 skipped

**Material assumptions:** none

**Remaining problems:** none

**Evidence:** 
- Function definition renamed at schedule/__init__.py:916 (`def _advance_to_weekday(...)`)
- Call site updated at schedule/__init__.py:724 (`_advance_to_weekday(next_run, self.start_day)`)
- All three test references updated in test_schedule.py:1254, 1261, 1268
- No remaining references to old name in tracked code
- All tests pass with expected results (40 passed, 41 skipped)