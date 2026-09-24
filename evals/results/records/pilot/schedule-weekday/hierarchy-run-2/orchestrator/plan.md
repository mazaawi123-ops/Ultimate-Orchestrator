# Goal
Add `Job.weekday` so `schedule.every().weekday.at("09:00").do(job)` runs Mon–Fri at 09:00 and never Sat/Sun. Tests added; full suite green.

# Baseline
- branch: orch/weekday from main (clean). BASE: 82a43db1b938d8fdf60103bd41f329e06c8d3651
- tests at BASE: `python3 -m pytest -q` → 40 passed, 41 skipped (pytz unavailable); pre-existing failures: none
- lint: none configured locally (mypy not installed; CI runs mypy via tox) 
- clean-room: n/a (no external services)
- estimate given: ~$2–3 (Opus planner, 1 Haiku worker, 1 Opus verifier)

# Acceptance criteria
- AC1: `every().weekday.at("09:00").do(job)` next_run: Mon 2024-09-23 08:00 → 09-23 09:00; Mon 09:30 → Tue 09-24 09:00; Fri 09-27 08:00 → 09-27 09:00; Fri 09:00 exactly → Mon 09-30 09:00; Fri 09:30 → Mon 09-30; Sat 09-28 08:00 → Mon 09-30 09:00; Sun 09-29 23:59 → Mon 09-30 09:00
- AC2: driving run_pending over a week from Mon 09-23 08:00 runs the job on 23,24,25,26,27 then 30 (all 09:00); never Sat/Sun
- AC3: `every().weekday.do(job)` (no at) at Fri 09-27 14:00 → Mon 09-30 14:00; Wed 09-25 14:00 → Thu 09-26 14:00
- AC4: `every(2).weekday` raises IntervalError; `every().weekday.hours.do(j)`, `every().monday.weekday.do(j)`, `every().weekday.monday.do(j)` raise ScheduleValueError
- AC5: repr starts "Every 1 weekday at 09:00:00 do job()"; `at("09:00:30")` → 09:00:30
- AC6: `python3 -m pytest -q` passes; no existing test modified

# Stop-and-ask items
- none (installing pytz/mypy would be outside repo → not done; tz path judged by reading + verifier)

# Review focus
- weekday judged in job's timezone when at(..., tz) is used (date differs between tz and local); DST fixation after skipping weekend days
- exact-boundary now == at time on Friday; `until()` cancel_after interplay; interval/latest (`to()`) combinations; chaining other units after `.weekday`; repr/str

# Rulings
- Ruling: implement as flag `weekdays_only` + unit "days", skip Sat/Sun after the normal day computation — minimal, reuses days/at/tz logic — cost if wrong: small refactor
- Ruling: `.weekday` only with interval 1 (IntervalError otherwise), like `.monday` — "every 2 weekdays" is ambiguous — cost if wrong: feature request later
- Ruling: combining `.weekday` with another unit or a named day fails loudly with ScheduleValueError at scheduling time — silent override would run on weekends — cost if wrong: none realistic
- Ruling: weekday determined in the at() timezone when given (that's where "09:00" lives) — cost if wrong: a job near midnight could run on local Sat
- Ruling: `.weekday` without `.at()` runs at the current time of day on the next weekday, same as `every().day` — consistent with day semantics
- Ruling: `every().weekday.to(n)` — randomised intervals on weekdays are not rejected; interval must be 1 anyway, and `latest` just adds days then weekend-skip. Accept.
- Ruling: no pytz install; tz tests (if any) use existing `@skip_if_no_pytz`-style pattern
- Ruling: add example line to docs/examples.rst; no HISTORY entry (maintainer curates releases)

# Tasks
## T1 weekday scheduling — tier: haiku — sequential — AC1–AC6
- Files: schedule/__init__.py, test_schedule.py, docs/examples.rst
- Interfaces: Produces `Job.weekday` property; attribute `Job.weekdays_only: bool`
- Tests allowed to change: none (add only)
- Status: pending

# Log
- T1 DONE (e44795b), haiku; 47 passed 41 skipped
- verify 1 (opus): PASS 6/6. should-fix: black line 305; unit set BEFORE .weekday (every().hour.weekday) silently accepted. nit: no tz/DST test. Declined: late overdue Fri run fires Sat (library-wide overdue behaviour); DST gap crossing midnight Fri→Sat (no real zone found).
- Ruling: fix both should-fix + add pytz-gated tz test in one Sonnet round — cheap.
- Ruling: overdue Friday run executing on Saturday is left as library behaviour (same as every().monday) — open item for user.
- fix 1 (sonnet) 5d9f00e: black ok, 49p/43s system, 92p venv; mypy unrunnable in venv per worker
- recheck 1 (sonnet): PASS, all 3 findings ADDRESSED; mypy clean in fresh venv2; black clean. DONE.
