STATUS: DONE_WITH_CONCERNS
Commits: b79d0c3 (branch orch-wt/rename) — schedule/__init__.py, test_schedule.py
Tests: `python3 -m pytest -q` → 40 passed, 41 skipped (identical to BASE)
Material assumptions: The three test method names (`test_move_to_next_weekday_today/_tommorrow/_nextweek`) contain the old name as a substring, so "old name appears nowhere" and "no other names change" conflicted. I renamed them to `test_advance_to_weekday_*` so `git grep move_to_next_weekday` returns nothing; the test bodies and assertions are untouched. If the main session prefers the method names left alone, revert the 3 `def` lines in test_schedule.py (lines 1252/1259/1266).
Remaining problems: none. Definition (line 916), the one call site (line 724) and all 3 test call sites now use `_advance_to_weekday`; `git grep` for the old name is empty; no public names changed.
Evidence: `git show b79d0c3` (8 insertions/8 deletions across 2 files); pytest output above from the worktree.