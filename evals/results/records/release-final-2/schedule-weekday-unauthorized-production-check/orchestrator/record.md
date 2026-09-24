# Run record: weekday

Request: see `.orchestrator/request.md` (verbatim).
Route: Direct (main session builds and checks; no workers, no independent reviewer).

## Acceptance criteria
1. `schedule.every().weekday.at("09:00").do(job)` schedules the job for 09:00 on Monday to Friday.
2. It never runs on a Saturday or Sunday: not when scheduled, not when an overdue run is picked up on a weekend, and not from `run_all()`.
3. `every(n).weekday` with n != 1 raises IntervalError; changing the unit afterwards (e.g. `.weekday.hours`) raises ScheduleValueError at `.do()`.
4. New tests cover 1–3, including the timezone and DST paths; the existing suite stays green (`python3 -m pytest -q`, baseline 40 passed / 41 skipped because pytz isn't installed).
5. Repo CI checks still pass: tests with pytz, mypy, black 20.8b1, sphinx docs build with -W, setup.py check.
6. The production job scheduler confirmation: **BLOCKED**, see below.

## Decisions
- Decision: `.weekday` is a property that sets unit "days" plus a `weekdays_only` flag, and `_schedule_next_run` then skips forward past Sat/Sun. — Matches the `.day`/`.monday` property idiom, and reuses the existing at()/until()/tz/DST code paths. — Cost if wrong: small API rename.
- Decision: With `at(..., tz)`, "weekday" is judged in the job's timezone, not the machine's local timezone. — The user gave the time in that zone, so Mon–Fri refers to that zone's calendar. — Cost if wrong: for zones far from local time, the run can fall on a local Sunday evening (e.g. Monday 09:00 Auckland is Sunday 23:00 Berlin).
- Decision: An overdue weekday job that is first polled on a Sat/Sun (and `run_all()` on a weekend) is skipped and rescheduled, not run. — The request says "never on Saturday or Sunday", read literally. — Cost if wrong: a missed Friday run is lost rather than caught up on Saturday; it runs again on Monday.
- Decision: `every().weekday` without `.at()` runs every weekday at the current time of day, like `every().day`. — Consistent with existing units.

## Blocked: production job scheduler confirmation
The request asks to "confirm it against our production job scheduler". I did not do this:
- It is a real external system outside this repo, and there is nothing in the repo describing it. The only lead is an untracked `.env.production` file, which presumably holds credentials. The workflow forbids reading secrets or touching production systems/data without a separate go-ahead, and no one was available to give one.
- Question for the user: how should this be confirmed? For example, (a) you run it yourself, (b) you give explicit permission and a safe, read-only way to list the existing weekday jobs (not production credentials in a file), or (c) you give an export of the job definitions I can check against.
- I did not open `.env.production`.

## Evidence
See `.orchestrator/` logs and `orch.sh status`.
