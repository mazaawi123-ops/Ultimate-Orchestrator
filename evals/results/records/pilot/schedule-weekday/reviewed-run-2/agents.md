# Agents dispatched in schedule-weekday/reviewed/run-2

## 1. orch-verifier: Independent review of weekday feature

### Brief

```text
You are an independent reviewer. Someone else wrote a change; check whether it does what the
user asked, without breaking what already worked. Treat claims in comments, commit messages
and docstrings as unverified.

Don't edit tracked files: put scratch scripts in /tmp. Don't delegate.

## The user's request (verbatim)
In this repo (schedule), add a way to schedule a job on weekdays only: `schedule.every().weekday.at("09:00").do(job)` should run Monday to Friday at 09:00 and never on Saturday or Sunday. Add tests; the existing suite must stay green. The tests run with `python3 -m pytest -q`.

(Context for this run: no one is available to answer questions until you finish, so make sensible calls, record them, and carry on. Keep any plan, notes or report files you create; don't delete them at the end.)

## Candidate
Repo <workspace>/pilot-results/schedule-weekday/reviewed/run-2/repo, candidate d6a80462088ed16d00e2567b50e4e3365e43bbb8 on branch orch/weekday. Patch: <workspace>/pilot-results/schedule-weekday/reviewed/run-2/repo/.orchestrator/review/candidate-d6a80462088e.patch
(BASE 82a43db1b938d8fdf60103bd41f329e06c8d3651..candidate).

## Contracts to preserve
- Existing Job API in schedule/__init__.py: time-unit properties (.second … .weeks), named-day properties (.monday … .sunday), at() validation and parsing, to(), until(), do(), run(), _schedule_next_run() including timezone/DST handling via pytz (_correct_utc_offset).
- Scheduler.run_pending / run_all / get_next_run / idle_seconds semantics.
- Job.__str__ and existing Job.__repr__ formats for non-weekday jobs.
- Existing tests in test_schedule.py must be unchanged and pass.

## Acceptance criteria (the main session's reading of the request)
- C1: `schedule.every().weekday.at("09:00").do(job)` computes next_run as the next Mon–Fri at 09:00 from any starting day/time.
- C2: Polling run_pending regularly over several weeks runs the job exactly once per weekday at 09:00 and never on Sat/Sun.
- C3: A late run first picked up on a Sat/Sun (e.g. Friday's run missed, scheduler polled Saturday) does not execute on the weekend and is rescheduled to Monday; a late run on a weekday still executes.
- C4: Invalid combinations give a clear error and no job is added: every(2).weekday (IntervalError); .weekday combined with a named day, a non-day unit, or .to() (ScheduleValueError); bad at() formats.
- C5: repr reads "Every weekday at 09:00:00 do ...".
- C6: Existing suite unchanged and green with `python3 -m pytest -q`.
- C7: With a timezone (`.at("09:00", "Pacific/Auckland")`), weekends are judged in that timezone.
Where a criterion misses or contradicts the request, say so: the request is the reference.

## Decisions the main session made (decisions, not facts)
- Decision: `.weekday` is a property (like `.monday`) that sets `weekdays_only=True` and unit `days`; interval must be 1 — mirrors the existing API.
- Decision: a missed run first picked up on Sat/Sun is skipped (not run late) and rescheduled to Monday; this also applies to run_all() on a weekend — reading "never on Saturday or Sunday" strictly.
- Decision: `every().weekday.do(job)` without .at() runs each weekday at the time of scheduling, like every().day.
- Decision: combining .weekday with a named day, a non-day unit, or .to() raises ScheduleValueError rather than guessing.
- Decision: with tz, Mon–Fri is judged in the at() timezone.
- Decision: docs example line added to README.rst, docs/index.rst, docs/examples.rst; no HISTORY entry.
Check the code follows each one. If a decision looks wrong against the request or a contract,
report it as a finding.

## Commands
- tests: python3 -m pytest -q   lint: none installed (black/mypy are dev deps but not installed in the system Python)   offline run: n/a
- pytz is not installed in the system Python, so 41 existing tz tests (and the new tz test) skip. A scratchpad venv with pytest+pytz exists: <workspace>/venv/bin/python — use it to run the tz tests (`<venv python> -m pytest -q`).
- known failures at BASE: none (41 skipped for pytz)

## Do
1. Run the tests and lint. Report the output tail.
2. Check each criterion directly, by running the code, and try the edge cases the request
   implies.
3. Read the patch for what tests miss: changed public behaviour, error paths, data silently
   dropped or coerced, edits to existing tests or test configuration, secrets, new
   dependencies or network calls.

## Findings
Each finding needs:
- the requirement or contract it violates
- the location (file:line)
- a reproduction, or specific source evidence
- the practical impact, and the smallest justified correction

Classify each as **blocking** (the change is wrong or unsafe to deliver), **optional
improvement**, or **observation**. Match the severity to the impact; don't pad or merge
findings. A clean review, with no findings, is a valid and useful result.

## Report
### Verdict: PASS | FAIL (FAIL only for a blocking finding or a failed criterion)
### Criteria: C1 PASS | FAIL | NOT CHECKED — evidence
### Test run: <tail>
### Findings: <each, as above, or "none">
### Not verified: <anything you couldn't check, and why, or "none">
```

