# Agents dispatched in schedule-weekday/hierarchy/run-1

## 1. orch-worker-haiku: T1 weekday scheduling

### Brief

```text
You are a worker on one task in a larger plan. Your deliverable is exactly the task below, with tests, and a report. Changes outside it belong in your report under "noticed", where the planner can decide on them.

You do not dispatch subagents. You do not ask the user questions — if the brief leaves something open that changes what you build, return NEEDS_CONTEXT with the question.

Work economically: every turn re-reads your whole context. Trust the repo notes below instead of exploring, read only the files you need, and chain shell commands with `&&`.

## Task
T1: Add a `weekday` property to `Job` in schedule/__init__.py so `schedule.every().weekday.at("09:00").do(job)` runs Monday–Friday at 09:00 and never on Saturday/Sunday. Add tests in test_schedule.py and one docs line.

Implementation (follow exactly):
1. In `Job.__init__`, after `self.start_day` block, add:
   ```
   # Only run on Monday to Friday. Only relevant when unit is 'days'.
   self.weekdays_only: bool = False
   ```
2. Add a property right after the `sunday` property (before `tag`):
   ```
   @property
   def weekday(self):
       """
       Schedule the job to run every weekday (Monday to Friday),
       skipping Saturdays and Sundays. Combine with :meth:`at` to
       run at a specific time, e.g. ``every().weekday.at("09:00")``.
       """
       if self.interval != 1:
           raise IntervalError(
               "Scheduling .weekday jobs is only allowed with an interval of 1. "
               "Using .weekday on a job scheduled to run every 2 or more days "
               "is not supported."
           )
       self.weekdays_only = True
       return self.days
   ```
3. In `_schedule_next_run`, directly after the existing `if self.unit not in (...)` check block, add:
   ```
   if self.weekdays_only:
       if self.unit != "days" or self.start_day is not None or self.latest is not None:
           raise ScheduleValueError(
               "`.weekday` can only be combined with a daily schedule "
               "(not with a specific day, another time unit or `.to()`)"
           )
   ```
   (let black format it). Then directly after the existing `while next_run <= now: next_run += period` loop and before `next_run = self._correct_utc_offset(...)`, add:
   ```
   if self.weekdays_only:
       # Skip Saturday (5) and Sunday (6)
       while next_run.weekday() >= 5:
           next_run += datetime.timedelta(days=1)
   ```
4. In `__repr__`, where the unit label is computed (`self.unit[:-1] if self.interval == 1 else self.unit`, used in BOTH branches), use `"weekday"` instead when `self.weekdays_only` is True. E.g. compute `unit = "weekday" if self.weekdays_only else (self.unit[:-1] if self.interval == 1 else self.unit)` once, before the `if self.at_time is not None` branch, and use it in both branches. Careful: `self.unit` can be None for a partial job (existing test `repr(schedule.every(10))` == "Every 10 None do [None] (last run: [never], next run: [never])") — keep that working (None[:-1] must not be evaluated differently than today; today with interval 10 it uses self.unit directly). `__str__` stays unchanged.
5. docs/examples.rst: in the first code block that contains `schedule.every().wednesday.at("13:15").do(job)` (~line 43), add a line `schedule.every().weekday.at("09:00").do(job)` right after it. Do not edit README.rst.

## Why
Users want Mon–Fri jobs without registering five separate `.monday`… `.friday` jobs. Misuse must raise loudly rather than silently doing something else, which is why combinations with specific days, other units or `.to()` raise.

## Context
- repo: <workspace>/pilot-results/schedule-weekday/hierarchy/run-1/repo — the main tree on branch orch/weekday; no branches or worktrees
- files you'll touch: schedule/__init__.py (the library), test_schedule.py (tests), docs/examples.rst (docs)
- file to imitate for style: test_schedule.py `test_run_every_weekday_at_specific_time_today` (~line 1427), `test_to_repr` (~line 1338)
- interfaces you must produce: `Job.weekday` (property), `Job.weekdays_only: bool` (default False)
- constraints: don't change behaviour of any existing unit/day; public API otherwise unchanged
- known failures at BASE: none (41 skipped tests are pytz-dependent and skipped; that's expected)

## Repo notes
- Library is one module: schedule/__init__.py (Scheduler, Job). Tests: test_schedule.py (unittest TestCase, run by pytest).
- Tests: `python3 -m pytest -q` → baseline 40 passed, 41 skipped (skips = "pytz unavailable"; pytz NOT installed, don't install it).
- Lint: `black --check schedule` passes at BASE. test_schedule.py already has 6 black-diff lines at BASE (tuple-unpacking `(job, tz) = ...`); check yours with `black --diff -q test_schedule.py | grep -c '^+[^+]'` → must stay 6. mypy is not installed. Do NOT run `black` in write mode on test_schedule.py (it would reformat pre-existing lines); you may run `black schedule`.
- Time is faked with the `mock_datetime(y, m, d, h, min)` context manager in test_schedule.py; local TZ is forced to Europe/Berlin at import.
- Fluent API: unit set by properties (`days`, `weeks`...); `monday`..`sunday` properties set `self.start_day` and return `self.weeks`, raising IntervalError if interval != 1.
- `Job.at()` accepts HH:MM(:SS) when `self.unit == "days"`. `_schedule_next_run()` computes next_run: now → move to at_time → `while next_run <= now: next_run += period` → `_correct_utc_offset(...)` → tz conversion.
- Dates: 2010-01-06 Wed, 07 Thu, 08 Fri, 09 Sat, 10 Sun, 11 Mon, 12 Tue.
- black at <root>/.local/bin/black (v26, py3.11).

## Always (unless this brief explicitly says otherwise)
- No new dependencies: don't install packages or edit dependency files.
- No real external services. Clean-room check: n/a: no external services.
- No secrets: don't open `.env` or credential files.
- No real user data.
- Stay inside the repo path above.

## Existing tests
Tests that existed before your task are fixed points. Don't edit, delete, skip or loosen them. Tests you may change: none (add new test methods only, inside the existing `SchedulerTests` class / the class holding `test_run_every_weekday_at_specific_time_today`). If an existing test contradicts this brief, stop and return NEEDS_CONTEXT.

## Done means
Add these tests (new methods, e.g. placed after `test_run_every_weekday_at_specific_time_past_today`). Exact expected values:
- AC1 `test_weekday_next_run`: for each (now → expected next_run) create `every().weekday.at("09:00").do(mock_job)` inside `with mock_datetime(...)` and assert `job.next_run == datetime.datetime(...)`:
  - Wed 2010-01-06 08:00 → 2010-01-06 09:00
  - Wed 2010-01-06 10:00 → 2010-01-07 09:00
  - Fri 2010-01-08 08:00 → 2010-01-08 09:00
  - Fri 2010-01-08 10:00 → 2010-01-11 09:00
  - Fri 2010-01-08 09:00 (exactly) → 2010-01-11 09:00
  - Sat 2010-01-09 08:00 → 2010-01-11 09:00
  - Sun 2010-01-10 23:59 → 2010-01-11 09:00
  - Mon 2010-01-11 08:59 → 2010-01-11 09:00
  (call `schedule.clear()` between cases, or use a fresh `schedule.Scheduler()`)
- AC2 `test_run_every_weekday_skips_weekend`: register at Fri 2010-01-08 08:00; `schedule.run_pending()` at Fri 08 09:01 → call_count 1 and `schedule.next_run()` == 2010-01-11 09:00; at Sat 09 09:01 → 1; Sun 10 09:01 → 1; Mon 11 09:01 → 2; Tue 12 09:01 → 3.
- AC3 `test_weekday_without_at`: `every().weekday.do(mock_job)`: now Thu 2010-01-07 10:30 → next_run 2010-01-08 10:30; Fri 2010-01-08 10:30 → 2010-01-11 10:30; Sat 2010-01-09 10:30 → 2010-01-11 10:30.
- AC4 `test_weekday_invalid_combinations`: `self.assertRaises(IntervalError, lambda: every(2).weekday)`; and ScheduleValueError for each of `every().weekday.monday.do(mock_job)`, `every().monday.weekday.do(mock_job)`, `every().weekday.hours.do(mock_job)`, `every().weekday.to(3).do(mock_job)`.
- AC5 in a new `test_weekday_repr`: `repr(every().weekday.at("09:00").do(job_fun))` startswith `"Every 1 weekday at 09:00:00 do job_fun() (last run: [never], next run: "`; `repr(every().weekday.do(job_fun))` startswith `"Every 1 weekday do job_fun() (last run: [never], next run: "`.
- AC6: `python3 -m pytest -q` → (40 + your new tests) passed, 41 skipped, 0 failed; `black --check schedule` passes; `black --diff -q test_schedule.py | grep -c '^+[^+]'` prints 6.
- AC7: the docs line and the docstring above.

## Test evidence
Run the new tests once before the implementation (e.g. write tests first) and confirm they fail for the right reason (AttributeError / missing weekday); then make them pass. Mention any pre-existing test that goes red.

## If you're out of your depth
Return BLOCKED with what you tried. Don't commit if you stop early; list files you left changed.

## Report
Commit only the files you changed, named one by one:
`git add schedule/__init__.py test_schedule.py docs/examples.rst && git commit -m "T1: add every().weekday for Monday-Friday jobs"`. Never `git add -A`. Then `git status --porcelain`, remove your own scratch files, list anything else still there (`.orchestrator/` is git-ignored; leave it).

Before writing the report, re-read the code next to yours (`_schedule_next_run`, `run`, `until`, `_move_to_at_time`). Note anything wrong under "Things you noticed", or write "looked, found nothing".

Write the full report to <workspace>/pilot-results/schedule-weekday/hierarchy/run-1/repo/.orchestrator/task-1-report.md:
- Files changed
- Tests added, with RED output and GREEN output
- Full-suite command and the verbatim tail of its output
- Deviations from the brief and why
- Things you noticed but didn't touch

Then reply with ONLY (under 15 lines):
STATUS: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
Commits: <hashes, or "uncommitted">
Tests: <command> → <N passed, M failed>
Concerns / blocker / question: <one or two lines, or "none">
Unspecified inputs: <for each input the brief gave no example for: one line on what your code does with it>
Decisions / deviations: <every other choice the brief didn't settle, or "none">
Report: <path>

If "Decisions / deviations" isn't "none", the status is DONE_WITH_CONCERNS.
```

