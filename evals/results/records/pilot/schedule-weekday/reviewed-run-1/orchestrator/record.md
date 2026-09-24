# weekday

## Request
See .orchestrator/request.md (verbatim). Add `every().weekday` so a job runs Mon–Fri only (e.g. at 09:00), never Sat/Sun.

## Done means
- C1: `schedule.every().weekday.at("09:00").do(job)` is accepted; next_run is 09:00 on the next Mon–Fri day strictly after now.
- C2: Scheduled Friday (or created on Sat/Sun) -> next run is Monday 09:00; job never runs Sat/Sun (run_pending simulation over a full week+ runs exactly on Mon–Fri).
- C3: Mon–Thu after a run -> next run is the following day at 09:00; same day if created before 09:00 on a weekday.
- C4: `every(2).weekday` raises IntervalError (mirrors `.day`); `.at()` validates HH:MM(:SS) like daily jobs.
- C5: Existing suite stays green: `python3 -m pytest -q` (baseline 40 passed, 41 skipped).
- C6: With a timezone (`.at("09:00", "America/New_York")`), weekday is judged in that timezone. (Tested only if pytz available — it is NOT installed here, so these tests skip like the existing tz tests.)

## Baseline
- BASE 82a43db, branch orch/weekday; test command: python3 -m pytest -q
- Known failures at BASE: none. 41 tests skip because pytz is not installed (pre-existing; installing it would be a global install -> not done).

## Contracts to preserve
- Builder API in schedule/__init__.py: unit properties, `.at()` validation per unit, `_schedule_next_run` DST handling, naive local next_run.
- Existing `.monday`..`.sunday` (weekly, start_day) semantics unchanged.

## Route
- Builders: me · Review: independent (user asked for Reviewed mode)
- Requirements set: orch.sh require review

## Decisions
- Decision: implement as unit "days" plus a `weekdays_only` flag; after computing the normal next daily run, advance by whole days past Sat/Sun — reuses all existing at()/tz/DST logic — cost if wrong: small refactor.
- Decision: `every(n).weekday` with n != 1 raises IntervalError (like `.day`); "every N weekdays" semantics are ambiguous — cost if wrong: users wanting it get a clear error.
- Decision: `every().weekday` without `.at()` behaves like `every().day` (runs 24h after now) but skips weekends — consistent with `.day`.
- Decision: weekend determined in the job's at() timezone when given (that's the zone the time is expressed in) — cost if wrong: edge-case around midnight across zones.
- Decision: combining weekday with `.monday`..`.sunday` or non-day units raises ScheduleValueError at do() rather than silently doing something odd.
- Decision: pytz (declared in requirements-dev.txt, not installed system-wide) installed only into a throwaway venv in the session scratchpad (--system-site-packages), not globally and not in the repo — so the 41 existing + 1 new timezone tests actually run — cost if wrong: none to the repo.
- Decision: candidate `check` uses the scratch venv's python (88 run, 0 skipped). With the user's exact command the new tz test skips like the 41 existing ones, and the helper's skip-count flag cannot be approved; the user's exact command is recorded separately as `run user-command-no-pytz` (46 passed, 42 skipped, 0 failed).
- Decision: repr shows "Every 1 weekday at 09:00:00 ..."; `str()` keeps unit=days.

## Work
- implementation + tests + docs (README, docs/examples.rst): me — done — 2431f44
- mutation checks: removing the weekend skip -> 6 tests fail; judging weekend in local time instead of job tz -> 1 test fails. Both killed.
- black not installed; lines kept <= 88 chars by hand. HISTORY.rst not touched (no unreleased section; maintainers add entries at release).

## Findings and repairs
- Repair cycles used: 0 of 2

## Status
In progress