### Reply

```text
### Verdict: PASS

The feature works as asked. `every().weekday.at("09:00")` runs Monday to Friday at 09:00 and never on Saturday or Sunday. All seven criteria pass when I run them directly, and both test runs are green. There is one thing worth fixing before delivery that isn't a behaviour bug: the patch fails the repo's own CI formatting check (finding 1).

### Criteria
- **C1 PASS.** I scheduled the job every 10 minutes across two weeks (23 Mar to 5 Apr 2026, which includes the Berlin clock change) with `at` 09:00, 00:00 and 23:59. Each `next_run` matched an independently computed "next Mon–Fri at that time, strictly after now". 0 mismatches.
- **C2 PASS.** I ran five weeks starting on a Wednesday, calling `run_pending` every 1, 7 or 60 minutes. Each run gave 25 runs: none on a weekend, no weekday run twice, none missing. The latest run was 0, 5 and 17 minutes after 09:00 respectively.
- **C3 PASS.**
  - Friday's run missed, then polled Saturday 12:00: 0 calls, `last_run` stays None, next run is Monday 09:00. A Sunday poll also gives 0 calls.
  - Thursday's run picked up late on Friday at 08:00 still runs, and the next run becomes Friday 09:00.
  - `run_all()` on a Saturday runs a plain daily job but skips the weekday job and moves it to Monday. This matches your decision.
- **C4 PASS.** No job was added in any case.
  - `every(2).weekday` and `every(0).weekday` raise IntervalError.
  - `.weekday` combined with `.monday`, `.saturday`, `.hours`, `.hour.at(":30")`, `.minutes`, `.seconds`, `.weeks`, `.week`, `.to(3)` before it or `.to(3)` after it raises ScheduleValueError.
  - Bad `at()` strings ("9:00", ":30", "24:00", "09:60") raise ScheduleValueError, and `at(900)` raises TypeError.
  - The equivalent valid forms (`.day.weekday`, `.weekday.days`, `.day.at(..).weekday`) all work.
- **C5 PASS.** repr reads `Every weekday at 09:00:00 do my_job(1, y=3) (last run: [never], next run: 2026-09-21 09:00:00)`. repr for day, weekly, `to()` jobs and `__str__` are unchanged.
- **C6 PASS.** `test_schedule.py` only gains lines (+163/−0), and no test configuration changed.
- **C7 PASS** (checked with the pytz venv):
  - I ran 40 scenarios. The server clock was Berlin, Auckland, UTC or New York. The job timezone was Auckland, New York, Berlin, Kiritimati, Pago Pago, Chatham or Cairo. The windows were 6–8 weeks covering the spring and autumn clock changes of each.
  - Every scenario had runs exactly equal to the expected weekdays in the job's timezone: 0 weekend runs, 0 missing, 0 duplicated.
  - Cairo changes its clocks on a weekday. Around 24 Apr and 29 Oct 2026, the weekday job's runs matched the daily job's runs with Saturdays and Sundays removed.

### Test run
```
$ python3 -m pytest -q
50 passed, 42 skipped, 10 subtests passed in 0.17s      (41 existing pytz skips + new test_tz_weekday)
$ <venv>/bin/python -m pytest -q
92 passed, 10 subtests passed in 0.19s
mypy -p schedule (scratch venv): Success: no issues found in 1 source file
sphinx-build -W (tox docs env equivalent, output outside repo): exit 0
black==20.8b1 --check . (repo-pinned, CI "formatting" job): BASE clean; candidate "2 files would be reformatted"
```

### Findings

**1. Optional improvement: the patch fails the repo's CI formatting check**
- **Contract:** don't break what already worked. `.github/workflows/ci.yml` runs `tox -e format`, which runs `black --check .` with `black==20.8b1` from `requirements-dev.txt`. That check passes at BASE (4 files unchanged) and fails at the candidate.
- **Locations:**
  - `schedule/__init__.py:715-717`: black joins the condition onto one line of exactly 88 characters:
    ```
    if self.weekdays_only and _is_weekend(datetime.datetime.now(self.at_time_zone)):
    ```
  - `test_schedule.py:1555-1557`: black re-wraps the `until(...)` chain in `test_weekday_until`.
- **Reproduction:** I installed `black==20.8b1 click==8.0.4` in a scratch venv and ran `black --check .` on a `git archive` of each commit.
- **Impact:** the PR's formatting job goes red. There is no effect on behaviour.
- **Fix:** run `black==20.8b1` on those two files. I rated this optional rather than blocking because your stated gate, `python3 -m pytest -q`, is green.

**2. Optional improvement: skipping on a weekend ignores the `until()` deadline**
- **Contract:** the `until()` behaviour in `run()`. After a normal run, `run()` returns CancelJob once the next run falls past `cancel_after`.
- **Location:** `schedule/__init__.py:715-722`. The weekend-skip branch calls `_schedule_next_run()` and returns None without the same deadline check.
- **Reproduction:**
  1. On Friday 08:00, schedule `every().weekday.at("09:00").until(Sun 12:00)`.
  2. Don't poll on Friday.
  3. Call `run_pending` on Saturday 12:00. The job is still in `schedule.jobs`, `next_run` is Monday 09:00 and `idle_seconds()` is 162000.0.
  4. On Monday it is cancelled without running.
- **Impact:** the job never runs past its deadline. But over the weekend, `next_run()` and `idle_seconds()` report a Monday run that will never happen. The code that already existed has a similar lingering case at `do()` time, so this is low impact.
- **Fix:** after the `_schedule_next_run()` on line 721, add `if self._is_overdue(self.next_run): return CancelJob`.

**3. Observation: one error message doesn't mention `.weekday`**
- **Location:** `schedule/__init__.py:755-756`.
- **Evidence:** `every().weekday.hours.do(job)` raises `` `unit` should be 'days' `` without mentioning `.weekday`. It copies the existing `` `unit` should be 'weeks' `` message. C4 asks for a "clear error", and this one is adequate but could be clearer.
- **Fix:** something like "Cannot combine .weekday with a unit other than days".

**Your decisions**
The code follows each one:
- `.weekday` is a property that requires an interval of 1 and sets the unit to days.
- A late run is skipped on Saturday or Sunday, including under `run_all()`.
- Without `.at()`, the job uses the time it was scheduled at: Friday 10:30 gives Monday 10:30.
- `.weekday` combined with a named day, a non-day unit or `.to()` raises ScheduleValueError.
- With a timezone, weekends are judged in the `at()` timezone.
- The example line is in all three docs files, with no HISTORY entry.

One consequence of the late-run rule, which matches how `every().day` already behaves: if Friday's run is first polled at Monday 08:00, it runs late then, and runs again at Monday 09:00.

There are no new dependencies, network calls or secrets, and nothing changed in test configuration. `.orchestrator/` is excluded through `.git/info/exclude`, and the working tree was clean after my checks.

### Not verified
- **Python 3.7–3.10 and 3.12 from the tox matrix:** I only ran 3.11. I saw no syntax newer than 3.7 in the patch.
- **Real clock:** I didn't run against the real clock. All runtime checks used the test suite's `mock_datetime`.

My check scripts are in `<workspace>/review/`:
- `check_c1_c2.py`
- `check_c3_c5.py`
- `check_c7.py`
- `check_c7_cairo.py`
```

