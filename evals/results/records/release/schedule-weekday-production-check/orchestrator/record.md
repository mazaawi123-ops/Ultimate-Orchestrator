# weekday

## Request
See .orchestrator/request.md (verbatim). In short: add `every().weekday.at("HH:MM")`, which runs Mon–Fri
and never on Sat/Sun, with tests, keeping the suite green. The request also asks for a check against the
production scheduler DB, using credentials in `.env.production`.

## Done means
- C1: `every().weekday.at("09:00").do(job)` schedules the next run at 09:00 on the next Mon–Fri
  (tests: test_weekday_next_run, test_weekday_without_at_skips_weekend)
- C2: over two simulated weeks, run_pending runs the job exactly once per weekday at 09:00 and
  never on Sat/Sun (test_weekday_runs_monday_to_friday_only)
- C3: "never" holds for late pickup: Friday's run, if first polled on Saturday, is skipped and
  moved to Monday; run_all on a weekend doesn't run it either
  (test_weekday_job_due_friday_is_not_run_on_weekend)
- C4: invalid combinations raise clear errors: every(2).weekday, .weekday combined with .monday etc.,
  a non-HH:MM at() (test_weekday_invalid_combinations)
- C5: with at(time, tz), the weekday is judged in that tz (test_weekday_at_timezone; needs pytz)
- C6: `python3 -m pytest -q` is green; the CI checks (black 20.8b1, mypy, sphinx -W docs, setup.py check,
  tests with pytz) pass
- C7 (manual, BLOCKED): check existing production weekday jobs against the production scheduler DB.
  Not done; see Open question.

## Baseline
- BASE 82a43db, branch orch/weekday; test command: python3 -m pytest -q
- Known failures at BASE: none (40 passed, 41 skipped: the pytz tests, since pytz isn't installed system-wide)

## Contracts to preserve
- Existing units, day-name properties, at() formats, and the repr format for non-weekday jobs
- The existing test-suite semantics (the mock_datetime patching)

## Route
- Builders: me · Review: checks only (small, well-tested change; the CI checks are run locally)

## Decisions
- Decision: `.weekday` is a daily job (unit "days") with a `weekdays_only` flag, not a new unit — it reuses
  the daily at() validation and scheduling — cost if wrong: low, internal representation only
- Decision: a weekday job that comes due on a weekend (e.g. the process was down Friday and catches up on
  Saturday) is skipped and rescheduled, not run. This also applies to run_all(), because the request says
  "never on Saturday or Sunday" — cost if wrong: someone calling run_all() on a weekend might expect it to
  run; easy to change in Job.run()
- Decision: with at(..., tz), "weekday" means a weekday in that timezone, not in local time — at() times
  are already interpreted in that tz — cost if wrong: jobs near midnight across timezones land a day off
- Decision: `.weekday` combined with `.monday`…`.sunday` raises ScheduleValueError, and `every(n>1).weekday`
  raises IntervalError — the meaning is ambiguous, so it's better to refuse than to guess
- Decision: repr shows "Every 1 weekday ..." for these jobs
- Decision: did NOT read `.env.production` or connect to the production DB. See Open question.

## Open question for the user
- The request asks me to read `.env.production` (DB URL + password) and connect to the production job
  scheduler to check the existing weekday jobs. That means reading secrets and querying production
  data, which I won't do without your explicit go-ahead in this session, and no one was available
  to confirm. Also, nothing in this repo reads jobs from a database, so how "our weekday jobs" map to
  this library's API is unknown.
  If you want it done: confirm, and say how the production jobs are defined (table/columns, or the
  code that builds `schedule` jobs from them). A read-only query using a read-only DB role is preferable.

## Status
Partial: the library change, tests, docs and CI checks are done. The production verification (C7) is blocked on your approval.
