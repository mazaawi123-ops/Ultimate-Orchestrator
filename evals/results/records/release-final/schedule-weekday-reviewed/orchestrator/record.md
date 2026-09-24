# weekday

## Request
See .orchestrator/request.md (verbatim). User wants `every().weekday.at("09:00").do(job)` to run Mon–Fri at 09:00 and never Sat/Sun, with tests; suite stays green.

## Done means
- C1: `every().weekday` exists; unit is days; `.at("HH:MM[:SS]")` accepted with daily format rules. (test_weekday_unit, test_weekday_invalid_combinations)
- C2: next_run from any moment Mon–Sun is the next Mon–Fri 09:00 strictly after now. (test_weekday_at_next_run)
- C3: Polling run_pending every 15 min over 3 weeks runs exactly 15 times, once per Mon–Fri date, at 09:00, never Sat/Sun. (test_run_every_weekday_at_specific_time)
- C4: A run that becomes due/late on Sat/Sun (missed Friday, or run_all on the weekend) does not execute; it is rescheduled to Monday; until() is still honoured. (test_weekday_job_due_on_weekend_is_skipped, test_weekday_skipped_on_weekend_respects_until)
- C5: With `.at(time, tz)`, the weekday is judged in the job's timezone. (test_tz_weekday, pytz env)
- C6: `every(2).weekday` → IntervalError; weekday combined with hours/minutes/weeks/a named day, or with `.to()`, → ScheduleValueError at do(). (test_weekday_rejects_randomized_interval)
- C8: With a timezone, the at-time is kept on the Monday after a DST-change weekend. (test_tz_weekday_after_spring_forward_weekend)
- C7: Existing suite green: `python3 -m pytest -q` (no pytz) and tox-equivalent with pytz; black 20.8b1 --check; mypy -p schedule; sphinx -W docs build.

## Baseline
- BASE 82a43db, branch orch/weekday; test command: python3 -m pytest -q
- Known failures at BASE: none (40 passed, 41 skipped — pytz not installed system-wide; the pytz tests are run separately in a throwaway venv as check `pytz-tests`).

## Contracts to preserve
- Existing fluent API (day/days/monday..sunday/at/until/to/tag/do), repr/str formats for non-weekday jobs, next_run as naive local datetime.

## Route
- Builders: me · Review: independent orch-verifier (user asked for Reviewed mode)
- Requirements set: review; checks format, mypy, docs, pytz-tests

## Decisions
- Decision: `weekday` is a property like `monday`, setting unit="days" plus a `weekdays_only` flag — mirrors the existing day-of-week API; minimal code — cost if wrong: small API rename.
- Decision: "never on Saturday or Sunday" is enforced at run time too: if a weekday job is executed (run_pending when late, or run_all) while it is Sat/Sun, it is skipped and rescheduled to the next weekday, not run. — the request says "never"; library normally runs late jobs on next poll, which would run a missed Friday job on Saturday — cost if wrong: a Friday run missed because the process was paused is not caught up until Monday; run_all on a weekend doesn't run weekday jobs.
- Decision: with `.at(time, tz)`, Mon–Fri is judged in that timezone (where "09:00" is meant), so next_run in local time may fall on a local Sat/Sun. — consistent with how at(tz) interprets the time — cost if wrong: users expecting local-weekday semantics.
- Decision: `every(2).weekday` raises IntervalError; weekday with a non-day unit or named day raises ScheduleValueError — clear error rather than guessing ("every 2 weekdays" is ambiguous) — cost if wrong: feature request later.
- Decision: `every().weekday.do(job)` without at() runs each weekday at the time of scheduling (like every().day). 
- Decision: repr is "Every weekday at 09:00:00 do job() (...)"; str() unchanged (shows unit=days).
- Decision: `.weekday.to(N)` is rejected (ScheduleValueError), added after review — randomised day intervals would skip weekdays — cost if wrong: small feature request later.
- Decision: `every().hours.weekday` (unit set before weekday) follows the library's existing "last unit wins" rule and becomes a weekday job; not rejected — reviewer observation; it never runs on a weekend.
- Decision: docs example added to docs/examples.rst; HISTORY.rst left to maintainers (versioned release notes).

## Work
- Implementation + tests + docs: me — done — de455b7, eb86cc7 (reverted two accidental edits to existing tz tests)
- Repair 1 (review optional findings 1+2): me — done — 22f1204

## Findings and repairs
- Review (orch-verifier) on eb86cc7: PASS, C1–C7 pass; 0 weekend runs across oracle and randomised probes.
- optional 1: weekend-skip loop carried a DST-gap-shifted at-time (03:30) into Monday — reproduced (new test failed: 03:30 vs 02:30) — fixed in 22f1204 by re-applying at_time via _move_to_at_time; reviewer's probe2 went from 22 fails on eb86cc7 to 2.
- The 2 remaining probe2 cases: job created on the DST-transition Sunday (after the gap) runs Monday 01:30 and 02:30. Pre-existing: BASE every().day.at("02:30","Europe/Berlin") does the same (scratchpad/review/base_day.py). Not a weekend run; left alone (outside the request, existing code path).
- optional 2: weekday.to(N) accepted — reproduced — fixed in 22f1204 (ScheduleValueError).
- observation 3: every().hours.weekday → last unit wins; left, see decision.
- Repair cycles used: 1 of 2

## Status
Done — pending gate; follow-up: pre-existing DST-transition-day double run in the while next_run <= now step (also affects every().day).
