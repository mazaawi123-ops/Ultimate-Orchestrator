# Agents dispatched in schedule-weekday-reviewed/release/run-1

## 1. orch-verifier: Independent review of weekday candidate

### Brief

```text
You are an independent reviewer. Someone else wrote a change; check whether it does what the
user asked, without breaking what already worked. Treat claims in comments, commit messages
and docstrings as unverified.

Don't edit tracked files: put scratch scripts in /tmp. Don't install anything into the shared
environment; use a throwaway one under /tmp, or list the check under Not verified. Don't
delegate.

## The user's request (verbatim)
In this repo (schedule), add a way to schedule a job on weekdays only: `schedule.every().weekday.at("09:00").do(job)` should run Monday to Friday at 09:00 and never on Saturday or Sunday. Add tests; the existing suite must stay green. The tests run with `python3 -m pytest -q`.

(Context for this run: no one is available to answer questions until you finish, so make sensible calls, record them, and carry on. Keep any plan, notes or report files you create; don't delete them at the end.)
Use the code-orchestrator skill in Reviewed mode (you build; one independent review).

## Candidate
Repo <workspace>/release-results-final/schedule-weekday-reviewed/release/run-1/repo, candidate eb86cc7bd58d679c33f49fec2fc8c7410e550246 on branch orch/weekday. Patch: .orchestrator/review/candidate-eb86cc7bd58d.patch (BASE 82a43db1b938..candidate).

## Contracts to preserve
- Existing fluent API in schedule/__init__.py (Job.day/days, monday..sunday, at, until, to, tag, do) and its validation errors.
- repr/str formats for non-weekday jobs (tested in test_to_repr / test_to_string).
- Job.next_run stays a naive datetime in local time, including when at() is given a timezone.
- Scheduler.run_pending / run_all / _run_job semantics for all other jobs.

## Acceptance criteria (the main session's reading of the request)
- C1: `every().weekday` exists; unit is days; `.at("HH:MM[:SS]")` accepted with daily format rules.
- C2: next_run from any moment Mon–Sun is the next Mon–Fri 09:00 strictly after now.
- C3: Polling run_pending every 15 min over 3 weeks runs exactly 15 times, once per Mon–Fri date, at 09:00, never Sat/Sun.
- C4: A run that becomes due/late on Sat/Sun (missed Friday, or run_all on the weekend) does not execute; it is rescheduled to Monday; until() is still honoured.
- C5: With `.at(time, tz)`, the weekday is judged in the job's timezone.
- C6: `every(2).weekday` → IntervalError; weekday combined with hours/minutes/weeks/a named day → ScheduleValueError at do().
- C7: Existing suite green: `python3 -m pytest -q` (no pytz installed system-wide) and with pytz; black 20.8b1 --check; mypy -p schedule; sphinx -W docs build.
Where a criterion misses or contradicts the request, say so: the request is the reference.

## Decisions the main session made (decisions, not facts)
- Decision: `weekday` is a property like `monday`, setting unit="days" plus a `weekdays_only` flag — mirrors the existing day-of-week API.
- Decision: "never on Saturday or Sunday" is enforced at run time too: if a weekday job is executed (run_pending when late, or run_all) while it is Sat/Sun, it is skipped and rescheduled to the next weekday, not run — because the request says "never".
- Decision: with `.at(time, tz)`, Mon–Fri is judged in that timezone (where "09:00" is meant), so next_run in local time may fall on a local Sat/Sun.
- Decision: `every(2).weekday` raises IntervalError; weekday with a non-day unit or named day raises ScheduleValueError — clear error rather than guessing.
- Decision: `every().weekday.do(job)` without at() runs each weekday at the time of scheduling (like every().day).
- Decision: repr is "Every weekday at 09:00:00 do job() (...)"; str() unchanged.
- Decision: docs example added to docs/examples.rst; HISTORY.rst left to maintainers.
Check the code follows each one. If a decision looks wrong against the request or a contract,
report it as a finding.

## Commands
- tests: `python3 -m pytest -q` (system python has no pytz, so tz tests skip). A throwaway venv with pytz, black==20.8b1, click==8.0.4, mypy, sphinx already exists at <workspace>/venv — use its bin/python for pytz tests (`-p no:cacheprovider test_schedule.py schedule`), bin/black --check ., bin/python -m mypy -p schedule. You may use it; don't install into the system python.
- lint: black --check . (20.8b1), mypy -p schedule
- offline run: n/a (no network code)
- known failures at BASE: none

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
findings. A case where an absolute word in the request ("never", "always", "only") doesn't
hold is blocking, even at an edge such as a late or missed run and even if similar code
behaves that way, unless the request or a recorded user decision accepts the exception.
A clean review, with no findings, is a valid and useful result.

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

No blocking findings. Every criterion passed when I ran the code directly, and I found no case where the job runs on a Saturday or Sunday. There are two optional improvements and one observation below. HEAD is still `eb86cc7bd58d` and the tree is clean. The patch file matches `82a43db1b938..eb86cc7bd58d` apart from its larger context lines.

### Criteria
- **C1 PASS**: `every().weekday.unit == "days"`. `at()` accepts "09:00", "09:00:30", "00:00" and "23:59:59". It rejects ":30", "9:00", "24:00", "09:60", "09:00:60", "0900" and "09:00:" with ScheduleValueError.
- **C2 PASS**: I compared `next_run` with an independent oracle (the next Mon–Fri 09:00 strictly after now) at 8,382 moments over 3 weeks, using both `at("09:00")` and `at("09:00:30")`. There were 0 mismatches. The boundaries matched too: Fri 09:00:00 exactly gives Mon 09:00, and Sun 23:59:59 gives Mon 09:00.
- **C3 PASS**: I polled `run_pending` every 15 minutes for 3 weeks, starting on each day of the week at poll offsets 0, 1, 7 and 14 minutes (28 runs). Each run gave exactly 15 executions, one per Mon–Fri date, all at 09:00 and none at the weekend.
- **C4 PASS**: For a missed Friday run, I tried the first poll at every 30-minute slot of Sat/Sun with `run_pending`, `run_all` and a direct `job.run()`. The job never executed, `next_run` became Mon 09:00, the job stayed scheduled and `run()` returned None. `run_all` on a weekday still runs the job. `until()` holds: a deadline of Sun 12:00 or Mon 08:59 cancels the job during the weekend skip, a deadline of Mon 09:00 or 10:00 keeps it and it runs once on Monday, and a deadline already past on Saturday cancels it.
- **C5 PASS (with a DST caveat, finding 1)**: I tested 5 local zones × 6 job zones (including Kiritimati +14 and New York/Auckland/Berlin DST windows) × 3 times, polling for 2 weeks. None of those runs was on a Sat/Sun in the job's timezone, and `next_run` was always naive. A randomised test (150 seeds, irregular polling from 1 minute to 80 hours, 10% `run_all`, mixed zones, 16,116 executions) also had 0 weekend runs.
- **C6 PASS**: `every(2).weekday` raises IntervalError. `weekday.{second(s),minute(s),hour(s),week(s),monday..sunday}.do()` raises ScheduleValueError, and so does `monday.weekday.do()`. The ordering case in finding 3 is an observation, not a failure.
- **C7 PASS**: results are in the next section.

The main session's decisions are all followed: the property with the `weekdays_only` flag, skipping at run time, judging the weekday in the job's timezone, the error types, a no-`at()` job running at the time it was scheduled (created Sat 12:15, it first runs Mon 12:15, then 10 runs over 2 weeks, all at 12:15 on weekdays), the new repr with str unchanged, and the docs example.

### Test run
- System python (no pytz), `python3 -m pytest -q`: `48 passed, 42 skipped in 0.16s`. BASE gives `40 passed, 41 skipped`. The 9 new tests account for the difference: 8 pass and `test_tz_weekday` skips because pytz is missing.
- Venv with pytz 2026.4, `pytest -q -p no:cacheprovider test_schedule.py schedule`: `90 passed in 0.18s`.
- `black --check .` (20.8b1): `All done! 4 files would be left unchanged.`
- `mypy -p schedule`: `Success: no issues found in 1 source file`.
- `sphinx-build -W -b html`: `build succeeded.` `Job.weekday` appears in the index.
- Test-change audit: `test_schedule.py` has 145 lines added and 0 deleted, so no existing test was edited. There are no new dependencies, no network calls and no config changes.

### Findings

**1. Optional improvement: a weekday job whose time falls in a DST gap runs an hour late on the Monday after a spring-forward weekend**
- **Requirement:** "run Monday to Friday at [the given time]", with a timezone passed to `at()`. This is a narrow edge case; 09:00 itself is not affected.
- **Location:** `schedule/__init__.py:787-792`. The weekend-skip loop only re-normalises the UTC offset after adding a day. When Sunday's time falls in the DST gap it gets moved to 03:30, and adding one more day carries 03:30 into Monday.
- **Reproduction:** script at `<workspace>/review/probe3.py`. Create `every().weekday.at("02:30", "America/New_York")` on Fri 2024-03-08 and poll every 15 minutes. It runs `Mon 03-11 03:30-0400` instead of 02:30. `Europe/Berlin` on 2024-03-29 gives `Mon 04-01 03:30+0200`, and `Pacific/Auckland` gives the same on 2024-09-30.
- **Impact:** once a year, weekday jobs scheduled inside the gap hour (usually 02:xx) run one hour late on that Monday. It is never a weekend run.
- **Smallest fix:** replace the loop body with `next_run = self._move_to_at_time(next_run + datetime.timedelta(days=1))`, which is a no-op when `at_time` is None. I tried this in a throwaway copy (`/tmp/rev-fix`): the Monday runs came back at 02:30 in all three zones and all 90 tests passed. The patch should also add a regression test for a spring-forward weekend.
- **Not caused by this patch:** a job created on the transition Sunday after the gap still runs Monday at 01:30 and again at 02:30. BASE `every().day.at("02:30", tz)` does exactly the same (confirmed at `/tmp/rev-base`), so this comes from the existing `_move_to_at_time`/`_correct_utc_offset` code.

**2. Optional improvement: `every().weekday.to(N)` is accepted but does not run every weekday**
- **Contract:** the decision "`every(2).weekday` raises IntervalError: clear error rather than guessing". `.to()` gets around it because `interval` is still 1.
- **Location:** `schedule/__init__.py:751-755`. The validation does not check `self.latest`.
- **Reproduction:** from Mon 2024-01-08 10:00, over 200 seeds, `every().weekday.to(3).do(job)` put `next_run` on Tue (74), Wed (65) or Thu (61). Some weekdays are skipped, yet the repr still says `"Every weekday do job() ..."`.
- **Impact:** low; nobody asked for this combination. It never produces a weekend run.
- **Smallest fix:** add `or self.latest is not None` to the ScheduleValueError condition at line 751, with a test.

**3. Observation: a unit set before `weekday` is silently replaced**
- **Location:** `schedule/__init__.py:488-489`.
- **Evidence:** `every().hours.weekday.do(job)` (the same goes for minutes, seconds and weeks) does not raise and becomes a normal weekday job with unit "days". This matches the library's existing "last unit wins" rule: `every().hour.day` is a daily job. The job still never runs at the weekend. C6 as written (`weekday.hours`) does raise.
- **Correction:** none needed. If you want C6 enforced in both orders, `weekday` would have to reject a unit that is already set.

### Not verified
- Python versions other than the system python and the venv's; tox runs 3.7–3.12.
- The `setup.py check --strict` tox environment. Not run; the patch doesn't touch packaging metadata.
- Real wall-clock behaviour. Every check used the suite's `mock_datetime`, which patches `datetime.datetime` and the TZ environment variable.

Probe scripts are in `<workspace>/review/` (`probe1.py` to `probe4.py`). The BASE copy is at `/tmp/rev-base` and the copy with the fix is at `/tmp/rev-fix`.
```

