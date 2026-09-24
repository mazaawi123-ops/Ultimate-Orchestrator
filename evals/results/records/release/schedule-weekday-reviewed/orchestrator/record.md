# weekday

## Request
See .orchestrator/request.md (verbatim). Add `every().weekday` so a job runs Mon–Fri only (e.g. `.at("09:00")`), never Sat/Sun.

## Done means
- C1: `schedule.every().weekday.at("09:00").do(job)` computes next_run as the next Mon–Fri 09:00 strictly after now (same day if before 09:00 on a weekday).
- C2: next_run is never a Saturday or Sunday — from any starting day of the week, and across repeated runs (Fri run -> next Mon; Sat/Sun now -> Mon).
- C3: invalid combinations fail loudly with a ScheduleError subclass instead of silently doing something else: `every(2).weekday` (IntervalError), `.weekday` combined with `.monday`..`.sunday`, with a non-day unit, or with `.to()`.
- C4: Existing tests unchanged and green: `python3 -m pytest -q` (baseline 40 passed / 41 skipped — pytz unavailable locally).
- C5: CI checks pass on candidate: black==20.8b1 `black --check .`, `mypy -p schedule`, and the full suite with pytz installed (the tox matrix's pytz leg), in a throwaway venv.
- C6: Docs mention the new API (README + docs/examples.rst); repr of a weekday job reads sensibly.

## Baseline
- BASE 82a43db, branch orch/weekday; test command: python3 -m pytest -q
- Known failures at BASE: none (41 skipped: pytz unavailable)

## Contracts to preserve
- Builder-pattern properties on Job (schedule/__init__.py); `unit` values validated in `_schedule_next_run`; `__str__` format; existing repr outputs for non-weekday jobs; naive local next_run.

## Route
- Builders: me · Review: independent (user asked for Reviewed mode)
- Requirements set: review; checks black, mypy, pytz-tests

## Decisions
- Decision: implement as `unit="days"` plus a `weekdays_only` flag, skipping forward past Sat/Sun after the normal daily computation — reuses the daily at()/tz/DST logic — cost if wrong: small refactor.
- Decision: with `at(..., tz)`, "weekday" is judged in that timezone (the one the at-time is expressed in), not the machine's local zone — consistent with how the at-time itself is interpreted — cost if wrong: in cross-zone setups the machine-local calendar day of a run can be Sat/Sun (e.g. Fri 20:00 New York is Sat 02:00 Berlin; covered by test_tz_weekday_judged_in_given_timezone). Documented in the property docstring.
- Decision: `every().weekday.do(job)` without at() is allowed: runs once per weekday at the time-of-day of scheduling, like `every().day` — cost if wrong: low.
- Decision: reject `every(n>1).weekday`, `.to()` with weekday, weekday combined with a weekday-name or non-days unit — no clear meaning; clear error preferred over guessing — cost if wrong: users wanting those must ask.
- Decision: repr shows "Every weekday at 09:00:00 do ..."; `__str__` unchanged in format (unit=days).

## Work
- implement + tests + docs: me — done — f142db5
- check f142db5: 49 passed / 44 skipped (system python); +3 skips approved (new pytz tests)
- runs on f142db5: black 20.8b1 pass, mypy pass, pytz-tests 93 passed, docs (sphinx -W) pass, fresh pass
- mutation sanity: weekend skip disabled -> 9 new tests fail
- independent review (orch-verifier) on f142db5: PASS, C1–C6 pass
- repair cycle 1 -> 156c94e: check 49 passed / 45 skipped (+4 skips approved), black/mypy/pytz-tests (94 passed)/docs/fresh pass
- targeted re-check (orch-rechecker) on 156c94e: PASS — F1, F2 addressed; ~155k DST cases, 0 weekend runs

## Findings and repairs
- F1 optional: tz job created on a spring-forward Sunday with at-time in the gap ran 1h late on Monday (03:30 instead of 02:30) — reviewer brute force: 1,976/141,974 cases — fixed in 156c94e (re-apply at-time after the weekend skip), test_tz_weekday_dst_gap_on_sunday
- F2 observation: every().hour.weekday etc. accepted silently (only .weekday.hour raised) — fixed in 156c94e (weekday rejects a prior non-day unit or named day), covered in test_weekday_invalid_combinations
- F3 observation: an overdue job (run_pending not called on time, e.g. machine asleep) runs at the next run_pending call, which may be on a weekend; same as every existing job type (should_run is now >= next_run) — left, disclosed as a known limit
- F4 observation: inherited daily DST quirk at BASE (every().day.at("02:30","Europe/Berlin") created Sun after the gap -> Mon 01:30) — pre-existing, out of scope, left
- Repair cycles used: 1 of 2

## Status
Done — see final report; known limits F3, F4 disclosed
