# weekday

## Request
See .orchestrator/request.md (verbatim). In my own words: add `every().weekday` so a job runs Monday to Friday (e.g. at 09:00) and never on Saturday or Sunday; add tests; keep the suite green.

## Done means
- C1: `schedule.every().weekday.at("09:00").do(job)` computes next_run as the next Mon–Fri at 09:00 from any starting day/time (test_weekday_next_run).
- C2: Polling run_pending every 15 min for 3 weeks runs the job exactly once per weekday at 09:00 and never on Sat/Sun (test_weekday_runs_monday_to_friday_only).
- C3: A late run whose moment falls on a weekend (Friday's run first picked up on Saturday) does not execute on the weekend and is rescheduled to Monday (test_weekday_late_run_is_not_run_on_weekend). A late run on a weekday still executes (test_weekday_late_run_on_weekday_still_runs).
- C4: Invalid combinations give a clear error, and no job is added: every(2).weekday (IntervalError); .weekday with .monday etc., .hours, .to() (ScheduleValueError); bad at() formats (test_weekday_invalid_combinations).
- C5: repr reads "Every weekday at 09:00:00 do ..." (test_weekday_repr).
- C6: Existing suite unchanged and green: `python3 -m pytest -q`.
- C7: With a timezone (`.at("09:00", "Pacific/Auckland")`), weekends are judged in that timezone (test_tz_weekday; skipped here without pytz, run in a scratchpad venv with pytz).

## Baseline
- BASE 82a43db, branch orch/weekday; test command: python3 -m pytest -q
- Known failures at BASE: none. 41 tests skip because pytz isn't installed in the system Python (pre-existing environment issue).

## Contracts to preserve
- Existing units/day properties, at() validation, run_pending/run_all/until semantics (schedule/__init__.py).
- Job.__str__ format (unchanged; weekday jobs show unit=days).

## Route
- Builders: me · Review: independent (the user asked for Reviewed mode)
- Requirements set: orch.sh require review

## Decisions
- Decision: `.weekday` is a property (like `.monday`) that sets `weekdays_only=True` and unit `days`; interval must be 1 — mirrors existing API — low cost if wrong.
- Decision: a missed run that is first picked up on a Sat/Sun is skipped (not run late) and rescheduled to Monday; this also applies to `run_all()` on a weekend — "never on Saturday or Sunday" read strictly — cost if wrong: a user expecting catch-up on the weekend loses Friday's missed run.
- Decision: `every().weekday.do(job)` without `.at()` runs each weekday at the time of scheduling, like `every().day` — cost if wrong: low.
- Decision: combining `.weekday` with a named day, a non-day unit, or `.to()` raises ScheduleValueError instead of guessing — could be relaxed later.
- Decision: with `tz`, Mon–Fri is judged in the at() timezone (where all scheduling maths already happens).
- Decision: added the example line to README.rst, docs/index.rst, docs/examples.rst; no HISTORY entry (releases write it).

## Work
- implementation + tests + docs: me — done — commits on orch/weekday

## Findings and repairs
- Review (orch-verifier) on d6a8046: PASS, C1–C7 pass. Optional findings:
  - black 20.8b1 `--check .` (CI format job) failed on 2 files — fixed in 8e0fcec (black-check run passes)
  - weekend-skip path ignored until() deadline — fixed in 8e0fcec + test_weekday_until_after_weekend_skip (mutation-checked)
  - `.weekday.hours` error message didn't mention .weekday — fixed in 8e0fcec
  - observation left as-is: a Friday run first polled Monday 08:00 runs late then and again at 09:00 — same as existing every().day catch-up semantics
- Recheck (orch-rechecker) on 8e0fcec: PASS, all three addressed.
- Repair cycles used: 1 of 2

## Status
Partial (by the helper gate only) — all criteria met and reviewed. The gate refuses "done" solely because the skipped-test count rose 41→42: the new test_tz_weekday skips without pytz like the 41 existing tz tests (passes with pytz: 93 passed). The helper has no way to approve a count flag, and removing or hiding the test to satisfy it would be gaming.