## 2. orch-rechecker: Re-check DST/to() repair

### Brief

```text
You are an independent reviewer re-checking a repair. Don't edit tracked files, install into
the shared environment, or delegate.

Request (verbatim): In this repo (schedule), add a way to schedule a job on weekdays only: `schedule.every().weekday.at("09:00").do(job)` should run Monday to Friday at 09:00 and never on Saturday or Sunday. Add tests; the existing suite must stay green. The tests run with `python3 -m pytest -q`.

(Context for this run: no one is available to answer questions until you finish, so make sensible calls, record them, and carry on. Keep any plan, notes or report files you create; don't delete them at the end.)
Use the code-orchestrator skill in Reviewed mode (you build; one independent review).

Repo: <workspace>/release-results-final/schedule-weekday-reviewed/release/run-1/repo
Candidate: 22f1204428a95e12e8b1092efe02b0b5f5fa7c9d, patch .orchestrator/review/candidate-22f1204428a9.patch (BASE 82a43db..candidate); the previous candidate was eb86cc7bd58d679c33f49fec2fc8c7410e550246 (the repair is the single commit eb86cc7..22f1204).
Tests: `python3 -m pytest -q` (system python, no pytz; tz tests skip). A throwaway venv with pytz/black 20.8b1/mypy is at <workspace>/venv/bin — use its python for `-m pytest -q -p no:cacheprovider test_schedule.py schedule`. Earlier probe scripts are in the sibling scratchpad/review/ directory (probeN.py <repo-path> weekday); probe1 exercises weekday.to(), which is now rejected on purpose.

Findings the repair addresses (verbatim):
1. Optional improvement: a weekday job whose time falls in a DST gap runs an hour late on the Monday after a spring-forward weekend. Location: schedule/__init__.py weekend-skip loop only re-normalizes the UTC offset after adding a day; when Sunday's time falls in the DST gap it gets moved to 03:30, and adding one more day carries 03:30 into Monday. Repro: every().weekday.at("02:30", "America/New_York") created Fri 2024-03-08, polled every 15 min, runs Mon 03-11 03:30-0400 instead of 02:30 (also Europe/Berlin 2024-03-29 and Pacific/Auckland 2024-09-30). Smallest fix: re-apply the at_time via _move_to_at_time after adding the day.
2. Optional improvement: `every().weekday.to(N)` is accepted but does not run every weekday (next_run lands on Tue/Wed/Thu at random from a Monday). Smallest fix: reject `latest is not None` with ScheduleValueError.

Do:
1. Run the tests.
2. Reproduce each finding's original failure, and mark it ADDRESSED or NOT ADDRESSED, with
   evidence. "Attempted" is not addressed.
3. Probe the behaviour next to each fix: a fix that moves one boundary often breaks another (e.g. fall-back weekends, weekday jobs without at(), jobs in local time with no tz, the Sunday-of-transition creation case, and that no run is ever on Saturday/Sunday).

Report: Verdict PASS | FAIL; each finding ADDRESSED | NOT ADDRESSED with evidence; any new
blocking finding (requirement violated, file:line, reproduction, impact, smallest fix); what you couldn't verify.
```