### Reply

```text
STATUS: DONE
Commits: 7023bdf
Tests: `python3 -m pytest -q` → 45 passed, 41 skipped (5 new tests added)
Concerns / blocker / question: none
Unspecified inputs: none
Decisions / deviations: none
Report: `<workspace>/pilot-results/schedule-weekday/hierarchy/run-1/repo/.orchestrator/task-1-report.md`
```

## 2. orch-verifier: Verify weekday feature

### Brief

```text
You are an independent verifier. Code was written to satisfy the acceptance criteria below. You didn't write it. Treat every claim that it works, including comments and docstrings in the code, as unverified. Your job is to try to show it does NOT meet the criteria, and to say so plainly if you can't.

You are read-only on tracked files: scratch scripts go in /tmp. You do not dispatch subagents. Do not install packages (pytz is intentionally not installed).

## Repo
<workspace>/pilot-results/schedule-weekday/hierarchy/run-1/repo. Diff under review: <repo>/.orchestrator/diff-1.patch (BASE 82a43db1b938d8fdf60103bd41f329e06c8d3651, HEAD 7023bdf).

User request: "add a way to schedule a job on weekdays only: `schedule.every().weekday.at("09:00").do(job)` should run Monday to Friday at 09:00 and never on Saturday or Sunday. Add tests; the existing suite must stay green. The tests run with `python3 -m pytest -q`."

## Commands
- tests: `python3 -m pytest -q` (BASE: 40 passed, 41 skipped — skips are "pytz unavailable")
- lint: `black --check schedule` (passes at BASE); `black --diff -q test_schedule.py | grep -c '^+[^+]'` was 6 at BASE (pre-existing black-26 style diffs), must stay 6. mypy not installed.
- pre-existing failures at BASE: none
- clean-room test command: n/a: no external services
- Test harness note: test_schedule.py forces local TZ to Europe/Berlin and provides `mock_datetime(y,m,d,h,min)` to fake now. Dates: 2010-01-06 Wed … 2010-01-11 Mon.

## Acceptance criteria
- AC1: with mock time, `every().weekday.at("09:00")` next_run: Wed 2010-01-06 08:00→Wed 06 09:00; Wed 10:00→Thu 07 09:00; Fri 08 08:00→Fri 08 09:00; Fri 08 10:00→Mon 11 09:00; Fri 08 09:00 exactly→Mon 11 09:00; Sat 09 08:00→Mon 11 09:00; Sun 10 23:59→Mon 11 09:00; Mon 11 08:59→Mon 11 09:00
- AC2: run_pending simulation: job registered Fri 08 08:00; run_pending at Fri 09:01 → called once, next_run Mon 11 09:00; at Sat 09 09:01 and Sun 10 09:01 → still 1; Mon 11 09:01 → 2; Tue 12 09:01 → 3
- AC3: no at(): `every().weekday.do(job)` at Thu 07 10:30 → Fri 08 10:30; at Fri 08 10:30 → Mon 11 10:30; at Sat 09 10:30 → Mon 11 10:30
- AC4: misuse fails loudly: `every(2).weekday` → IntervalError; `every().weekday.monday.do(f)`, `every().monday.weekday.do(f)`, `every().weekday.hours.do(f)`, `every().weekday.to(3).do(f)` → ScheduleValueError
- AC5: repr(every().weekday.at("09:00").do(f)) starts "Every 1 weekday at 09:00:00 do f() (last run: [never], next run: "; without at: "Every 1 weekday do f() ..."
- AC6: `python3 -m pytest -q` → 40+N passed, 41 skipped, 0 failed; `black --check schedule` passes; test_schedule.py black-diff count stays 6
- AC7: docs: docs/examples.rst first example block lists `schedule.every().weekday.at("09:00").do(job)`; `weekday` property has a docstring
- AC8 (manual): tz-aware `every().weekday.at("09:00", "America/New_York")` picks weekdays in that tz — pytz not installed, so can't be run here

## Review focus
- Weekend skip applied in at_time_zone (tz-aware) when tz given; DST correction after skipping (reason about the code path since pytz is absent)
- exact boundary now == 09:00 Friday; midnight Sat/Sun; run() rescheduling after a Friday run; a job that runs late (e.g. run_pending first called Sat for a job due Fri)
- `until()` combined with weekday (cancel if next weekday run past deadline)
- flag interaction with other unit properties / start_day / .to(); run_all(); Scheduler instances other than the default
- existing daily/weekly jobs unaffected (flag default False); repr of partial jobs (`repr(every(10))`)

## Rulings
- Ruling: implement as unit "days" + `Job.weekdays_only: bool` flag; skip loop `while next_run.weekday() >= 5: next_run += timedelta(days=1)` after the `while next_run <= now` loop and before `_correct_utc_offset` — reuses daily at() parsing/DST handling — cost if wrong: small refactor
- Ruling: `every(n).weekday` with n != 1 → IntervalError — "every 2 weekdays" is ambiguous, matches `.monday` — cost if wrong: users wanting it get a clear error
- Ruling: weekday + start_day / non-days unit / `.to()` → ScheduleValueError at scheduling time — fail loudly over guessing — cost if wrong: a combination is rejected that someone wanted
- Ruling: without at(), weekday behaves like daily (now + 1 day) then skips weekends — natural extension — cost if wrong: minor
- Ruling: str(job) unchanged (shows unit=days); repr shows "weekday" — cost if wrong: cosmetic
- Ruling: only singular `weekday` (no `weekdays` alias), no HISTORY.rst entry — cost if wrong: trivial to add
- Ruling: weekday is judged in at_time_zone when tz given, else local time
Check the code follows each one. Behaviour that follows a ruling is not a finding. If you think a ruling itself is wrong, list it as `ruling challenged`, with why.

## Do
1. Run the tests and lint yourself. Paste the output.
2. For each criterion, check it directly — run the code with a scratch script in /tmp — and try the review-focus cases that apply.
3. Read the diff for what tests can't catch: debug leftovers, public behaviour changed outside the criteria, missing cleanup. The request's silence on something is not permission to get it wrong.
4. Check for changes the plan didn't allow: a test that existed at BASE and was edited/deleted/skipped/loosened is at least should-fix (tests allowed to change: none). Flag new dependencies, real external calls, secrets.
5. Check the new tests would actually fail against a broken implementation (e.g. temporarily-in-/tmp copy with the skip loop removed) — do NOT modify tracked files; copy the repo to /tmp if you need to mutate.

## Report (this structure)
### Verdict: PASS | FAIL
### Per criterion
- AC1: PASS | FAIL — evidence
### Test run
<verbatim tail of test + lint output>
### Findings outside the criteria
- <blocker | should-fix | nit | ruling challenged> <file:line> <what, and why it matters>
### Declined to judge
- <...> or "none"
### If FAIL: smallest change that would make it pass
```

