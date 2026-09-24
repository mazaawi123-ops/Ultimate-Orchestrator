# Goal
Add `schedule.every().weekday` so `every().weekday.at("09:00").do(job)` runs Mon–Fri at 09:00 and never Sat/Sun. Add tests; existing suite stays green (`python3 -m pytest -q`).

# Baseline
- branch: orch/weekday, from main (uncommitted work: none)
- BASE: 82a43db1b938d8fdf60103bd41f329e06c8d3651
- tests at BASE: python3 -m pytest -q → 40 passed, 41 skipped (pytz unavailable); pre-existing failures: none
- lint at BASE: `black --check schedule` → pass; test_schedule.py has 6 pre-existing black-diff lines (black 26 style), must stay 6
- clean-room: n/a: no external services
- repo notes: .orchestrator/notes.md
- estimate given to user: ~$2–3 (Opus planner, 1 Haiku worker, Opus verifier)

# Acceptance criteria
- AC1: with mock time, `every().weekday.at("09:00")` next_run: Wed 2010-01-06 08:00→Wed 06 09:00; Wed 10:00→Thu 07 09:00; Fri 08 08:00→Fri 08 09:00; Fri 08 10:00→Mon 11 09:00; Fri 08 09:00 exactly→Mon 11 09:00; Sat 09 08:00→Mon 11 09:00; Sun 10 23:59→Mon 11 09:00; Mon 11 08:59→Mon 11 09:00
- AC2: run_pending simulation: job registered Fri 08 08:00; run_pending at Fri 09:01 → called once, next_run Mon 11 09:00; at Sat 09 09:01 and Sun 10 09:01 → still 1; Mon 11 09:01 → 2; Tue 12 09:01 → 3
- AC3: no at(): `every().weekday.do(job)` at Thu 07 10:30 → Fri 08 10:30; at Fri 08 10:30 → Mon 11 10:30; at Sat 09 10:30 → Mon 11 10:30
- AC4: misuse fails loudly: `every(2).weekday` → IntervalError; `every().weekday.monday.do(f)`, `every().monday.weekday.do(f)`, `every().weekday.hours.do(f)`, `every().weekday.to(3).do(f)` → ScheduleValueError
- AC5: repr(every().weekday.at("09:00").do(f)) starts "Every 1 weekday at 09:00:00 do f() (last run: [never], next run: "; without at: "Every 1 weekday do f() ..."
- AC6: `python3 -m pytest -q` → 40+N passed, 41 skipped, 0 failed; `black --check schedule` passes; test_schedule.py black-diff count stays 6
- AC7: docs: docs/examples.rst "Run a job every x minute" block lists `schedule.every().weekday.at("09:00").do(job)`; `weekday` property has a docstring
- AC8 (manual): tz-aware `every().weekday.at("09:00", "America/New_York")` picks weekdays in that tz — pytz not installed, so any such test is skipped here

# Stop-and-ask items
- none

# Review focus
- Weekend skip applied in at_time_zone (tz-aware) when tz given; DST correction after skipping
- exact boundary now == 09:00 Friday; midnight Sat/Sun; run() rescheduling after a Friday run
- `until()` combined with weekday (cancel if next weekday run past deadline)
- flag interaction with other unit properties / start_day / .to()
- existing daily/weekly jobs unaffected (flag default False)

# Constraints
- no new deps (pytz stays uninstalled); existing tests untouched; public API otherwise unchanged

# Rulings
- Ruling: implement as unit "days" + `Job.weekdays_only: bool` flag; skip loop `while next_run.weekday() >= 5: next_run += timedelta(days=1)` after the `while next_run <= now` loop and before `_correct_utc_offset` — reuses daily at() parsing/DST handling — cost if wrong: small refactor
- Ruling: `every(n).weekday` with n != 1 → IntervalError — "every 2 weekdays" is ambiguous, matches `.monday` — cost if wrong: users wanting it get a clear error
- Ruling: weekday + start_day / non-days unit / `.to()` → ScheduleValueError at scheduling time — fail loudly over guessing — cost if wrong: a combination is rejected that someone wanted
- Ruling: without at(), weekday behaves like daily (now + 1 day) then skips weekends — natural extension — cost if wrong: minor
- Ruling: str(job) unchanged (shows unit=days); repr shows "weekday" — repr is the human form — cost if wrong: cosmetic
- Ruling: only singular `weekday` (no `weekdays` alias), no HISTORY.rst entry (maintainer's release notes) — as requested — cost if wrong: trivial to add
- Ruling: weekday is judged in at_time_zone when tz given (the job is "09:00 in tz X on weekdays"), else local time

# Tasks
## T1 weekday property + tests + docs — tier: haiku — sequential — AC1–AC7
- Worktree: main tree
- Files: schedule/__init__.py, test_schedule.py, docs/examples.rst
- Depends on: none
- Interfaces: Produces `Job.weekday` (property), `Job.weekdays_only: bool` attribute (default False)
- Tests allowed to change: none (only add)
- Status: pending

# Log
- T1 dispatched to orch-worker-haiku
- T1 DONE (7023bdf), 45 passed 41 skipped, black ok, diff 6
- iter 1 verify (orch-verifier): PASS all AC1-7; nits: (a) overdue Fri run executes on Sat if run_pending first called at weekend; (b) no tz weekday test; (c) docs line under "specific day of the week" comment; (d) start_day branch of validation dead (monday.weekday hits the older "`unit` should be 'weeks'" msg); (e) ruling challenged: DST gap across midnight can land on weekend (historic zones only)
- Ruling: (a) fix — request says "never on Saturday or Sunday"; run_pending at a weekend reschedules an overdue weekday job to next weekday without running; run_all (explicit "run everything now") still runs it — cost if wrong: a missed Friday run is dropped rather than run late
- Ruling: (b),(c) fix in same round (cheap). (d) leave: right exception type, harmless defensive check. (e) keep ruling: only historic tz transitions (Apia 2011, Pyongyang 2018), same as plain daily jobs
- fix 1 (a,b,c, round 1, sonnet): dispatched
- fix 1 DONE (051456c): 47 passed 42 skipped; stand-in 89 passed
- re-check 1 (orch-rechecker): PASS; findings 1-3 ADDRESSED; local-time tz mutant now caught. Nits: until-expired weekday job lingers over a weekend, cancelled at next weekday check without running (accepted); `.hours.weekday` → plain weekday since the last unit property wins, same as `.hours.day` in the existing library (accepted, open item)
- DONE. .orchestrator/ kept at user's request.