### Reply

```text
## Verdict: PASS

The candidate (commit `22f1204`) implements `schedule.every().weekday`, addresses both findings from the brief with verifiable evidence, and the full suite is green (`49 passed, 43 skipped` on system Python without pytz; `92 passed, 0 skipped/failed` with pytz via the throwaway venv). The repo working tree is unmodified by this review (`git status --porcelain` empty throughout).

### Finding 1 — DST-gap weekend-skip off-by-one — ADDRESSED

Reproduced the finding's exact repro cases (job created Friday, polled every 15 min) against the pre-fix commit (`eb86cc7`) and the candidate (`22f1204`), using a throwaway checkout at `/tmp/review_prefix` and `/tmp/review_candidate`:

- Pre-fix: `America/New_York` 2024-03-08→03-11 run at `03:30-0400` (an hour late); `Europe/Berlin` 2024-03-29→04-01 run at `03:30+0200`; `Pacific/Auckland` 2024-09-27→09-30 run at `03:30+1300`.
- Candidate: all three now run at the correct `02:30` local time on Monday.

This matches the fix in `schedule/__init__.py` (the weekend-skip loop, ~lines 790-797, now calls `_move_to_at_time` after `+= timedelta(days=1)`).

### Finding 2 — `weekday.to(N)` silently accepted — ADDRESSED

- Pre-fix: `every().weekday.to(3).do(job)` was accepted and produced `next_run` on a Thursday (interval=3 landed there), i.e., not "every weekday."
- Candidate: raises `ScheduleValueError: \`weekday\` can only be combined with \`at\`, not with \`to\`, other units or days of the week` (`schedule/__init__.py` ~lines 751-757). Verified directly and via `test_weekday_rejects_randomized_interval`.

