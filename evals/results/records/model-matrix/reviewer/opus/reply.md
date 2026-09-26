### Verdict: FAIL

The candidate works whenever the scheduler loop is running at 09:00. The request says the job must "never" run on Saturday or Sunday, and that fails in one case: a missed Friday run fires on Saturday.

### Criteria
- **C1 PASS.** I ran `test_weekday_next_run_from_every_day_of_week`, the two-week hourly walk and my own script. `next_run` is the next Mon–Fri 09:00 strictly after now: same day when before 09:00, next weekday at exactly 09:00.
- **C2 FAIL.** The computed `next_run` is never a Saturday or Sunday, from any starting day or after repeated runs (Fri→Mon, Sat/Sun→Mon). But the job can still *run* on a weekend: see finding 1.
- **C3 PASS.** `every(2).weekday` raises IntervalError. `.weekday.monday`, `.monday.weekday` and `.weekday.hours/.weeks` raise ScheduleValueError. `.weekday.to(n)` raises ScheduleValueError. No job is left registered after any of these errors.
- **C4 PASS.** The system python gives 49 passed, 44 skipped (baseline 40 passed / 41 skipped, plus 9 new tests of which 3 skip without pytz). The diff only adds to `test_schedule.py`; no existing test or config was edited.
- **C5 PASS.** In the venv with pytz: 93 passed. `black --check .` reports "4 files would be left unchanged". `mypy -p schedule` reports "no issues found in 1 source file". The Sphinx `-W` html build finished with no warnings.
- **C6 PASS.** README, `docs/examples.rst` and HISTORY mention the new API. repr is `Every weekday at 09:00:00 do job() (last run: [never], next run: …)`. `__str__` is unchanged (`Job(interval=1, unit=days, …)`).

### Test run
```
system python:  49 passed, 44 skipped in 0.35s
venv (pytz):    93 passed in 0.14s
black:          All done! ✨ 🍰 ✨  4 files would be left unchanged.
mypy:           Success: no issues found in 1 source file
sphinx -W:      no output (no warnings)
```

### Findings

**1. Blocking: a missed Friday run fires on Saturday**
- **Violates:** the request's "never on Saturday or Sunday" (C2). No recorded decision accepts a late weekend run. The only accepted weekend exception is the cross-timezone one.
- **Location:** `schedule/__init__.py:695–700` (`should_run` is `now >= next_run`) together with `Job.run` at 702ff. The weekend skip at `schedule/__init__.py:774–777` only affects how `next_run` is computed, not whether a run is allowed now.
- **Reproduction:** `/tmp/wk_repro.py`, run with `PYTHONPATH=.`:
  - Schedule `every().weekday.at("09:00")` on Fri 2010-01-08 at 08:00, so `next_run` is Fri 09:00.
  - Nothing calls `run_pending` until Sat 2010-01-09 10:00 (machine asleep, loop blocked by a long job, process paused).
  - Output: `calls [(MockDate(2010, 1, 9, 10, 0), 'Saturday')] next 2010-01-11 09:00:00`. The job ran on a Saturday.
  - The same happens for any overdue Friday run first checked on Sat/Sun.
- **Impact:** weekday-only jobs (for example business-hours reports or trading tasks) can run on a weekend after a laptop wakes up or after a stall. The new tests miss this because they always call `run_pending` on time.
- **Smallest correction:** in `Job.should_run`, when `weekdays_only` is set, don't run if today is Saturday or Sunday. Judge the day in `at_time_zone` when one is set, to stay consistent with the timezone decision. Then reschedule the overdue job to the next weekday instead of leaving it pending; the simplest way is to call `self._schedule_next_run()` and return False. Add a test for "Fri run missed, first check Sat 10:00 → no call, `next_run` Mon 09:00".
  - If the main session would rather keep "a late run fires when noticed" (as `every().day` does), that is a user-facing exception to "never". It should be recorded as a decision and documented, not left implicit.

**2. Observation: `run_all()` runs weekday jobs on weekends**
- **Location:** `Scheduler.run_all`.
- **Evidence:** `run_all()` called on Sunday ran the job (same script, `run_all Sunday calls [... 'Sunday']`).
- **Impact:** low. `run_all` is an explicit "run everything now" call and ignores all schedules by design, so I'd leave it. It's worth a sentence in the `weekday` docstring if finding 1 is fixed.

**3. Observation: misleading error message for `every(0).weekday`**
- **Location:** `schedule/__init__.py` (the new `weekday` property).
- **Evidence:** `every(0).weekday` raises IntervalError with the message "…every 2 or more days is not supported", which doesn't describe interval 0.
- **Impact:** cosmetic; the exception type is correct.

### Not verified
- Python versions other than the system python and the venv's; CI covers 3.7–3.12.
- The tox/GitHub Actions configuration itself; the patch doesn't touch those files, so I didn't run them.

My scratch files are `/tmp/wk_repro.py` and `/tmp/wk_docs_out`. The working tree is clean.