### Verdict: FAIL

One blocking finding, under the brief's rule for absolute words: a late `run_pending()` executes a weekday job on Saturday/Sunday, and no recorded decision accepts that exception. Everything else — criteria, contracts, CI checks, docs — passes. If the main session records a decision accepting the library's standard catch-up semantics for missed runs, this becomes a PASS.

### Criteria
- **C1 PASS** — `test_weekday_next_run_from_every_day_of_week` covers all 7 start days; my check (script case C): Fri 08:59:59 → Fri 09:00 same day; Fri 09:00:00 exactly → Mon 09:00 (strictly after now).
- **C2 PASS** (with the tz consequence the decision accepts) — 8-week walk with `run_pending` every minute (case D): 40 runs, all Mon–Fri at 09:00, 40 expected. Fri run → next Mon 09:00; Sat/Sun now → Mon (cases A/B, tests `test_run_every_weekday_friday_to_monday`, `test_weekday_without_at_time`). Note: `at("06:00","Pacific/Auckland")` from local Fri 20:00 Berlin yields next_run local **Sun 18:00** (Mon 06:00 NZ) — that is the recorded "judge day in the at-tz" decision, not a defect. But see Finding 1 for the *scheduled-on-weekday, executed-on-weekend* case.
- **C3 PASS** — `every(2).weekday` → IntervalError; `.weekday.monday`, `.monday.weekday`, `.weekday.hours/.hour/.week/.seconds`, `.weekday.to(3)` and `every(1).to(2).weekday` → ScheduleValueError at `do()`; `schedule.jobs` stays empty (test `test_weekday_invalid_combinations` + case E).
- **C4 PASS** — `python3 -m pytest -q`: 49 passed, 44 skipped (baseline 40/41 + 9 new passing + 3 new tz tests skipped). `git diff BASE..HEAD -- test_schedule.py` has 0 removed lines; existing tests untouched.
- **C5 PASS** — venv (pytz): 93 passed; `black --check .`: 4 files unchanged; `mypy -p schedule`: no issues; `sphinx-build -W` (tox docs command) succeeds, `weekday` appears in reference.html and examples.html.
- **C6 PASS** — README.rst, docs/examples.rst, module docstring, HISTORY.rst updated. `repr` → `Every weekday at 09:00:00 do job_fun() (...)`; `str()` unchanged (`Job(interval=1, unit=days, ...)`).

### Test run
```
$ python3 -m pytest -q                       -> 49 passed, 44 skipped in 0.33s
$ /tmp/orch-weekday-venv/bin/python -m pytest -q -p no:cacheprovider -> 93 passed in 0.17s
$ black --check .                            -> All done! 4 files would be left unchanged.
$ python -m mypy -p schedule                 -> Success: no issues found in 1 source file
$ sphinx-build -W -b html . <scratch>        -> build succeeded.
```
Working tree clean before and after (`git status --short` empty).

### Findings

**Finding 1 — blocking (per the brief's "never" rule): a missed weekday run is executed on Saturday/Sunday.**
- Violates: request text "never on Saturday or Sunday"; no recorded decision covers missed/late runs.
- Location: `schedule/__init__.py:695` (`Job.should_run` is `now >= next_run` with no weekday check) / `:702` (`Job.run`); the weekend guard exists only in `_schedule_next_run` at `:774`.
- Reproduction (scratch script case A, `<scratchpad>/edge.py`): schedule `every().weekday.at("09:00")` at Fri 08:00; first `run_pending()` at Sat 10:00 → `call_count == 1`, `last_run == 2010-01-09 10:00`, `last_run.weekday() == 5`. The job ran on a Saturday. Same holds for a process that sleeps from Fri 08:59 and wakes at Sat 00:01.
- Impact: any scheduler downtime (or `run_pending` loop that stalls) spanning a Friday 09:00 causes a weekend execution — exactly what the request excludes. This is the library's general catch-up behaviour (`every().monday` behaves the same), which the brief says does not excuse it.
- Smallest correction, either of:
  1. Record a decision that missed weekday runs may execute late on the weekend (library-standard catch-up), and say so in the `weekday` docstring; or
  2. In `Job.run()` (line ~702), before calling `job_func`: `if self.weekdays_only and datetime.datetime.now(self.at_time_zone).weekday() >= 5: self._schedule_next_run(); return None` (skip the missed run and reschedule to Monday), plus a test mirroring case A. Note `run_all()` also goes through `run()`; if a forced run must still work on weekends, apply the guard in `Scheduler.run_pending`/`_run_job` instead.

### Not verified
- Sphinx was run with the venv's Sphinx version, not the pinned `requirements-dev.txt` via tox (network not used); the `-W` build did succeed.
- DST transitions at midnight on a weekday (e.g. historical Asia/Amman Friday 00:00 rules) with `at("23:xx", tz)` — reasoned from `_correct_utc_offset` that fixate-time keeps the day, but not executed; Berlin DST cases at 00:30/02:30 verified (case G, all land on Monday).

Scratch files kept: `<scratchpad>/edge.py` (edge-case script) and `<scratchpad>/docs-build/` (sphinx output).