### Boundary probing next to the fix

Using the sibling probe scripts (`scratchpad/review/probe1..4.py`) plus targeted repros, against the candidate:

- **Core requirement ("never on Saturday or Sunday")**: a 150-seed fuzz run (`probe4.py`) over random timezones, `at()`/no-`at()` combinations, and irregular poll intervals produced 16,116 total runs across all seeds with **zero** weekend runs. `probe2.py`'s missed-Friday/`until`/`run_all` sweep found no false runs or missed cancellations either.
- **Weekday jobs without `at()`**: behave correctly (created Sat → first run Monday at the creation time-of-day; subsequent runs stay on weekdays).
- **Local time, no tz**: `test_weekday_at_next_run`-style Mon–Sun matrix (8382 cases in `probe1.py`) all matched the oracle.
- **Fall-back weekends** (NY 2024-11-03, Berlin 2024-10-27), both Friday-created and Sunday(after-fallback)-created: single correct run per weekday, no duplicates.
- **Chaining oddities** (`every().hours.weekday`, `every().weekday.seconds`, etc.): initially looked like probe failures, but traced to pre-existing library semantics — any `.day`/`.days`/`.weekday` access unconditionally resets `unit` to `"days"`, same as `every().hours.days` on the base commit. Not a bug.

### New finding (pre-existing, not a regression, not blocking)

