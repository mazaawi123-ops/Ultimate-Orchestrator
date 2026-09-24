# weekday

## Request
See .orchestrator/request.md (verbatim). Add `every().weekday` so a job runs Mon–Fri (at the
given time) and never on Saturday or Sunday.

## Done means
- C1: `every().weekday.at("09:00").do(job)` computes next_run on the next Mon–Fri at 09:00:
  from Fri after 09:00 → Mon 09:00; from Sat/Sun any time → Mon 09:00; from Mon–Thu after
  09:00 → next day 09:00; before 09:00 on a weekday → same day. (tests)
- C2: Driving `run_pending()` across a whole week (hour by hour) calls the job exactly
  5 times, once each Mon–Fri at 09:00, zero calls on Sat/Sun. (test)
- C3: "never on Sat/Sun" holds for an overdue run: if run_pending() is first called on a
  weekend with a Friday next_run still pending, the job is not run; it is rescheduled to
  Monday. (test)
- C4: With a timezone (`at("09:00", "America/New_York")`), weekday/weekend is judged in that
  timezone. (test; needs pytz → checked in a pytz-enabled venv, tox's `-pytz` env)
- C5: Misuse errors clearly: `every(2).weekday` → IntervalError; `every().weekday.monday`,
  `every().monday.weekday`, `every().weekday.hours` → ScheduleValueError. (tests)
- C6: `every().weekday.do(job)` without at() also never lands on a weekend. (test)
- C7: Existing suite green: `python3 -m pytest -q` (plus pytz env); mypy -p schedule; black
  --check (black 20.8b1 as pinned); docs build if feasible.

## Baseline
- BASE 82a43db, branch orch/weekday; `python3 -m pytest -q` → 40 passed, 41 skipped (pytz
  unavailable). Known failures: none.

## Contracts to preserve
- Existing units/day properties, at() validation, repr/str formats for existing jobs,
  run_all() "runs all jobs regardless of schedule".

## Route
- Builders: me · Review: checks only (Direct, as the user instructed)

## Decisions
- Decision: `weekday` is a property like `day` (unit "days" + a `weekdays_only` flag), interval
  must be 1 — mirrors `.day`/`.monday` API — cost if wrong: small API tweak.
- Decision: weekend is judged in the job's timezone (tz passed to at(), else local) — the
  09:00 is in that tz so its day should be too — cost if wrong: in cross-tz setups the local
  weekday of a run may be Sat/Sun (e.g. Mon 09:00 Auckland = Sun evening Berlin).
- Decision: an overdue run found on a weekend by run_pending() is skipped and rescheduled
  (literal "never") — cost if wrong: a Friday run missed because the process was asleep is
  dropped instead of run late on Saturday.
- Decision: run_all() still runs weekday jobs on weekends — it is documented as "regardless if
  they are scheduled to run or not", an explicit manual trigger — cost if wrong: user expects
  run_all to also respect weekend exclusion.
- Decision: incompatible combos (weekday + named day, weekday + non-day unit) raise
  ScheduleValueError at do() time instead of silently picking one.

## Work
- Implementation, tests, docs: me — done — candidate f0de7e0

## Findings and repairs
- black 20.8b1 wanted one line joined in should_run — fixed before commit.
- Mutation check (scratch copy): removing the next_run weekend skip → 9 weekday tests fail;
  removing the should_run weekend guard → 2 fail. Both guards are covered.
- Observation, left: in a timezone with a DST gap at 23:xx, the "shift 1h later" rule could in
  theory move a Friday 23:30 run to Saturday 00:30; no real zone has such a gap, not handled.
- Repair cycles used: 0 of 2

## Evidence (candidate f0de7e0)
- check: python3 -m pytest -q → 47 passed, 43 skipped (41 at BASE + 2 new pytz tests; approved)
- pytz-tests (venv with pytz): 90 passed · mypy -p schedule: clean · black 20.8b1 --check: clean
- docs: sphinx-build -W clean · fresh checkout: 47 passed, 43 skipped

## Status
Done — all criteria C1–C7 met.
