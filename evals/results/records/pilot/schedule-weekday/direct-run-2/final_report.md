I've added `schedule.every().weekday`. `every().weekday.at("09:00").do(job)` now runs at 09:00 Monday to Friday and never at the weekend. The full suite passes: 89 of 89 tests with pytz available, and 47 passed with 42 skipped without it.

## Done: `every().weekday` schedules Monday to Friday only
- **Built:** `Job.weekday` in `schedule/__init__.py` makes the job a daily job that skips Saturday and Sunday. It uses the same `.at()`, timezone and daylight-saving handling as `every().day`. `repr` shows "Every 1 weekday …". I added one example line to `README.rst`, `docs/index.rst` and `docs/examples.rst`.
- **Criteria:** 6/6 met:
  - Runs at 09:00 on Monday to Friday. A test walks two weeks and gets exactly 10 runs, all on weekdays.
  - Scheduling after Friday 09:00, or at the weekend, gives Monday 09:00. After the Friday run it moves to Monday.
  - `every(2).weekday` raises `IntervalError`.
  - `.weekday.monday` and `.monday.weekday` raise `ScheduleValueError`.
  - With `.at(..., tz)`, the weekend is judged in that timezone.
  - The existing suite stays green.
- **Tests:** 8 new tests in `test_schedule.py`. When I disabled the weekend-skipping line, 4 of them failed, so they catch the bug.
- **Evidence:** on commit `ba8232a`:
  - `python3 -m pytest -q` as given: 47 passed, 42 skipped (`.orchestrator/logs/002-check.log`). The skips are because pytz isn't installed here.
  - With pytz: 89 passed, 0 skipped (`.orchestrator/logs/004-check.log`). pytz is listed in `requirements-dev.txt`, and I installed it into the scratchpad only, not system-wide.
  - The final gate passed.
- **Known failures:** none.
- **Test changes:** no existing tests were changed. The check helper flagged that the skip count rose from 41 to 42. That extra skip is the new timezone test, which, like the 41 existing timezone tests, skips without pytz. The helper has no way to approve that flag, so I re-checked the same commit with pytz available and got 0 skips. Both runs are on record.
- **Review:** not reviewed independently (Direct mode, as you asked).
- **Not verified:** none.
- **Decisions:**
  - Only an interval of 1 is allowed, because "every 2nd weekday" is ambiguous. `every(2).day` works the same way.
  - `every().weekday.do(job)` without `.at()` is allowed. It runs once per weekday at the time of day it was scheduled.
  - I left `HISTORY.rst` alone; the release notes are the maintainers' call.
- **Branch:** `orch/weekday` from `main` at `82a43db`, not pushed. To take it: `git merge orch/weekday`.
- **Route and models:** Direct; no subagents. The session cost about $0.90 (a local estimate, not a bill).

The notes and evidence are kept in `.orchestrator/`: `record.md` has the criteria and decisions, and `logs/` has the test output.