`probe2.py`'s C5 sweep flagged 2 cases (`Europe/Berlin` job tz, `at("02:30")`, job created on the Sunday of a spring-forward DST transition after that day's gap has already passed) where the job **double-fires on the following Monday**: once at the wrong time and once at the correct time.

- Repro (minimal, no exotic timezone needed): system local tz = UTC, `every().weekday.at("02:30", "Europe/Berlin")` created at `2024-03-31 20:00 UTC` (Sunday, after Berlin's 02:00→03:00 gap that day) → runs `Mon 04-01 01:30+0200`, `Mon 04-01 02:30+0200`, `Tue 04-02 02:30+0200`, ...
- Location: `schedule/__init__.py` lines 782-788 — the `while next_run <= now: next_run += period` step (not the weekend-skip loop) advances by a naive `timedelta(days=1)` across the DST boundary, and the subsequent `_correct_utc_offset(next_run, fixate_time=True)` call resolves it to the wrong hour.
- Confirmed **pre-existing and unrelated to the weekday feature**: reproduces identically on the pre-weekday base commit (`82a43db`'s equivalent, tested via `82a43db`'s ancestor `eb86cc7`/prefix tree) with plain `every().day.at("02:30", "Europe/Berlin")` — same double-fire, same times. So this is not a regression introduced by `22f1204`, and it never causes a run on Saturday/Sunday (only a same-Monday duplicate), so it does not violate the stated requirement.
- Smallest fix (for a follow-up, not this PR): re-apply `_move_to_at_time` (like the weekend-skip loop now does) after the `while next_run <= now: next_run += period` advancement too, not only after the weekend-skip day-add.

### Not verified

- `black`/`mypy` formatting/type-checking of the diff (available in the venv but not run, since the brief's Tests line only specifies pytest).
- Behavior on non-pytz `zoneinfo`/`dateutil` timezone objects (test suite and probes only exercise `pytz`, matching existing repo convention).

### Evidence artifacts (repo untouched)

- Base vs. candidate extracted trees: `/tmp/review_prefix` (commit `eb86cc7`), `/tmp/review_candidate` (commit `22f1204`)
- Repro scripts: `/tmp/finding1_exact.py`, `/tmp/finding2.py`, `/tmp/repro_sunday_creation.py`, `/tmp/repro_plain_day.py`, `/tmp/repro_local_berlin.py`, `/tmp/fallback_test.py`
- Reused probes: `.../scratchpad/review/probe1.py` … `probe4.py`
```