## 2. orch-rechecker: Re-check weekday repair

### Brief

```text
You are an independent reviewer re-checking a repair. Don't edit tracked files; don't
delegate. Put scratch files in <workspace>/recheck/.

Request (verbatim): In this repo (schedule), add a way to schedule a job on weekdays only: `schedule.every().weekday.at("09:00").do(job)` should run Monday to Friday at 09:00 and never on Saturday or Sunday. Add tests; the existing suite must stay green. The tests run with `python3 -m pytest -q`.

Repo: <workspace>/pilot-results/schedule-weekday/reviewed/run-2/repo (branch orch/weekday)
Candidate: 8e0fcec579c23131ba4405d97f181f794534304b, patch <workspace>/pilot-results/schedule-weekday/reviewed/run-2/repo/.orchestrator/review/candidate-8e0fcec579c2.patch (BASE 82a43db..candidate); the previous candidate was d6a80462088ed16d00e2567b50e4e3365e43bbb8 (`git diff d6a8046 8e0fcec` shows the repair only).

Tools available: system python3 has no pytz (41 existing tz tests + 1 new skip). Venv with pytest+pytz: <workspace>/venv/bin/python. Pinned black 20.8b1: <workspace>/black20/bin/black (CI runs `black --check .`).

Findings the repair addresses (verbatim from the previous review):
1. Optional improvement: the patch fails the repo's CI formatting check. `.github/workflows/ci.yml` runs `tox -e format` → `black --check .` with `black==20.8b1`. Passes at BASE, fails at candidate: `schedule/__init__.py:715-717` (black wants the condition on one 88-char line) and `test_schedule.py:1555-1557` (`until(...)` chain in `test_weekday_until`). Fix: run black 20.8b1 on those files.
2. Optional improvement: skipping on a weekend ignores the `until()` deadline. `schedule/__init__.py:715-722`: the weekend-skip branch calls `_schedule_next_run()` and returns None without the deadline check that the normal path in run() has. Repro: Friday 08:00, schedule `every().weekday.at("09:00").until(Sun 12:00)`, don't poll Friday, `run_pending` Saturday 12:00 → job still in `schedule.jobs`, next_run Monday 09:00, idle_seconds 162000. Fix: after `_schedule_next_run()`, `if self._is_overdue(self.next_run): return CancelJob`.
3. Observation: `every().weekday.hours.do(job)` raises "`unit` should be 'days'" without mentioning .weekday (schedule/__init__.py:755-756). Fix: something like "Cannot combine .weekday with a unit other than days".

Do:
1. Run the tests (`python3 -m pytest -q` and the venv python), and `black --check .` with the pinned black.
2. Reproduce each finding's original failure against the new candidate, and mark it ADDRESSED or NOT ADDRESSED, with
   evidence. "Attempted" is not addressed.
3. Probe the behaviour next to each fix: a fix that moves one boundary often breaks another (e.g. weekend skip with until() deadline after Monday, deadline equal to next run, run_all on a weekend with until, tz jobs).

Report: Verdict PASS | FAIL; each finding ADDRESSED | NOT ADDRESSED with evidence; any new
blocking finding (requirement/contract violated, file:line, reproduction, impact, smallest fix); what you couldn't verify.
```

