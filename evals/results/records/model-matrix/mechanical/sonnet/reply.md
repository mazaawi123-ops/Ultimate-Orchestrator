STATUS: DONE
Commits: b63cbaa
Tests: `python3 -m pytest -q` → 40 passed, 41 skipped (matches baseline)
Material assumptions: The old name also appeared as a substring inside three test method names (`test_move_to_next_weekday_*`). Interpreted "old name appears nowhere in the tracked files" strictly and renamed those method names to `test_advance_to_weekday_*` too, since this is a pure reference rename with no behavior/logic change (test bodies, assertions, and coverage untouched).
Remaining problems: none
Evidence: grep confirms `_move_to_next_weekday` is absent and `_advance_to_weekday` appears at all former sites (schedule/__init__.py:724,916; test_schedule.py:1252-1268); pytest output above.