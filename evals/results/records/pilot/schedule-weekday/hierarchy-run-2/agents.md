# Agents dispatched in schedule-weekday/hierarchy/run-2

## 1. orch-worker-haiku: T1 weekday scheduling

### Brief

```text
You are a worker on one task in a larger plan. Your deliverable is exactly the task below, with tests, and a report. Changes outside it belong in your report under "noticed", where the planner can decide on them.

You do not dispatch subagents. You do not ask the user questions — if the brief leaves something open that changes what you build, return NEEDS_CONTEXT with the question.

Work economically: every turn re-reads your whole context. Trust the repo notes below instead of exploring, read only the files you need, and chain shell commands with `&&`.

## Task
T1: Add a `weekday` builder property to `Job` so `schedule.every().weekday.at("09:00").do(job)` runs Monday–Friday at 09:00 and never on Saturday or Sunday. Implement exactly as specified below, add tests, and add one docs example line.

### Implementation spec (schedule/__init__.py)
1. In `Job.__init__`, right after the `self.start_day` block, add:
   ```python
   # Only run on weekdays (Monday to Friday). Only relevant when unit is 'days'.
   self.weekdays_only: bool = False
   ```
2. Add a property right after the `sunday` property:
   ```python
   @property
   def weekday(self):
       if self.interval != 1:
           raise IntervalError(
               "Scheduling .weekday jobs is only allowed for jobs that run "
               "every weekday. Using .weekday on a job scheduled to run every "
               "2 or more days is not supported."
           )
       self.weekdays_only = True
       return self.days
   ```
3. In `_schedule_next_run`, directly after the existing unit-validation `raise ScheduleValueError(...)` block (before the `if self.latest is not None:`), add:
   ```python
   if self.weekdays_only and (self.unit != "days" or self.start_day is not None):
       raise ScheduleValueError(
           "`.weekday` cannot be combined with another time unit or day of the week"
       )
   ```
4. In `_schedule_next_run`, after the `while next_run <= now: next_run += period` loop and BEFORE the `next_run = self._correct_utc_offset(...)` call, add:
   ```python
   if self.weekdays_only:
       # Skip Saturday (5) and Sunday (6). next_run is still in the job's
       # timezone here, so the weekday is judged where the at-time lives.
       while next_run.weekday() >= 5:
           next_run += datetime.timedelta(days=1)
   ```
5. In `__repr__`, both branches currently derive the unit word from `self.unit[:-1] if self.interval == 1 else self.unit`. Compute it once before the `if self.at_time is not None:` as `unit = "weekday" if self.weekdays_only else (self.unit[:-1] if self.interval == 1 else self.unit)` and use `unit` in both branches (behaviour for non-weekday jobs must stay identical). Leave `__str__` unchanged.

### Tests (append to test_schedule.py, in the same TestCase class as `test_run_every_weekday_at_specific_time_today`, ~line 1427, same style: `mock_datetime`, `make_mock_job()`, module-level `every()` / `schedule.run_pending()`)
Exact expected results (Sept 2024: Mon 23, Tue 24, Wed 25, Thu 26, Fri 27, Sat 28, Sun 29, Mon 30; Tue Oct 1). Assert `job.next_run == datetime.datetime(...)`:
- `every().weekday.at("09:00").do(mock_job)` scheduled at:
  - Mon 2024-09-23 08:00 → 2024-09-23 09:00
  - Mon 2024-09-23 09:30 → 2024-09-24 09:00
  - Fri 2024-09-27 08:00 → 2024-09-27 09:00
  - Fri 2024-09-27 09:00 (exactly) → 2024-09-30 09:00
  - Fri 2024-09-27 09:30 → 2024-09-30 09:00
  - Sat 2024-09-28 08:00 → 2024-09-30 09:00
  - Sun 2024-09-29 23:59 → 2024-09-30 09:00
- A week-long run test: schedule at Mon 2024-09-23 08:00; then 6 times: enter `mock_datetime` at the job's current next_run (year, month, day, hour, minute), call `schedule.run_pending()`, record the run date. Expected run dates: 23, 24, 25, 26, 27, 30 September (all 09:00), mock_job.call_count == 6, and final next_run == 2024-10-01 09:00. Also check that with `mock_datetime(2024, 9, 28, 9, 0)` and `(2024, 9, 29, 9, 0)` run_pending does NOT call the job (do this between the Friday and Monday runs).
- No at(): `every().weekday.do(mock_job)` at Fri 2024-09-27 14:00 → next_run 2024-09-30 14:00; at Wed 2024-09-25 14:00 → 2024-09-26 14:00.
- `at("09:00:30")` at Sat 2024-09-28 08:00 → 2024-09-30 09:00:30.
- `every(2).weekday` raises `IntervalError` (use `self.assertRaises` like nearby tests).
- Each of these raises `ScheduleValueError` on `.do(mock_job)`: `every().weekday.hours`, `every().monday.weekday`, `every().weekday.monday`. (Note: `every().weekday.monday` — `monday` returns `self.weeks`, so unit is "weeks".)
- repr: at Mon 2024-09-23 08:00, `repr(every().weekday.at("09:00").do(job_fun))` (use a plain function named `job_fun` defined in the test, or reuse an existing helper as nearby repr tests do) starts with `"Every 1 weekday at 09:00:00 do job_fun()"`.
- Import `IntervalError` / `ScheduleValueError` the way the test file already does.

### Docs
In docs/examples.rst, in the block containing `schedule.every().tuesday.at("16:40").do(job_2)` is a run_all example — do NOT put it there. Instead find the main "Run a job every x minute" style example block near the top (the one with lines like `schedule.every().monday.do(job)` / `schedule.every().wednesday.at("13:15").do(job)`) and add right after the wednesday line: `schedule.every().weekday.at("09:00").do(job)` with no comment, matching indentation. If no such line exists, add it after the first `.at(` example in the first code block and mention where in your report.

## Why
Users want business-day jobs. Combining `.weekday` with other units must fail loudly, because a silent override would make the job run on weekends. The weekday check happens before converting to local time so that a job with `at("09:00", "America/New_York")` is judged by the New York date.

## Context
- repo: <workspace>/pilot-results/schedule-weekday/hierarchy/run-2/repo — the main tree, on branch orch/weekday; no new branches or worktrees
- files you'll touch: schedule/__init__.py (library), test_schedule.py (tests), docs/examples.rst (docs)
- file to imitate for style: existing code in those same files
- interfaces you must produce: `Job.weekday` property; attribute `Job.weekdays_only: bool`
- known failures at BASE: none (41 tests skip because pytz is not installed — expected; leave them)

## Repo notes
- Single-module lib: schedule/__init__.py (Scheduler, Job, every(), helpers _move_to_next_weekday/_weekday_index). Tests: test_schedule.py (one big file, pytest).
- Test: `python3 -m pytest -q` → baseline 40 passed, 41 skipped (skips = pytz not installed; expected, leave them).
- mypy/pytz NOT installed; don't install. Keep type annotations consistent (tox runs mypy in CI).
- Job builder API = @property methods returning self (e.g. `days`, `monday`); `monday` sets self.start_day and returns self.weeks; interval!=1 guards raise IntervalError.
- Next-run logic: Job._schedule_next_run (~line 700). `next_run` is tz-aware in self.at_time_zone when at(..., tz) used, else naive local. Loop `while next_run <= now: next_run += period`, then `_correct_utc_offset(next_run, fixate_time=...)`, then converted to naive local.
- Tests use `mock_datetime(y, m, d, H, M[, S])` context manager + `make_mock_job()`; module-level `every()`/`schedule.run_pending()` hit the default scheduler, cleared in setUp. See test_run_every_weekday_at_specific_time_today (~line 1427) for style.
- Style: black formatting, double quotes.

## Always (unless this brief explicitly says otherwise)
- No new dependencies: don't install packages or edit dependency files.
- No real external services. Clean-room check: n/a: no external services.
- No secrets: don't open `.env` or credential files.
- No real user data.
- Stay inside the repo path above.

## Existing tests
Tests that existed before your task are fixed points. Don't edit, delete, skip or loosen them. Tests you may change: none. If an existing test contradicts this brief, stop and return NEEDS_CONTEXT.

## Done means
- All the tests above exist and pass; `python3 -m pytest -q` (FULL suite) passes with only the pre-existing pytz skips (expect 40 + your new tests passed, 41 skipped).

## Test evidence
Write the tests first, run them before implementing and confirm they fail for the right reason (AttributeError: no `weekday`), then implement and make them pass.

## If you're out of your depth
Return BLOCKED with what you tried. If you stop early, don't commit, and list changed files.

## Report
Commit only the files you changed, named one by one:
`git add schedule/__init__.py test_schedule.py docs/examples.rst && git commit -m "T1: add every().weekday scheduling"`. Never `git add -A` or `git add .`. Then run `git status --porcelain`, remove your own scratch files, list anything else still there.

Before writing the report, re-read the code right next to yours. Note anything that looks wrong under "Things you noticed", or write "looked, found nothing".

Write the full report to `<repo path above>/.orchestrator/task-1-report.md`: files changed; tests added with RED and GREEN output; full-suite command and verbatim tail; deviations; things noticed.

Then reply with ONLY (under 15 lines):
STATUS: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
Commits: <hashes>
Tests: <command> → <N passed, M failed>
Concerns / blocker / question: <or "none">
Unspecified inputs: <for each input the brief gave no example for: one line on what your code does with it>
Decisions / deviations: <or "none">
Report: <path>

If "Decisions / deviations" isn't "none", the status is DONE_WITH_CONCERNS.
```

### Reply

```text
STATUS: DONE
Commits: e44795b (T1: add every().weekday scheduling)
Tests: python3 -m pytest -q → 47 passed, 41 skipped
Concerns / blocker / question: none
Unspecified inputs: None - all inputs were fully specified in the brief
Decisions / deviations: none
Report: <workspace>/pilot-results/schedule-weekday/hierarchy/run-2/repo/.orchestrator/task-1-report.md
```

## 2. orch-verifier: Full verify weekday change

### Brief

```text
You are an independent verifier. Code was written to satisfy the acceptance criteria below. You didn't write it. Treat every claim that it works, including comments and docstrings in the code, as unverified. Your job is to try to show it does NOT meet the criteria, and to say so plainly if you can't.

You are read-only on tracked files: scratch scripts go in /tmp (or <workspace>). You do not dispatch subagents.

## Repo
<workspace>/pilot-results/schedule-weekday/hierarchy/run-2/repo. Diff under review: <repo>/.orchestrator/diff-1.patch (BASE 82a43db1b938d8fdf60103bd41f329e06c8d3651, HEAD e44795b).

User request: "add a way to schedule a job on weekdays only: `schedule.every().weekday.at("09:00").do(job)` should run Monday to Friday at 09:00 and never on Saturday or Sunday. Add tests; the existing suite must stay green."

## Commands
- tests: `python3 -m pytest -q` (41 skips are pre-existing: pytz not installed)
- lint/typecheck: none installed locally (CI runs mypy via tox). You may create a throwaway venv in the scratchpad dir above and pip install pytz/mypy there to exercise timezone paths and typecheck (`python -m mypy -p schedule`), if the network allows; do not install into the system Python or change repo files.
- pre-existing failures at BASE: none
- clean-room test command: n/a: no external services

## Acceptance criteria
- AC1: `every().weekday.at("09:00").do(job)` next_run: Mon 2024-09-23 08:00 → 09-23 09:00; Mon 09:30 → Tue 09-24 09:00; Fri 09-27 08:00 → 09-27 09:00; Fri 09:00 exactly → Mon 09-30 09:00; Fri 09:30 → Mon 09-30; Sat 09-28 08:00 → Mon 09-30 09:00; Sun 09-29 23:59 → Mon 09-30 09:00
- AC2: driving run_pending over a week from Mon 09-23 08:00 runs the job on 23,24,25,26,27 then 30 (all 09:00); never Sat/Sun
- AC3: `every().weekday.do(job)` (no at) at Fri 09-27 14:00 → Mon 09-30 14:00; Wed 09-25 14:00 → Thu 09-26 14:00
- AC4: `every(2).weekday` raises IntervalError; `every().weekday.hours.do(j)`, `every().monday.weekday.do(j)`, `every().weekday.monday.do(j)` raise ScheduleValueError
- AC5: repr starts "Every 1 weekday at 09:00:00 do job()"; `at("09:00:30")` → 09:00:30
- AC6: `python3 -m pytest -q` passes; no existing test modified

## Review focus
- weekday judged in the job's timezone when at(..., tz) is used (date differs between tz and local zone); DST time fixation after skipping weekend days (e.g. weekend containing a DST change)
- exact-boundary now == at time on Friday; `until()` / cancel_after interplay; `to()`/latest combinations; chaining other units after `.weekday`; repr/str
- behaviour of existing jobs unchanged (repr of non-weekday jobs byte-identical)

## Rulings
- Ruling: implement as flag `weekdays_only` + unit "days", skip Sat/Sun after the normal day computation — minimal, reuses days/at/tz logic — cost if wrong: small refactor
- Ruling: `.weekday` only with interval 1 (IntervalError otherwise), like `.monday` — "every 2 weekdays" is ambiguous — cost if wrong: feature request later
- Ruling: combining `.weekday` with another unit or a named day fails loudly with ScheduleValueError at scheduling time — silent override would run on weekends
- Ruling: weekday determined in the at() timezone when given (that's where "09:00" lives) — cost if wrong: a job near midnight could run on local Sat
- Ruling: `.weekday` without `.at()` runs at the current time of day on the next weekday, same as `every().day`
- Ruling: `every().weekday.to(n)` not rejected; latest adds days then weekend-skip
- Ruling: no pytz install into the repo environment
- Ruling: add example line to docs/examples.rst; no HISTORY entry
Check the code follows each one. Behaviour that follows a ruling is not a finding. If you think a ruling itself is wrong, list it under Findings as `ruling challenged`, with why.

## Do
1. Run the tests yourself. Paste the output.
2. For each criterion, check it directly — run the code — and try the review-focus cases that apply.
3. Read the diff for what tests can't catch: debug leftovers, public behaviour changed outside the criteria, missing cleanup. The request is a description of intent, not an exhaustive spec.
4. Check for changes the plan didn't allow: any test that existed at BASE edited/deleted/skipped/loosened is at least should-fix (tests allowed to change: none). Also flag new dependencies, external calls, secrets.

## Report (this structure)
### Verdict: PASS | FAIL
### Per criterion
- AC1: PASS | FAIL — evidence
### Test run
<verbatim tail>
### Findings outside the criteria
- <blocker | should-fix | nit | ruling challenged> <file:line> <what, and why it matters>
### Declined to judge
- <...> or "none"
### If FAIL: smallest change that would make it pass
```

### Reply

```text
### Verdict: PASS

All six criteria hold when run directly. There are two should-fix findings outside the criteria. The first will turn the repo's CI "formatting" job red; the second is a partial departure from the "fails loudly" ruling.

### Per criterion
- **AC1: PASS.** I ran all 7 listed cases through the repo's `mock_datetime` (TZ Berlin). Each `next_run` matches exactly, including Fri 09:00 exactly → Mon 09-30 09:00 and Sun 23:59 → Mon 09:00.
- **AC2: PASS.** I called `run_pending` every minute from Mon 09-23 08:00 to Tue 10-01 08:00. It ran at exactly `[09-23, 09-24, 09-25, 09-26, 09-27, 09-30]`, all at 09:00, with no Saturday or Sunday runs.
- **AC3: PASS.** Fri 14:00 → Mon 09-30 14:00 and Wed 14:00 → Thu 09-26 14:00. Extra cases also correct: Sat → Mon, Sun → Mon, Thu → Fri, all at 14:00.
- **AC4: PASS.** `every(2).weekday` raises IntervalError. `weekday.hours`, `monday.weekday` and `weekday.monday` raise ScheduleValueError. So do all other units placed after `.weekday` (seconds, minutes, weeks and their singular forms) and every named day in either order. A failed `.do()` leaves no job in the scheduler.
- **AC5: PASS.** The repr is `Every 1 weekday at 09:00:00 do job() (last run: [never], next run: 2024-09-23 09:00:00)`. With `at("09:00:30")` it reads `Every 1 weekday at 09:00:30 do job()` and next_run is 09:00:30.
- **AC6: PASS.** 47 passed and 41 skipped, against 40 and 41 at BASE, so 7 tests were added. `test_schedule.py` numstat is `174 0`: only additions, no existing test touched. With pytz installed in a scratch venv, 88 passed. `mypy -p schedule` reports "Success: no issues found".

Review-focus cases I ran with pytz (all correct):
- **Weekday judged in the `at()` timezone:**
  - Local Berlin with `at("09:00","Pacific/Auckland")`: runs on local Sun 23:00 (Auckland Monday). There is no run on local Fri 23:00 (Auckland Saturday).
  - Local UTC with `at("22:00","America/New_York")`: runs on local Sat 02:00 (New York Friday), none on local Mon 02:00 (New York Sunday).
  - Both match the ruling.
- **DST change during the weekend:**
  - Berlin, 2024-10-27 fall-back: Fri, Sat and Sun 23:00 all → Mon 09:00. A two-week minute-by-minute run gives exactly the 11 weekday runs at 09:00.
  - Berlin, 2024-03-31 spring-forward, `at("02:30")`: → Mon 02:30.
  - US 2024-11-03 (local New York, `at` Chicago): → Mon 10:00 local.
  - Auckland, 2024-09-29 DST start: → Mon 09:00.
- **`until()`:** a job limited to Fri 12:00 runs Mon–Fri, then cancels. One limited to Sat 12:00 and scheduled Fri 09:30 never runs and is cancelled on Monday.
- **`to(3)`:** tried with and without `at`, 8 seeds, 3 weeks each. No weekend runs.
- **Other paths:** `@repeat(every().weekday.at("09:00"))` works.
- **Existing jobs:** repr and str of 22 non-weekday job shapes (bound and unbound) are byte-identical between BASE and HEAD, checked by diffing the output.

### Test run
```
$ python3 -m pytest -q
ss.ssss........................sss.ss...................ssssssssssssssss [ 81%]
ssssssssssssss..                                                         [100%]
47 passed, 41 skipped in 0.14s
```
With pytz in the scratch venv: `88 passed in 0.24s`. mypy: `Success: no issues found in 1 source file`.

### Findings outside the criteria
- **should-fix: `schedule/__init__.py:305` fails the formatting check.** CI's `formatting` job runs `tox -e format`, which is `black --check .` with the pinned `black==20.8b1`. BASE passes that check ("4 files would be left unchanged"); HEAD fails it ("1 file would be reformatted"). Black wants this 105-character line split up:
  ```python
  unit = (
      "weekday"
      if self.weekdays_only
      else (self.unit[:-1] if self.interval == 1 else self.unit)
  )
  ```
- **should-fix: `schedule/__init__.py:463-471` and `:725` silently accept a unit placed before `.weekday`.** The ruling says combining `.weekday` with another unit fails loudly. That only holds when the other unit comes after `.weekday` or is a named day.
  - The `.weekday` property overwrites `self.unit` with `"days"`, so the check at line 725 can't see an earlier unit.
  - `every().hour.weekday.do(j)`, `every().minutes.weekday`, `every().second.weekday` and `every().week.weekday` are all accepted. Each silently becomes a once-a-day weekday job: repr `Every 1 weekday do job()`, unit `days`.
  - It never runs on a weekend, but someone who wrote "every hour on weekdays" gets one run a day with no error.
  - The library has a precedent: at BASE, `every().hours.monday` also silently becomes weekly. Still, this goes against the ruling as written.
- **nit: `test_schedule.py`, no test for the timezone ruling or DST.** None of the new tests uses `at(..., tz)`. Nothing pins "weekday judged in the `at()` timezone" or a DST change during the weekend, and pytz-gated tests would be skipped locally anyway. The behaviour is correct today, as shown above, but a regression would go unnoticed.

Nothing else turned up: no debug leftovers, new dependencies, external calls or secrets. The docs change is the one line in `docs/examples.rst` that the ruling allows. No HISTORY entry was added, as ruled.

### Declined to judge
- **Late runs:** if `run_pending` isn't called between Friday's 09:00 and Saturday (say the machine was asleep), Friday's overdue run happens on Saturday. I confirmed it: ran on Sat 08:00, then next_run is Mon 09:30… more precisely Mon 09-30 09:00. This is the library's normal overdue behaviour (`every().monday` behaves the same), and AC2 only covers `run_pending` being called on time. Whether "never on Saturday" should also cover late runs is a product decision.
- **DST gap across midnight:** if the clock jumps forward from Friday 23:xx into Saturday, the existing gap handling (`moment += offset_diff`) would push an `at` time inside that gap into Saturday. The weekend skip runs before `_correct_utc_offset`, so it wouldn't catch this. I found no real zone with that transition and didn't test it.

### If FAIL: smallest change that would make it pass
Not applicable, since all criteria pass. For the two should-fix items:
1. Run `black` 20.8b1 on `schedule/__init__.py` so line 305 is split as shown above.
2. In the `weekday` property, before `self.weekdays_only = True`, raise if a unit other than days is already set, e.g. `if self.unit not in (None, "days"): raise ScheduleValueError("`.weekday` cannot be combined with another time unit or day of the week")`. The ruling says "at scheduling time", so if the error must come from `.do()`, record a conflict flag here instead and raise it at line 725.

Files:
- Diff under review: `<workspace>/pilot-results/schedule-weekday/hierarchy/run-2/repo/.orchestrator/diff-1.patch` (identical to `git diff 82a43db HEAD`)
- My check scripts are in `<workspace>/`:
  - `verify_ac.py`
  - `verify_tz.py`
  - `verify_misc.py`
  - `verify_order.py`
  - `repr_cmp.py`
```

## 3. orch-worker-sonnet: Fix round 1 weekday

### Brief

```text
You are a worker on one task in a larger plan (fix round 1). Your deliverable is exactly the fixes below, with tests, and a report. Changes outside it belong in your report under "noticed".

You do not dispatch subagents. You do not ask the user questions — if something is open that changes what you build, return NEEDS_CONTEXT with the question. Work economically: chain shell commands with `&&`, read only what you need.

## Task
A previous commit (e44795b) added `Job.weekday` so `schedule.every().weekday.at("09:00").do(job)` runs Mon–Fri only. An independent verifier passed all criteria but raised the findings below. Fix all three.

## Findings to fix (verbatim from verifier)
1. should-fix `schedule/__init__.py:305` — breaks CI `formatting` job. CI runs `tox -e format` → `black --check .` pinned `black==20.8b1`. BASE passes ("4 files would be left unchanged"); HEAD fails ("1 file would be reformatted"). Black wants the 105-char line split as:
```python
        unit = (
            "weekday"
            if self.weekdays_only
            else (self.unit[:-1] if self.interval == 1 else self.unit)
        )
```
2. should-fix `schedule/__init__.py:463-471` + `:725` — unit set BEFORE `.weekday` is silently accepted. The planner's ruling: "combining `.weekday` with another unit or a named day fails loudly with ScheduleValueError". It only holds when the other unit comes after. The `.weekday` property overwrites `self.unit = "days"`, so the check at line 725 can't see an earlier unit. `every().hour.weekday.do(j)`, `every().minutes.weekday`, `every().second.weekday`, `every().week.weekday` are all accepted and silently become once-a-day weekday jobs.
3. nit `test_schedule.py` — no test for the timezone ruling ("weekday is judged in the at() timezone, not local") or a DST change over a weekend. Verifier confirmed these cases behave correctly with pytz: local TZ Europe/Berlin with `every().weekday.at("09:00", "Pacific/Auckland")` runs at local Sun 23:00 (Auckland Monday 09:00) and NOT at local Fri 23:00 (Auckland Saturday); Berlin fall-back 2024-10-27: scheduling `at("09:00")` at Fri 2024-10-25 23:00, Sat 23:00 or Sun 23:00 local → Mon 2024-10-28 09:00.

## How to fix
- Finding 1: reformat exactly as shown. Check with black 20.8b1 in the scratch venv: `<SCRATCH>/venv/bin/python -m black --check schedule test_schedule.py` if black is installed there (`ls <SCRATCH>/venv/bin`); if not, try `<SCRATCH>/venv/bin/pip install black==20.8b1 click==8.0.4` into THAT venv only. Never install into system python. If you can't get black, format by hand to black style and say so.
- Finding 2: in the `weekday` property, after the interval check and before setting the flag, add:
  ```python
  if self.unit not in (None, "days") or self.start_day is not None:
      raise ScheduleValueError(
          "`.weekday` cannot be combined with another time unit or day of the week"
      )
  ```
  (`every().day.weekday` / `every().days.weekday` stay allowed — harmless.) Keep the existing check in `_schedule_next_run` (catches units after `.weekday`). Note `every().monday.weekday` now raises at the `.weekday` step instead of at `.do()`; if the T1 test for it only wraps `.do()` in assertRaises, widen it to wrap the whole chain (these T1 weekday tests are new in this branch and you may adjust them; tests that existed at BASE 82a43db you may NOT touch). Add tests: each of `every().hour.weekday`, `every().minutes.weekday`, `every().second.weekday`, `every().week.weekday`, `every().monday.weekday` raises ScheduleValueError; `every().day.weekday.at("09:00").do(job)` at Sat 2024-09-28 08:00 → next_run 2024-09-30 09:00.
- Finding 3: add pytz-gated tests (skip with `self.skipTest("pytz unavailable")` exactly as existing tests at test_schedule.py ~line 104/514 do; see how existing tz tests set the local TZ via `mock_datetime(..., zone=...)` / the `TZ` env pattern they use — imitate the nearest existing tz test for `at(..., tz)`). Cases: (a) local Europe/Berlin, `every().weekday.at("09:00", "Pacific/Auckland")` scheduled at local Fri 2024-09-27 22:00 → next_run is local naive Sun 2024-09-29 23:00 (Auckland NZDT starts 2024-09-29 02:00 → UTC+13; Mon 09:00 NZDT = Sun 20:00 UTC = Sun 22:00 CEST... COMPUTE this yourself with pytz in the venv, don't trust my arithmetic; the key assertion is next_run lands on Auckland's Monday and not on Auckland's Saturday). (b) local Europe/Berlin, `every().weekday.at("09:00")` (no tz) scheduled at Sat 2024-10-26 23:00 → 2024-10-28 09:00. Run these in the venv (which has pytz) to confirm they pass, and in system python to confirm they skip.

## Context
- repo: <workspace>/pilot-results/schedule-weekday/hierarchy/run-2/repo — main tree, branch orch/weekday. Don't create branches/worktrees.
- <SCRATCH> = <workspace> (has `venv` with pytz and mypy). Use it for scratch; don't modify its other files.
- files: schedule/__init__.py, test_schedule.py
- known failures at BASE: none. 41 skips in system python are pytz-unavailable skips — expected.

## Repo notes
- Single-module lib: schedule/__init__.py (Scheduler, Job, every()). Tests: test_schedule.py (pytest).
- Test: `python3 -m pytest -q` → currently 47 passed, 41 skipped. In venv: `<SCRATCH>/venv/bin/python -m pytest -q` → 88 passed.
- mypy: `<SCRATCH>/venv/bin/python -m mypy -p schedule` must stay clean.
- Job builder API = @property methods returning self; `monday` sets start_day and returns self.weeks.
- Tests use `mock_datetime(y, m, d, H, M[, S][, zone=...])` + `make_mock_job()`.
- Sept 2024: Mon 23 … Fri 27, Sat 28, Sun 29, Mon 30. Oct 2024: Fri 25, Sat 26, Sun 27 (Berlin DST ends), Mon 28.

## Always
- No new dependencies in repo files; no installs into system python. No external services except pip into the scratch venv if needed. No secrets, no real user data. Stay inside the repo and scratch dir.

## Existing tests
Tests that existed at BASE 82a43db are fixed points: don't edit, delete, skip or loosen them. You may adjust only the weekday tests added in e44795b, and only as described above.

## Done means
- black 20.8b1 `--check` passes on schedule/ and test_schedule.py (or explain why you couldn't run it)
- all findings addressed with tests; `python3 -m pytest -q` full suite green; venv suite green; mypy clean.

## Test evidence
Show each new test failing before the fix (for finding 2) / confirm tz tests actually execute in the venv (not skipped).

## Report
Commit only your files: `git add schedule/__init__.py test_schedule.py && git commit -m "Fix round 1: black, reject unit before .weekday, tz tests"`. Never `git add -A`. Then `git status --porcelain`.
Write the full report to <repo>/.orchestrator/fix-1-report.md (files, RED/GREEN, full-suite tails for system python + venv + mypy + black, deviations, noticed).
Reply with ONLY (under 15 lines):
STATUS: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
Commits:
Tests: <system> / <venv> / mypy / black
Concerns / blocker / question:
Unspecified inputs:
Decisions / deviations:
Report: <path>
```

### Reply

```text
STATUS: DONE_WITH_CONCERNS
Commits: 5d9f00e "Fix round 1: black, reject unit before .weekday, tz tests"
Tests: system 49 passed/43 skipped / venv 92 passed / mypy could not run (see concern) / black clean (0.20.8b1, "2 files would be left unchanged")
Concerns / blocker / question: scratch venv's mypy (2.3.1) is broken independent of this change — imports `pathspec.patterns.gitignore` which doesn't exist in any installable pathspec version (mypy wants `pathspec>=1.0.0`, no such release exists); confirmed the traceback fails before mypy ever inspects `schedule/`. Restored venv's pathspec back to 0.12.1 afterward. Source diff is a small `if`/`raise` reusing existing types, so risk is low but unverified by mypy.
Unspecified inputs: none
Decisions / deviations: `every().monday.weekday...` test already wrapped the full chain in assertRaises, needed no widening. Computed finding-3 tz/DST expected values by running the actual library code with pytz rather than the brief's example arithmetic.
Report: <workspace>/pilot-results/schedule-weekday/hierarchy/run-2/repo/.orchestrator/fix-1-report.md
```

## 4. orch-rechecker: Scoped recheck fix round 1

### Brief

```text
You are an independent verifier doing a scoped re-check. A previous verification raised the findings below; a fix was applied. You didn't write the fix. Treat claims that it works as unverified.

Read-only on tracked files; scratch goes in <SCRATCH>. You do not dispatch subagents.

## Repo
<workspace>/pilot-results/schedule-weekday/hierarchy/run-2/repo. Fix diff: <repo>/.orchestrator/fix-1.patch (e44795b..5d9f00e). Full change since BASE 82a43db: <repo>/.orchestrator/diff-2.patch.
<SCRATCH> = <workspace> — has `venv` with pytz, black 20.8b1, and mypy (a worker reported mypy there crashes on a pathspec import; if so, try to get a working mypy in a NEW venv under <SCRATCH> e.g. `python3 -m venv <SCRATCH>/venv2 && <SCRATCH>/venv2/bin/pip install mypy types-pytz pytz`; never install into system python).

## Commands
- tests: `python3 -m pytest -q` (pytz-less; skips expected) and `<SCRATCH>/venv/bin/python -m pytest -q` (with pytz)
- lint: `<SCRATCH>/venv/bin/python -m black --check schedule test_schedule.py` (black 20.8b1, as CI's `tox -e format`); typecheck: `python -m mypy -p schedule` in a working venv
- clean-room: n/a

## Previous findings (verbatim)
1. should-fix `schedule/__init__.py:305` — fails CI formatting job (`black==20.8b1 --check .`): 105-char `unit = "weekday" if self.weekdays_only else (...)` line in `__repr__` must be split.
2. should-fix `schedule/__init__.py:463-471` + `:725` — unit set BEFORE `.weekday` is silently accepted: `every().hour.weekday.do(j)`, `every().minutes.weekday`, `every().second.weekday`, `every().week.weekday` became once-a-day weekday jobs with no error. Ruling says combining `.weekday` with another unit or named day fails loudly with ScheduleValueError.
3. nit `test_schedule.py` — no test pins "weekday judged in the at() timezone" or a DST change over a weekend.

## Must still hold
- AC1: `every().weekday.at("09:00").do(job)` next_run: Mon 2024-09-23 08:00 → 09-23 09:00; Mon 09:30 → Tue 09-24 09:00; Fri 09-27 08:00 → 09-27 09:00; Fri 09:00 exactly → Mon 09-30 09:00; Fri 09:30 → Mon 09-30; Sat 09-28 08:00 → Mon 09-30 09:00; Sun 09-29 23:59 → Mon 09-30 09:00
- AC2: run_pending over a week from Mon 09-23 08:00 runs on 23,24,25,26,27, then 30 at 09:00; never Sat/Sun
- AC3: `every().weekday.do(job)` (no at) Fri 14:00 → Mon 14:00; Wed 14:00 → Thu 14:00
- AC4: `every(2).weekday` → IntervalError; `.weekday.hours`, `.monday.weekday`, `.weekday.monday` → ScheduleValueError
- AC5: repr starts "Every 1 weekday at 09:00:00 do job()"; at("09:00:30") → 09:00:30
- AC6: full suite passes; no test that existed at BASE 82a43db modified
- Non-weekday jobs' repr/str byte-identical to BASE (earlier comparison script: <SCRATCH>/repr_cmp.py, outputs base_repr.txt)

## Do
1. Run tests (both), black, mypy. Paste output.
2. For each finding, reproduce the original failing case and mark ADDRESSED / NOT ADDRESSED with evidence. For 3, confirm the new tz tests actually execute (not skip) under the venv, and would fail if the weekend-skip were judged in local time instead of the at() tz (e.g. mutate a scratch copy, not the repo).
3. Read the fix diff for new breakage (e.g. `every().day.weekday` / `every().days.weekday` should still work; errors raised before a job is added to the scheduler; default `every()` jobs unaffected). A fix that edits a test that existed at BASE counts as breakage.

## Report (this structure)
### Verdict: PASS | FAIL
### Previous findings
- 1/2/3: ADDRESSED | NOT ADDRESSED — evidence
### Must still hold
- ACn: PASS | FAIL — evidence
### Test run
<verbatim tails>
### New breakage in the fix diff
- <blocker | should-fix | nit> <file:line> <what> — or "none"
### Out of scope observations (non-blocking)
- ... or "none"
```

### Reply

```text
### Verdict: PASS

### Previous findings
- 1: ADDRESSED — `schedule/__init__.py:305` (now 305-309) unit assignment split across 5 lines; `black --check` now reports "All done! 2 files would be left unchanged."
- 2: ADDRESSED — a check was added both in the `weekday` property getter (`__init__.py:474-477`, raises before `.weekday.hours`/`.weekday.monday` even complete) and in `_schedule_next_run` (`:733-736`, catches unit-before-`.weekday` cases like `every().hour.weekday`, `every().minutes.weekday`, `every().second.weekday`, `every().week.weekday`). Verified directly: `every().hour.weekday`, `.minutes.weekday`, `.second.weekday`, `.week.weekday`, `.monday.weekday` all raise `ScheduleValueError`; `every(2).weekday` still raises `IntervalError`.
- 3: ADDRESSED — `test_tz_weekday_judged_in_at_timezone` and `test_tz_weekday_dst_fallback_over_weekend` both execute (not skipped) under the pytz venv (`-k` run: "2 passed"). Built a scratch mutant (moved the weekend-skip loop to run after the local-timezone conversion instead of in the at()-timezone) and reran: `test_tz_weekday_judged_in_at_timezone` fails under the mutation (`AssertionError: MockDate(2024,9,27,23,0) == MockDate(2024,9,29,22,0)`), proving the test genuinely pins tz-judged weekend-skip rather than trivially passing.

### Must still hold
- AC1: PASS — all 7 next_run cases match exactly (verified via scratch script against the live repo).
- AC2: PASS — run_pending simulation Mon 09-23 08:00 → Sun 10-01 fires only on 23,24,25,26,27,30, all at 09:00, no Sat/Sun.
- AC3: PASS — Fri 2024-09-27 14:00 → 2024-09-30 14:00 (Mon); Wed 2024-09-25 14:00 → 2024-09-26 14:00 (Thu).
- AC4: PASS — `every(2).weekday` → IntervalError; `.weekday.hours.do()`, `.monday.weekday.do()`, `.weekday.monday.do()` → ScheduleValueError, and in each error case `len(scheduler.jobs)` stayed 0 (job never added).
- AC5: PASS — repr starts `"Every 1 weekday at 09:00:00 do job()"`; `.at("09:00:30")` → next_run `...09:00:30`.
- AC6: PASS — full suite: pytz-less `49 passed, 43 skipped`; pytz venv `92 passed`. `git diff 82a43db..HEAD -- test_schedule.py` shows zero removed/modified lines, only additions. Non-weekday job repr/str confirmed byte-identical to BASE via `<SCRATCH>/repr_cmp.py` (diff against `base_repr.txt`: no output).

### Test run
```
$ python3 -m pytest -q
ss.ssss..........................sss.ss...................ssssssssssssss [ 78%]
ssssssssssssssssss..                                                     [100%]
49 passed, 43 skipped in 0.12s

$ <SCRATCH>/venv/bin/python -m pytest -q
........................................................................ [ 78%]
....................                                                     [100%]
92 passed in 0.14s

$ <SCRATCH>/venv/bin/python -m black --check schedule test_schedule.py
All done! ✨ 🍰 ✨
2 files would be left unchanged.

$ <SCRATCH>/venv/bin/python -m mypy -p schedule
ModuleNotFoundError: No module named 'pathspec.patterns.gitignore'   (confirmed broken, as flagged)

$ <SCRATCH>/venv2/bin/python -m mypy -p schedule   (fresh venv: mypy, types-pytz, pytz)
Success: no issues found in 1 source file
```

### New breakage in the fix diff
none — full diff since BASE 82a43db touches only `docs/examples.rst` (+1), `schedule/__init__.py` (+38/-2), `test_schedule.py` (+234), all additive; `every().day.weekday` / `every().days.weekday` still work (verified: next_run correct for both); default `every()` / non-weekday job reprs are byte-identical to BASE; the `ScheduleValueError` in both the getter and `_schedule_next_run` fires before `self.scheduler.jobs.append(self)`, so no job is added to the scheduler on error.

### Out of scope observations (non-blocking)
- A few pre-existing lines (docstrings/error-message strings, e.g. `__init__.py:774`, `:801`) exceed 88 chars but are string/comment content that black legitimately leaves alone — not something the fix introduced or needs to address.
```