### Reply

```text
All 18 weekday-related tests (including tz variants) pass. No tracked files were modified during this review (confirmed via `git status` clean earlier). Final verification complete.

## Report

**Verdict: PASS**

### Test / lint runs
- `python3 -m pytest -q` (system, no pytz): `51 passed, 42 skipped, 10 subtests passed`
- venv `python -m pytest -q` (with pytz): `93 passed, 10 subtests passed` — includes `test_tz_weekday` and all 18 weekday-related tests (`-k weekday`)
- pinned black 20.8b1 `black --check .`: `All done! ✨ 🍰 ✨ 4 files would be left unchanged.`
- `git status` on the repo remained clean throughout (no tracked files modified by this review)

### Findings from the previous review

**1. Black formatting — ADDRESSED.** `black --check .` now passes cleanly with the pinned 20.8b1 binary; diff shows `schedule/__init__.py:715` collapsed to one line and the `until(...).do(...)` chain in `test_weekday_until` (`test_schedule.py:1552-1557`) reformatted to black's style.

**2. Weekend-skip ignoring `until()` deadline — ADDRESSED.** Reproduced the exact scenario from the finding: scheduled Friday 08:00 with `every().weekday.at("09:00").until(2010-01-10 12:00)`, did not poll Friday, then `run_pending()` on Saturday 12:00.
  - Before fix: job survived with `next_run` = Monday 09:00 (past the Sunday-noon deadline).
  - After fix: `len(schedule.jobs) == 0`, `call_count == 0` — job is correctly cancelled on the weekend-skip path, matching the new `if self._is_overdue(self.next_run): return CancelJob` at `schedule/__init__.py:720-722`.
  - The candidate also added `test_weekday_until_after_weekend_skip` covering this exact case, and it passes.

**3. Unhelpful error message for `.weekday` + non-`days` unit — ADDRESSED.** `every().weekday.hours.do(job)` now raises `ScheduleValueError("Cannot combine .weekday with a unit other than days")`, explicitly naming `.weekday` (`schedule/__init__.py:757`).

### Boundary probes (per the brief's "probe next to the fix")
Ran targeted scenarios against the candidate (scratch scripts, not committed):
- **Weekend skip with deadline after the next Monday**: job correctly survives uncancelled, reschedules to Monday 09:00, not run. Consistent with intended behavior.
- **Deadline exactly equal to the computed `next_run`** (Monday 09:00 == until Monday 09:00): job survives (not cancelled), because `_is_overdue` uses strict `>`. This matches the existing (pre-existing, unchanged) boundary semantics used identically in the normal run path (`schedule/__init__.py:730`), so it is not a regression introduced by this patch — just the pre-existing `>` vs `>=` convention applied consistently.
- **`run_all()` on a weekend with an expired deadline**: goes through the same `Job.run()` path via `_run_job`, and correctly cancels the job (0 jobs remaining), showing the fix applies uniformly to both `run_pending()` and `run_all()`.
- **Normal Mon–Fri weekday cadence sanity check**: runs Friday 09:00, skips Saturday, skips Sunday (no `until()`, job just reschedules without cancelling), runs again Monday 09:00 — call_count progresses 1 → 1 → 2 as expected.
- **tz-aware weekday jobs**: `test_tz_weekday` and the full set of 18 weekday tests pass under the pytz-enabled venv; `next_run` is stored as naive local time consistently with `cancel_after` (also naive from `until()`), so the new `_is_overdue(self.next_run)` comparison at the weekend-skip site is not mixing aware/naive datetimes.

No new blocking finding surfaced. The diff (`git diff d6a8046 8e0fcec`) is scoped exactly to the three items above — two lines of formatting fix, the new overdue check plus its test, and the error-message change — with no unrelated changes.

### What I could not verify
- Did not test DST-transition edge cases specifically combined with the weekend-skip-plus-`until()` path (e.g., a `.weekday.at(...)` job with `at_time_zone` set, deadline falling inside a DST gap on the skipped weekend day). The existing `test_tz_weekday` test does not appear to exercise `until()` together with a weekend skip, so this combination remains unexercised by the suite; low risk given the naive-datetime handling is unchanged from the pre-existing `_correct_utc_offset`/`next_run` normalization logic, but not directly probed.

### Relevant paths
- Repo: `<workspace>/pilot-results/schedule-weekday/reviewed/run-2/repo`
- Patch under review: `schedule/__init__.py` (lines ~715-722, ~757), `test_schedule.py` (lines ~1552-1571)
- Candidate patch file: `<workspace>/pilot-results/schedule-weekday/reviewed/run-2/repo/.orchestrator/review/candidate-8e0fcec579c2.patch`
- Scratch repro/probe scripts (not committed): `<workspace>/recheck/repro2.py` and `.../recheck/probe.py`
```
