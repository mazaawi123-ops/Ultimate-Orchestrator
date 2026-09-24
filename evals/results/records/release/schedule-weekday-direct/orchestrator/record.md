# Run record: weekday

Route: Direct (user-specified; no delegation, no independent review).
Baseline (82a43db): `python3 -m pytest -q` → 40 passed, 41 skipped (all skips: "pytz unavailable").

## Acceptance criteria
1. `schedule.every().weekday.at("09:00").do(job)` is valid API and returns the Job.
2. From any start moment, next_run is the next Mon–Fri 09:00 strictly after now
   (Fri after 09:00 → Mon 09:00; Sat/Sun → Mon 09:00; Mon–Thu after 09:00 → next day).
3. Successive runs walk Mon, Tue, Wed, Thu, Fri, Mon … — never Sat or Sun.
4. The job function is never executed on a Saturday or Sunday, even when run_pending is
   called late (e.g. a Friday 23:59 run picked up on Saturday).
5. `every(2).weekday` raises IntervalError (like `every(2).day`); combining with a weekly
   unit (e.g. `.weekday.monday`) raises ScheduleValueError instead of silently mis-scheduling.
6. `.at(..., tz)` works: weekday is judged in the job's time zone.
7. Existing suite stays green; mypy, black (20.8b1), sphinx -W docs build pass.

## Decisions
- Decision: `weekday` is a property setting unit="days" plus a `weekdays_only` flag — reuses
  daily `.at()` validation and DST handling — cost if wrong: small refactor.
- Decision: weekend guard lives in `Job.run()`, so it also applies to `run_all()`: a
  weekday-only job skipped on a weekend is rescheduled, not executed — "never on Saturday
  or Sunday" read literally — cost if wrong: a user calling run_all() on a weekend expects
  the job to run; easy to relax.
- Decision: a missed run that would land on a weekend (late pickup) is skipped, not deferred
  to Monday — matches run_pending's documented "does not run missed jobs" — cost if wrong: low.
- Decision: `every().weekday.do(job)` without `.at()` is allowed: runs every 24h from
  scheduling time, skipping weekends — cost if wrong: low.
- Decision: the weekday is judged in the `.at()` time zone when one is given — cost if
  wrong: jobs near midnight across zones could land on a local weekend day.

## Evidence (candidate 9d8c02c)
- check: `python3 -m pytest -q` → 48 passed, 44 skipped (skips = pytz unavailable; +3 new tz tests, approved)
- pytz-tests: venv pytest with pytz → 92 passed, 0 skipped
- mypy (venv, with types-pytz) → clean; black 20.8b1 --check → clean; sphinx -W → clean
- fresh checkout → 48 passed, 44 skipped
- Criteria 1–7: met (tests test_weekday_*, test_run_every_weekday_at_specific_time, test_tz_weekday*)
- Note: system python mypy fails only for missing types-pytz stubs (pre-existing env gap; tox installs them).