### Reply

```text
### Verdict: PASS

### Per criterion
- **AC1: PASS.** My scratch script (`verify.py`) checked all 8 cases with `mock_datetime` and each `next_run` matched. I also tried extra boundaries and they all passed:
  - Sat 00:00, Sun 00:00, Fri 23:59 and Fri 08:59:59 → Mon 11 09:00 (or Fri 08 09:00 for the last one).
  - Mon 09:00 exactly → Tue 12 09:00.
  - `at("00:00")` from Fri 00:01 → Mon 00:00.
  - Across the Berlin DST changes (Fri 2010-03-26 → Mon 03-29 09:00; Fri 10-29 → Mon 11-01 02:30).
- **AC2: PASS.** The simulation gave the expected counts at each step: 1 on Fri, `next_run` = Mon 11 09:00, still 1 on Sat and Sun, 2 on Mon, 3 on Tue. I also ran `run_pending` every 15 minutes for two weeks (Jan 4–18). It ran exactly 10 times, all at 09:00 on Mon–Fri, never on a weekend.
- **AC3: PASS.** Thu 10:30 → Fri 08 10:30; Fri 10:30 → Mon 11 10:30; Sat 10:30 → Mon 11 10:30. Extra case: Sun 10:30 → Mon 11 10:30.
- **AC4: PASS.** `every(2).weekday` raises IntervalError. `.weekday.monday`, `.monday.weekday`, `.weekday.hours` and `.weekday.to(3)` all raise ScheduleValueError. So do `.to(3).weekday`, `.weekday.weeks`, `.weekday.minutes` and `.weekday.seconds`. No job is left in `schedule.jobs` after a rejected `.do()`.
- **AC5: PASS.** Output was `Every 1 weekday at 09:00:00 do f() (last run: [never], next run: ...` and `Every 1 weekday do f() (last run: [never], next run: ...`. For non-weekday jobs, repr and str are byte-identical between BASE and HEAD: I compared 11 expressions, including `repr(every(10))` → `Every 10 None do [None]` and `repr(every())` → TypeError, which BASE does too. `str()` of a weekday job still shows `unit=days`, as the ruling says.
- **AC6: PASS.** 45 passed and 41 skipped (N=5), 0 failed. `black --check schedule` passes. The test_schedule.py black-diff count is still 6.
- **AC7: PASS.** `docs/examples.rst:44` has `schedule.every().weekday.at("09:00").do(job)` in the first code block. `Job.weekday` has a docstring (`schedule/__init__.py:467-472`).
- **AC8 (manual): not proven without real pytz, but the evidence is strong.**
  - I wrote a small pytz stand-in backed by zoneinfo in the scratchpad (a test double on `PYTHONPATH`, nothing installed). With it, all 41 tz tests that are skipped at BASE pass on BASE (81/81), so it behaves faithfully. HEAD also passes 86/86 with it.
  - New York: Fri 10:00 NY → Mon 15:00 Berlin. This also holds across the US DST start (Mon 03-15 14:00 Berlin) and end (Mon 11-08 15:00 Berlin).
  - Pacific/Auckland: Berlin Thu 22:00 (NZ Fri 10:00) → Berlin Sun 21:00 (NZ Mon 09:00). This shows the weekday is judged in the job's timezone (`at_time_zone`), as the ruling requires. A two-week run had no NZ-Saturday or NZ-Sunday runs.
  - A mutant that judges the weekday in local time fails these checks. It passes the repo's own tests.

### Test run
```
ss.ssss.................sss.ss....................ssssssssssssssssssssss [ 83%]
ssssssss......                                                           [100%]
45 passed, 41 skipped in 0.12s
$ black --check schedule
All done! ✨ 🍰 ✨
1 file would be left unchanged.
$ black --diff -q test_schedule.py | grep -c '^+[^+]'
6
```
Diff numstat: `docs/examples.rst +1`, `schedule/__init__.py +43 -2`, `test_schedule.py +151 -0`. No existing test was edited or deleted. There are no debug leftovers, no new dependencies and no external calls. The working tree is clean.

**Do the new tests catch a broken implementation?** I ran them against mutated copies in the scratchpad:

| Mutant | Tests that fail |
|---|---|
| Skip loop removed | 3 |
| Skip loop checks only Sunday (`> 5`) | 3 |
| Skip loop moved before the `while next_run <= now` loop | 3 |
| No validation at all | 1 |
| No `.to()` check | 1 |
| No interval check | 1 |
| repr not changed | 1 |
| `weekdays_only` flag never set | 5 |
| Weekday judged in local time instead of the job's timezone | 0 (no tz weekday test exists) |
| The start_day part of the validation removed | 0 (that part never runs; see findings) |

### Findings outside the criteria
- **nit** `schedule/__init__.py:751-756`: the `or self.start_day is not None` condition never runs. `.weekday.monday` sets the unit to weeks, which the unit check catches. `.monday.weekday` is caught earlier by the existing start_day check (line 747-748). A side effect is that `every().monday.weekday.do(f)` raises with the unrelated message "`unit` should be 'weeks'" instead of the weekday message. The exception type is still right.
- **nit** `test_schedule.py`: there is no timezone test for the weekday feature. Other tz tests call `skipTest("pytz unavailable")`, and `requirements-dev.txt` lists pytz, so such a test would run in upstream CI. Without it, the "judge the weekday in the job's timezone" ruling has no test; the local-time mutant passes the whole suite.
- **nit** (needs a planner decision): a missed Friday run can execute on a Saturday. If a job is due Fri 09:00 and `run_pending` is first called Sat 10:00, the job runs on Saturday (call_count 1). `next_run` is then correctly Mon 09:00. This matches how the library handles every overdue job (a missed `.monday` job runs on Tuesday). But read literally, the user's "never on Saturday or Sunday" rules it out. If the planner reads it that way, the fix is a weekend guard in `run()` that reschedules without running.
- **nit** `docs/examples.rst:44`: the new line sits under the comment "Run job on a specific day of the week", which does not describe Mon–Fri. README.rst and docs/index.rst are unchanged; AC7 does not require them.
- **ruling challenged** (negligible, no change recommended): the ruling puts the skip loop before `_correct_utc_offset`. When a DST gap crosses midnight, the correction can move the result onto a weekend or keep a shifted time.
  - With the stand-in, Pyongyang 2018-05-04 (gap 23:30–24:00) at `at("23:45")` gave Mon 00:15 instead of 23:45.
  - Pacific/Apia, which skipped Friday 2011-12-30 entirely, gave a Saturday 09:00 run.
  - I scanned all 498 zones for 2000–2030. Only historic Friday cases like these exist (Dhaka 2009, Pyongyang 2018); there are none in current or future tzdata. Plain daily jobs share the same gap handling.

### Declined to judge
- Real-pytz behaviour for AC8. The stand-in passes BASE's whole tz suite, but it is not pytz.
- Whether a missed Friday run should be skipped rather than run late on Saturday (the third nit). That is a product-semantics call the rulings do not cover.

All scratch scripts are in `<workspace>/`: `verify.py`, `verify_tz.py`, `mutate.py`, `edge_tz.py`, `gapscan.py`, `repr_cmp.py` and the stand-in `fakepytz/pytz.py`.
```

## 3. orch-worker-sonnet: Fix round 1 weekday

### Brief

```text
You are a worker on one task in a larger plan. Your deliverable is exactly the task below, with tests, and a report. Changes outside it belong in your report under "noticed".

You do not dispatch subagents. You do not ask the user questions — if the brief leaves something open that changes what you build, return NEEDS_CONTEXT with the question.

Work economically: trust the repo notes, read only the files you need, chain shell commands with `&&`.

## Task
Fix round 1 for the `every().weekday` feature (already implemented in commit 7023bdf on this branch: `Job.weekday` property, `Job.weekdays_only` flag, a weekend-skip loop in `Job._schedule_next_run`, tests near `test_weekday_next_run` in test_schedule.py). Three findings to fix:

## Findings to fix (verbatim from the verifier)
(a) "A missed Friday run can execute on a Saturday. If a job is due Fri 09:00 and `run_pending` is first called Sat 10:00, the job runs on Saturday (call_count 1). `next_run` is then correctly Mon 09:00. ... read literally, the user's 'never on Saturday or Sunday' rules it out."
(b) "test_schedule.py: there is no timezone test for the weekday feature. ... Without it, the 'judge the weekday in the job's timezone' ruling has no test; the local-time mutant passes the whole suite."
(c) "docs/examples.rst:44: the new line sits under the comment 'Run job on a specific day of the week', which does not describe Mon–Fri."

## What to build
(a) Planner ruling: when `run_pending()` finds a `weekdays_only` job due, and the current day — judged in the job's timezone, i.e. `datetime.datetime.now(self.at_time_zone).weekday()` — is Saturday or Sunday, the job must NOT run. Instead it is rescheduled via `self._schedule_next_run()` (which lands on the next weekday at the at-time) and `last_run` stays unchanged. Implement this in `Job.should_run` (the property used only by `Scheduler.run_pending`): when `datetime.datetime.now() >= self.next_run` and `self.weekdays_only` and the job-tz weekday >= 5, call `self._schedule_next_run()` and return False. Update the should_run docstring to say so. Do NOT put it in `run()`: `run_all()` is an explicit "run everything now" and must still run weekday jobs on a weekend. Why rescheduling rather than just returning False: returning False alone leaves next_run at Fri 09:00, so the job would fire Mon 00:00 instead of Mon 09:00. First confirm with grep that `should_run` has no other callers than run_pending; if it does, return NEEDS_CONTEXT.
Exact expected behaviour (mock_datetime, local TZ Berlin; 2010-01-08 Fri, 09 Sat, 10 Sun, 11 Mon):
  - `test_weekday_overdue_friday_not_run_on_weekend`: register `every().weekday.at("09:00").do(mock_job)` at Fri 2010-01-08 08:00; `schedule.run_pending()` first at Sat 2010-01-09 10:00 → call_count 0, `job.next_run == datetime.datetime(2010, 1, 11, 9, 0)`, `job.last_run is None`; at Sun 2010-01-10 10:00 → 0; Mon 2010-01-11 08:59 → 0; Mon 2010-01-11 09:01 → 1.
  - `test_weekday_run_all_on_weekend`: registered Fri 2010-01-08 08:00; at Sat 2010-01-09 10:00 `schedule.run_all()` → call_count 1 (run_all ignores the weekday guard), then next_run == Mon 2010-01-11 09:00.
  - Existing weekday tests must still pass unchanged.
(b) Add `test_tz_weekday` following the pattern of existing tz tests (they start with `mock_datetime(..., zone=...)` / `pytz` import guarded by `self.skipTest("pytz unavailable")` — read one, e.g. `test_tz_daily_*` near line 600–700, and copy its structure). Cases (local TZ is Europe/Berlin; next_run is naive Berlin local time):
  - `every().weekday.at("09:00", "Pacific/Auckland")`: now Berlin Thu 2010-01-07 22:00 (= NZ Fri 10:00) → next_run Berlin 2010-01-10 21:00 (= NZ Mon 09:00).
  - `every().weekday.at("10:00", "America/New_York")`: now Berlin Fri 2010-01-08 17:00 (= NY Fri 11:00) → next_run Berlin 2010-01-11 16:00 (= NY Mon 10:00).
  - Also for (a) in tz: `every().weekday.at("09:00", "Pacific/Auckland")` registered at Berlin Thu 2010-01-07 20:00 (= NZ Fri 08:00, next_run Berlin Thu 21:00); `run_pending()` first at Berlin Fri 2010-01-08 12:00 (= NZ Sat 00:00) → not run, next_run Berlin 2010-01-10 21:00.
  pytz is not installed, so this test is skipped under the plain suite. To actually run it, a pytz stand-in (zoneinfo-backed, verified to pass all 41 existing tz tests) exists at <workspace>/fakepytz — run `PYTHONPATH=<that dir> python3 -m pytest -q` as an extra check and paste its tail. If an expected value above is off, re-derive it and report it as a deviation — don't tweak the implementation to match a wrong number. Do not copy the stand-in into the repo and do not install pytz.
(c) docs/examples.rst: give the `schedule.every().weekday.at("09:00").do(job)` line its own comment, a blank line then `# Run job every weekday (Monday to Friday)` above it, matching the block's style.

## Context
- repo: <workspace>/pilot-results/schedule-weekday/hierarchy/run-1/repo — main tree, branch orch/weekday; no worktrees
- files: schedule/__init__.py, test_schedule.py, docs/examples.rst
- known failures at BASE: none

## Repo notes
- Library is one module: schedule/__init__.py (Scheduler, Job). Tests: test_schedule.py.
- Tests: `python3 -m pytest -q` → currently 45 passed, 41 skipped (skips = "pytz unavailable").
- Lint: `black --check schedule` must pass. `black --diff -q test_schedule.py | grep -c '^+[^+]'` must print 6 (pre-existing diffs). Never run black in write mode on test_schedule.py. mypy not installed.
- Time faked with `mock_datetime(y, m, d, h, min, zone=...)` in test_schedule.py; local TZ forced to Europe/Berlin.
- `_schedule_next_run()`: now (in at_time_zone) → at_time → `while next_run <= now` → weekend skip (weekdays_only) → `_correct_utc_offset` → convert to naive local.

## Always
- No new dependencies, no installs, no real services, no secrets, stay in the repo (scratch files in the scratchpad dir above).

## Existing tests
Tests that existed before are fixed points, including the 5 weekday tests from 7023bdf. Don't edit, delete, skip or loosen them. Only add new tests.

## Done means
- (a),(b),(c) above; new tests fail before the fix (show RED for the overdue test) and pass after.
- `python3 -m pytest -q` → 48 passed, 42 skipped (or state the numbers), 0 failed; with the stand-in on PYTHONPATH → all passed; black checks as above.

## Report
`git add schedule/__init__.py test_schedule.py docs/examples.rst && git commit -m "fix 1: never run weekday jobs on weekends; tz test; docs"`. Never `git add -A`. Then `git status --porcelain`.
Write the full report to <repo>/.orchestrator/fix-1-report.md (files changed, RED/GREEN, suite tails, deviations, things noticed).
Then reply with ONLY (under 15 lines):
STATUS: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
Commits: <hashes>
Tests: <command> → <N passed, M failed>; with stand-in → <...>
Concerns / blocker / question: <or "none">
Unspecified inputs: <what your code does with inputs the brief gave no example for>
Decisions / deviations: <or "none">
Report: <path>
```

### Reply

```text
STATUS: DONE
Commits: 051456c
Tests: `python3 -m pytest -q` → 47 passed, 42 skipped, 0 failed; with stand-in → 89 passed, 0 failed
Concerns / blocker / question: none
Unspecified inputs: none outside brief's examples were exercised
Decisions / deviations: final count is 47/42 not the brief's guessed 48/42 (only 2 of 3 new tests run without pytz, one is properly skipped); two multi-line tz-test expressions reformatted to black's single-line style to keep the diff-count invariant at 6
Report: <workspace>/pilot-results/schedule-weekday/hierarchy/run-1/repo/.orchestrator/fix-1-report.md
```

## 4. orch-rechecker: Scoped re-check fix 1

### Brief

```text
You are an independent verifier doing a scoped re-check. A previous verification raised the findings below; a fix was applied. You didn't write the fix. Treat claims that it works as unverified.

Read-only on tracked files; scratch in /tmp or the scratchpad dir below. You do not dispatch subagents. Do not install packages.

## Repo
<workspace>/pilot-results/schedule-weekday/hierarchy/run-1/repo. Fix diff: <repo>/.orchestrator/fix-1.patch (7023bdf..051456c). Full change since BASE 82a43db: <repo>/.orchestrator/diff-2.patch.
Feature: `schedule.every().weekday.at("09:00").do(job)` runs Mon–Fri at 09:00, never on Saturday or Sunday.

## Commands
- tests: `python3 -m pytest -q` (expect 47 passed, 42 skipped; skips = pytz unavailable)
- tests with a pytz stand-in (zoneinfo-backed, passes all BASE tz tests): `PYTHONPATH=<workspace>/fakepytz python3 -m pytest -q`
- lint: `black --check schedule`; `black --diff -q test_schedule.py | grep -c '^+[^+]'` must print 6 (pre-existing)
- clean-room: n/a

## Previous findings (verbatim)
1. (a) A missed Friday run can execute on a Saturday. If a job is due Fri 09:00 and `run_pending` is first called Sat 10:00, the job runs on Saturday. Planner ruling: run_pending on a weekend (judged in the job's timezone) must not run a due weekday job; it reschedules to the next weekday at-time, last_run unchanged; `run_all()` still runs it (explicit "run everything now"). Implemented in `Job.should_run`.
2. (b) No timezone test for the weekday feature; the "judge the weekday in the job's timezone" ruling was untested (a mutant judging weekday in local time passed the suite).
3. (c) docs/examples.rst: the weekday line sat under the comment "Run job on a specific day of the week".

## Must still hold
- next_run for `every().weekday.at("09:00")` (local TZ Berlin): Wed 2010-01-06 08:00→Wed 09:00; Wed 10:00→Thu 07 09:00; Fri 08 10:00→Mon 11 09:00; Fri 09:00 exactly→Mon 11 09:00; Sat/Sun→Mon 11 09:00
- normal Mon–Fri runs via run_pending happen exactly once per weekday at 09:00 (e.g. two-week simulation, run_pending every 15 min → 10 runs, none at weekend)
- misuse → IntervalError / ScheduleValueError (every(2).weekday; weekday+monday either order; weekday.hours; weekday.to(3))
- repr "Every 1 weekday at 09:00:00 do f() ..."; non-weekday jobs' behaviour unchanged vs BASE (should_run now has new code — confirm plain daily/weekly/interval jobs behave identically, including should_run for jobs with weekdays_only False)
- existing tests at BASE and the 5 weekday tests from 7023bdf are unmodified

## Do
1. Run tests (both variants) and lint. Paste output.
2. For each finding, reproduce the original failing case and mark ADDRESSED or NOT ADDRESSED with evidence. For (b), confirm the new tz test fails against a mutant that judges weekday in local time (mutate a copy outside the repo, run with the stand-in).
3. Read the fix diff for new breakage. Probe: should_run side effect (rescheduling inside a property) — is it called anywhere besides run_pending (get_next_run, idle_seconds, other schedulers)? `until()` deadline combined with the weekend reschedule (job past its deadline on a weekend: does it get cancelled eventually and not run?); a job due Fri 23:59 checked Sat 00:00; tz job where local day is weekday but job-tz day is weekend and vice versa; run_all on weekend.

## Report (this structure)
### Verdict: PASS | FAIL
### Previous findings
- 1: ADDRESSED | NOT ADDRESSED — evidence
### Must still hold
- <criterion>: PASS | FAIL — evidence
### Test run
<verbatim tail>
### New breakage in the fix diff
- <blocker | should-fix | nit> <file:line> <what> — or "none"
### Out of scope observations (non-blocking)
- ... or "none"
```

### Reply

```text
### Verdict: PASS

### Previous findings
- 1 (weekend run of missed Friday job): ADDRESSED — reproduced the original bug at commit `7023bdf` (pre-fix): `every().weekday.at("09:00")` created Fri 08:00, checked Sat 10:00 → `call_count on Saturday: 1` (job ran). At the current fix (`051456c`), the identical scenario yields `call_count == 0`, `next_run` rescheduled to Mon 09:00, `last_run` still `None`; confirmed with the repo's own `test_weekday_overdue_friday_not_run_on_weekend`. `run_all()` still runs it explicitly (`test_weekday_run_all_on_weekend`, and reproduced independently: `run_all` on Saturday → `call_count == 1`).
- 2 (no tz test for weekday; untested "judge weekday in job's own tz" ruling): ADDRESSED — `test_tz_weekday` added, and I built a mutant (`datetime.datetime.now(self.at_time_zone).weekday()` → `datetime.datetime.now().weekday()`, i.e. judge in local time) in a scratch copy; it fails the new test (`AssertionError: assert 1 == 0` on the Auckland Fri-due/Sat-checked case). Also independently verified both directions of tz/local-day mismatch: local=Sunday(weekend)/job-tz=Monday(weekday) → runs; local=Monday(weekday)/job-tz=Sunday(weekend) → does not run.
- 3 (docs comment misplaced): ADDRESSED — `docs/examples.rst` now has its own `# Run job every weekday (Monday to Friday)` comment above the `schedule.every().weekday.at("09:00").do(job)` line, separated from the "specific day of the week" comment.

### Must still hold
- next_run table (Berlin local): PASS — all 6 cases (Wed 08:00→Wed09, Wed10:00→Thu09, Fri10:00→Mon09, Fri09:00 exact→Mon09, Sat→Mon09, Sun→Mon09) verified by direct script.
- Two-week run_pending simulation (every 15 min): PASS — `total calls: 10 weekend_runs: 0`.
- Misuse errors: PASS — `every(2).weekday` → `IntervalError`; `weekday.monday.do()`, `monday.weekday.do()`, `weekday.hours.do()`, `weekday.to(3).do()` all → `ScheduleValueError` (raised lazily at `.do()`, as designed — `IntervalError` is itself a `ScheduleValueError` subclass, matching the "either" allowance).
- repr: PASS — `Every 1 weekday at 09:00:00 do <lambda>() (last run: [never], next run: ...)`; `test_weekday_repr` also checks the no-`.at()` form.
- Non-weekday jobs unaffected: PASS — new `should_run` logic is fully gated behind `self.weekdays_only` (default `False`); full suite (89 tests with the tz stand-in, 47/42-skip without) passes unchanged from BASE behavior.
- Existing tests at BASE / 5 weekday tests from `7023bdf` unmodified: PASS — `git diff 7023bdf 051456c -- test_schedule.py` is pure addition (new tests only), no existing lines touched.

### Test run
```
$ python3 -m pytest -q
47 passed, 42 skipped in 0.15s

$ PYTHONPATH=.../fakepytz python3 -m pytest -q
89 passed in 0.12s

$ black --check schedule
All done! ✨ 🍰 ✨
1 file would be left unchanged.

$ black --diff -q test_schedule.py | grep -c '^+[^+]'
6
```

### New breakage in the fix diff
- none (blocker/should-fix). Reviewed all touched code: `should_run` (schedule/__init__.py:691-710), `_schedule_next_run` weekday skip (764-788), `weekday` property (466-480), repr `unit` computation (300-320). `should_run` is called only from `Scheduler.run_pending` (schedule/__init__.py:99) — not from `get_next_run`/`idle_seconds`/anywhere else — so the reschedule side-effect inside the property fires exactly once per `run_pending()` call per job, with no double-evaluation (the generator is consumed once by `sorted()`).
- nit: `until()` + weekend interaction (schedule/__init__.py:701-710 vs 873-874) — a weekday job whose deadline (`cancel_after`) has already passed is *not* cancelled immediately when the weekend check reschedules it in `should_run`; it stays in the job list through the whole weekend and is only actually cancelled when `run()` is invoked and `_is_overdue` fires on the next weekday attempt. Verified: created Fri 08:00 with `.until("2010-01-08 23:59")`, checked Sat/Sun (job present, `call_count==0`, `next_run` pushed to Monday), then checked Monday 09:01 → job runs `_is_overdue` check, cancelled without ever calling `job_func` (`call_count` stays 0, job removed from `default_scheduler.jobs`). Net effect is still correct (job function never runs past its deadline), just a one-weekday-cycle delay in list cleanup — not a correctness bug against the stated ruling, which only specifies `run_pending` must not run the job and must reschedule.

### Out of scope observations (non-blocking)
- `.hours.weekday` (order not in the required misuse list) ends up with `unit="days"` because the `weekday` property's `return self.days` overrides any unit set before it — untested combination, behaves like plain `.weekday` rather than raising. Not required by the brief's misuse list (`every(2).weekday`, `weekday+monday` either order, `weekday.hours`, `weekday.to(3)`), all of which do behave correctly.
```
