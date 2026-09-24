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

## Candidate
Repo <workspace>/release-results/schedule-weekday-reviewed/release/run-1/repo, candidate f142db5a64be2a2d62e51f953e83c059c0367d0e on branch orch/weekday. Patch: <workspace>/release-results/schedule-weekday-reviewed/release/run-1/repo/.orchestrator/review/candidate-f142db5a64be.patch
(BASE 82a43db1b938..candidate).

## Contracts to preserve
- Job builder-pattern properties and their existing behaviour (schedule/__init__.py, class Job): second(s)/minute(s)/hour(s)/day(s)/week(s), monday..sunday, at(), to(), until(), do(), tag().
- `_schedule_next_run` unit validation and the daily/weekly/tz/DST next-run logic; next_run stays a naive local datetime.
- Existing `__str__` and `__repr__` output for non-weekday jobs (test_to_string / test_to_repr).
- No new runtime dependencies (pytz stays optional, imported only when a tz is given).
- CI (tox.ini, .github/workflows/ci.yml): pytest on py3.7–3.12 with and without pytz, `mypy -p schedule`, `black==20.8b1 --check .`, sphinx docs build with -W.

## Acceptance criteria (the main session's reading of the request)
- C1: `schedule.every().weekday.at("09:00").do(job)` computes next_run as the next Mon–Fri 09:00 strictly after now (same day if before 09:00 on a weekday).
- C2: next_run is never a Saturday or Sunday — from any starting day of the week, and across repeated runs (Fri run -> next Mon; Sat/Sun now -> Mon).
- C3: invalid combinations fail loudly with a ScheduleError subclass instead of silently doing something else: `every(2).weekday` (IntervalError), `.weekday` combined with `.monday`..`.sunday`, with a non-day unit, or with `.to()`.
- C4: Existing tests unchanged and green: `python3 -m pytest -q` (baseline 40 passed / 41 skipped — pytz is unavailable in the system python, so tz tests skip).
- C5: CI checks pass on the candidate: black==20.8b1 `black --check .`, `mypy -p schedule`, and the full suite with pytz installed.
- C6: Docs mention the new API (README + docs/examples.rst); repr of a weekday job reads sensibly.
Where a criterion misses or contradicts the request, say so: the request is the reference.

## Decisions the main session made (decisions, not facts)
- Decision: implement as unit="days" plus a `weekdays_only` flag, skipping forward past Sat/Sun after the normal daily next-run computation — reuses daily at()/tz/DST logic.
- Decision: with `at(..., tz)`, the day of week is judged in that timezone (the zone the at-time is expressed in), not the machine's local zone. Consequence: the run's local calendar day can be Sat/Sun in cross-zone setups (e.g. Fri 20:00 New York is Sat 02:00 Berlin).
- Decision: `every().weekday.do(job)` without at() is allowed: runs once per weekday at the time-of-day of scheduling, like every().day.
- Decision: reject `every(n>1).weekday`, `.to()` with weekday, weekday combined with a named day or a non-days unit — raise rather than guess.
- Decision: repr shows "Every weekday at 09:00:00 do ..."; `__str__` format unchanged (unit=days).

## Commands
- tests: `python3 -m pytest -q`   (system python, no pytz)
- tests with pytz + CI tools: a throwaway venv already exists at /tmp/orch-weekday-venv (black==20.8b1, click==8.0.4, pytz, types-pytz, mypy, pytest, Sphinx). Use `/tmp/orch-weekday-venv/bin/python -m pytest -q -p no:cacheprovider`, `/tmp/orch-weekday-venv/bin/black --check .`, `/tmp/orch-weekday-venv/bin/python -m mypy -p schedule`. Don't install into it; create your own under /tmp if you need something else.
- offline run: n/a (no network use)
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

The change does what was asked: next runs land Monday to Friday at the requested time and never on a weekend, the existing suite stays green, and CI passes. I found one real but narrow defect: a timezone job scheduled on the Sunday clocks go forward can run an hour late the next Monday. I've rated it an optional improvement, not blocking; the fix is below.

### Criteria
- **C1 PASS.** I compared `every().weekday.at(t).do(f)` against a brute-force reference in 21,600 cases: every 7 minutes over 3 weeks spanning Berlin's March 2023 clock change, with t = 09:00, 00:00, 23:59:59, 09:00:30 and 02:30. There were 0 mismatches. "Strictly after now" holds: Monday at exactly 09:00 gives Tuesday 09:00.
- **C2 PASS.**
  - **Minute-by-minute simulation:** over 5 weeks, the job ran 25 times, once per weekday, all at 09:00, never on Saturday or Sunday. Friday goes to Monday, and Saturday or Sunday goes to Monday.
  - **Without `at()`:** 14 runs in 3 weeks, none on a weekend.
  - **With a timezone (pytz):** I tested every common zone around every clock change from 2020 to 2026, under 4 machine timezones (141,974 cases each). The run never fell on a weekend in the given timezone. On weekdays it always matched `every().day.at(...)` exactly.
  - The one exception is a job that is already overdue, covered in the observations below.
- **C3 PASS, with a gap.**
  - These all raise a `ScheduleError` subclass and register no job: `every(2).weekday` and `every(0).weekday` (IntervalError); `.weekday` combined with any of monday..sunday in either order, `.weekday.<second|minute|hour|week>(s)`, and `.to()` in either order (ScheduleValueError).
  - The reverse order does not raise: `every().hour.weekday` is accepted (see the observations).
- **C4 PASS.** BASE gives 40 passed / 41 skipped. The candidate gives 49 passed / 44 skipped: 9 new tests run and 3 timezone tests skip without pytz. The test diff only adds lines; no existing test was changed.
- **C5 PASS.** black 20.8b1 `--check .` passes, and `mypy -p schedule` reports no issues. With pytz, 93 tests pass, including the CI form `pytest test_schedule.py schedule`. `sphinx-build -W` succeeds. `setup.py check --strict --metadata --restructuredtext` exits 0.
- **C6 PASS.** README, docs/examples.rst, HISTORY and the module docstring show the new call. `repr` reads `Every weekday at 09:00:00 do job_fun(1, b=3) (last run: [never], next run: ...)`, and without `at()` it reads `Every weekday do ...`. `__str__` output is unchanged (`Job(interval=1, unit=days, ...)`).

### Test run
```
python3 -m pytest -q                        -> 49 passed, 44 skipped in 0.13s
venv pytest -q -p no:cacheprovider (pytz)   -> 93 passed in 0.13s
black --check .                             -> All done! 4 files would be left unchanged.
mypy -p schedule                            -> Success: no issues found in 1 source file
sphinx-build -W (docs)                      -> build succeeded.
```

### Findings

**1. Optional improvement: after a clock change, the shifted time carries over to Monday.**
- **Contract:** C1 (run at the `at()` time on Mon–Fri), and "reuses the daily at/tz/DST logic".
- **Location:** `<workspace>/release-results/schedule-weekday-reviewed/release/run-1/repo/schedule/__init__.py:774-777`
- **Cause:** when clocks go forward, a missing time is moved an hour later, and that happens inside `_move_to_at_time` before the weekend skip. If "now" is on a weekend day whose `at()` time falls in the skipped hour, the day is corrected to 03:30. The skip then adds whole days and keeps 03:30 on Monday.
- **Reproduction (machine TZ Berlin):** at Sun 2024-03-31 00:30, `every().weekday.at("02:30", "Europe/Berlin")` gives **Mon 04-01 03:30** instead of 02:30. `every().day.at(...)` correctly gives Sun 03:30 and then Mon 02:30. The same happens with New York: at Sun 2024-03-10 01:00, the result is Mon 03:30 EDT.
- **Scale:** 1,976 of 141,974 brute-force cases, across 145 zones including all US and EU zones. Every one of them is specific to the weekday code, not inherited from the daily logic.
- **Impact:** the Monday run is one hour late. It needs all three: a timezone argument, an `at()` time inside the skipped hour, and the job being created or run on that Sunday before the change. It corrects itself after that run (next is Tue 02:30). The user's 09:00 example, and any job without a timezone, are not affected.
- **Smallest fix:** re-apply the at-time after skipping.
  ```python
  skipped = False
  while next_run.weekday() >= 5:
      next_run += datetime.timedelta(days=1)
      skipped = True
  if skipped and self.at_time is not None:
      next_run = self._move_to_at_time(next_run)
  ```
  I checked this in a scratch copy: 93 passed, and 0 mismatches in the brute-force run.
  - **Suggested test:** the Berlin reproduction above.

**2. Observation: only one order of `.weekday` plus another unit is rejected.**
- **Contract:** C3 (".weekday with a non-day unit fails loudly").
- **Location:** the `weekday` property at `schedule/__init__.py:467-483`, and the check at 737-742.
- **Evidence:**
  - `every().hour.weekday.do(f)` and the seconds, minutes and weeks versions register "Every weekday do ..." with no error.
  - `every().minute.at(":30").weekday.do(f)` becomes weekdays at 00:00:30.
  - Only `.weekday.<unit>` raises.
  - This matches the library's existing behaviour, where the last unit wins: at BASE, `every().hour.day` gives a daily job and `every().minute.at(":30").day` gives daily at 00:00:30.
- **Impact:** low. The request doesn't require this; C3 as written is broader than what was built and what the tests cover.
- **Correction (if wanted):** in `weekday`, raise when `self.unit not in (None, "days")`. Otherwise, narrow C3's wording.

**3. Observation: an overdue job can still run on a weekend.**
- **Evidence:** a job created Friday 08:00 for 09:00, where `run_pending()` is next called on Saturday at 10:00, runs at **Sat 10:00**; its next run is then Mon 09:00. This happens because `should_run` is simply `now >= next_run`. `run_all()` also runs it on any day.
- **Impact:** "never on Saturday or Sunday" holds for the scheduled next run, not for an overdue run after the loop stalled (for example, the machine slept). A missed `every().monday` job behaves the same way, running on Tuesday. Worth recording as a known limit; no change proposed.

**4. Observation: a clock-change quirk inherited from the existing daily logic, not introduced here.**
- **Evidence:** at BASE, `every().day.at("02:30", "Europe/Berlin")` created on Sun 2024-03-31 at 04:00 or 12:00 gives Mon **01:30**. The weekday job inherits the same result.
- **Impact:** out of scope for this change.

### Not verified
- **Other Python versions:** I only ran 3.11; 3.7–3.10 and 3.12 weren't available. The change uses no syntax that's new in those versions.
- **Coverage:** the tox `--cov` run was skipped because pytest-cov isn't installed in the venv.
- **tox itself:** I ran each CI command directly, not through tox.

My scratch scripts are in `/tmp/rev-scratch/`. Clean copies of BASE and the candidate are in `/tmp/rev-base` and `/tmp/rev-cand`, and the patched copy with the fix is in `/tmp/rev-fix`. The repo is untouched: the working tree is clean and HEAD is still f142db5a64be2a2d62e51f953e83c059c0367d0e.
```

## 2. orch-rechecker: Re-check weekday DST repair

### Brief

```text
You are an independent reviewer re-checking a repair. Don't edit tracked files, install into
the shared environment, or delegate.

Request (verbatim): In this repo (schedule), add a way to schedule a job on weekdays only: `schedule.every().weekday.at("09:00").do(job)` should run Monday to Friday at 09:00 and never on Saturday or Sunday. Add tests; the existing suite must stay green. The tests run with `python3 -m pytest -q`.

(Context for this run: no one is available to answer questions until you finish, so make sensible calls, record them, and carry on. Keep any plan, notes or report files you create; don't delete them at the end.)

Repo: <workspace>/release-results/schedule-weekday-reviewed/release/run-1/repo
Candidate: 156c94e96b88a6f1954ea7166cc27bae9af45e1b, patch <workspace>/release-results/schedule-weekday-reviewed/release/run-1/repo/.orchestrator/review/candidate-156c94e96b88.patch (BASE 82a43db1b938..candidate); the previous candidate was f142db5a64be2a2d62e51f953e83c059c0367d0e (`git diff f142db5 156c94e` shows the repair alone).

Environment: system python3 has no pytz (tz tests skip). A throwaway venv with pytz, black==20.8b1, mypy, pytest exists at /tmp/orch-weekday-venv (use `/tmp/orch-weekday-venv/bin/python -m pytest -q -p no:cacheprovider`); don't install into it. A previous reviewer left scratch material at /tmp/rev-scratch/ (brute-force comparison scripts), /tmp/rev-base (BASE copy) — you may reuse or adapt them in /tmp; treat them as unverified.

Findings the repair addresses (verbatim):
1. Optional improvement — DST-gap at-time shift is carried across the weekend skip. Location: schedule/__init__.py (weekday skip in _schedule_next_run). When "now" is on a weekend day whose at-time falls in a spring-forward gap, _move_to_at_time (before the skip) already shifted it +1h (e.g. to 03:30); the skip then adds whole days and preserves 03:30 onto Monday. Repro (machine TZ Berlin): at Sun 2024-03-31 00:30, every().weekday.at("02:30", "Europe/Berlin") -> next_run Mon 04-01 03:30 instead of 02:30. Suggested fix: re-apply _move_to_at_time after skipping.
2. Observation — only one ordering of weekday+unit is rejected: every().hour.weekday (and second/minute/week variants, every().minute.at(":30").weekday) silently register a weekday job, while every().weekday.hour raises. Correction: in `weekday`, raise when self.unit not in (None, "days").

Do:
1. Run the tests (system python and the pytz venv), black --check ., mypy -p schedule.
2. Reproduce each finding's original failure against the new candidate, and mark it ADDRESSED or NOT ADDRESSED, with evidence. "Attempted" is not addressed.
3. Probe the behaviour next to each fix: a fix that moves one boundary often breaks another. In particular: brute-force weekday tz jobs around DST transitions (gap and fold, several zones and machine TZs) — next_run must be a weekday in the job's tz, at the at-time (or the documented DST-gap best-effort time when the target Monday..Friday day itself has the gap), and equal to every().day.at(...) on weekday days; weekday jobs without tz and without at(); and that `every().day.weekday` still works while the rejection doesn't break any existing builder chain.

Report: Verdict PASS | FAIL; each finding ADDRESSED | NOT ADDRESSED with evidence; any new
blocking finding (requirement violated, file:line, reproduction, impact, smallest correction); what you couldn't verify.
```

### Reply

```text
## Verdict: PASS

Candidate `156c94e96b88a6f1954ea7166cc27bae9af45e1b` (repair diff `f142db5..156c94e` in `schedule/__init__.py`, both hunks) correctly addresses both findings without regressing existing behavior.

### Test/lint results
- `python3 -m pytest -q` (system, no pytz): **49 passed, 45 skipped** (tz tests skip, as expected without pytz).
- `/tmp/orch-weekday-venv/bin/python -m pytest -q -p no:cacheprovider` (pytz venv): **94 passed, 0 skipped, 0 failed**.
- `black --check .` (venv): all files unchanged — clean.
- `mypy -p schedule` (venv): no issues found.
- `git status --porcelain`: clean throughout (no tracked files modified by this review).

### Finding 1 — DST-gap at-time carried across weekend skip: **ADDRESSED**
Repro (`Sun 2024-03-31 00:30` Berlin, `every().weekday.at("02:30","Europe/Berlin")`):
- Pre-repair (`f142db5` worktree): `next_run = 2024-04-01 03:30:00` (bug — gap-shift carried onto Monday).
- Candidate (`156c94e`): `next_run = 2024-04-01 02:30:00` (correct).
The fix (`schedule/__init__.py`, in `_schedule_next_run`) re-invokes `self._move_to_at_time(next_run)` after the weekend-skip loop, which re-derives the at-time in the landing day's own offset instead of carrying the shifted wall-clock time forward. Confirmed against the actual pre-repair commit, not just the diff.

### Finding 2 — only one weekday+unit ordering was rejected: **ADDRESSED**
Directly reproduced pre/post on `.do()`-triggered scheduling:
- Pre-repair: `every().hour.weekday`, `.minute.weekday`, `.second.weekday`, `.week.weekday`, `.minute.at(":30").weekday` all silently registered as weekday jobs (unit ended up "days" because `.weekday` returns `self.days`, overwriting the unit set by the preceding property); only `every().weekday.hour` raised (unit ends "hours" after `.weekday`).
- Candidate: all five silently-passing orderings above now raise `ScheduleValueError` immediately from the `weekday` property (`if self.unit not in (None, "days") or self.start_day is not None: raise ...`), matching `weekday.hour`'s existing behavior. `every().day.weekday` and bare `every().weekday` continue to work.
New tests added in the candidate diff (`test_schedule.py`, `test_weekday_and_daily_exclusive` extension and `test_tz_weekday_dst_gap_on_sunday`) cover exactly these two cases and pass.

### Adjacent-behavior probing
- Brute-forced `every().weekday.at(...)` across 6+ zones (Europe/Berlin, America/New_York, Australia/Lord_Howe, Pacific/Chatham, America/Sao_Paulo, Asia/Tehran, Australia/Adelaide, America/Santiago), 7 at-times, full-year day sweep, multiple "now" offsets, both DST directions and `fold=0/1`: **0 weekend `next_run` results** across ~155k combined cases (gap+fold scripts).
- On days that aren't themselves DST-transition days, `every().weekday.at(...)` next_run exactly equals `every().day.at(...)` next_run whenever the landing day is Mon–Fri (1800/1800 checked, 0 mismatches).
- Weekday jobs without tz and without `at()` work correctly (skip Sat/Sun, land on next weekday).
- `every().day.weekday`, `every(1).day.weekday` still work and set `weekdays_only=True`; `every(2).weekday` still correctly raises `IntervalError`; `every(2).days` (no `.weekday`) is unaffected (`weekdays_only=False`); `every().monday` unaffected.

### New finding surfaced (not a candidate regression, informational only)
While brute-forcing, found 9/81984 cases where the *at-time itself* (not weekday-ness) ends up wrong in the opposite direction — e.g. `every().weekday.at("02:30","Europe/Berlin")` computed with "now" = Sun 2024-03-31 **10:00** (i.e., already past the spring-forward gap that same day) yields `next_run = 2024-04-01 01:30`, not `02:30`. I verified this is **pre-existing and not introduced or left by this repair**: it reproduces identically with plain `every().day.at("02:30","Europe/Berlin")` on both the candidate and on the untouched `82a43db` release commit (before the `weekday` feature existed at all). Root cause is in `_correct_utc_offset`'s gap-correction direction depending on which side of the transition "now" sits (an existing library subtlety unrelated to weekday logic). I'm not marking this as a blocking finding against the candidate since it's out of scope of the repair and equally present in `.day.at()`; flagging only for awareness (location: `schedule/__init__.py`, `_correct_utc_offset`, lines ~824–866).

### Not verified
- Did not test additional interpreters (only the system `python3` and the provided venv's Python 3.11).
- Did not exhaustively brute-force `fold=1` combined with the weekend-skip path landing exactly on a fold-ambiguous Monday time (only checked weekday-ness there, not exact at-time match); given the equivalence check against `.day.at()` passed broadly, this is unlikely to be new but wasn't separately exhaustively cross-checked for that narrow slice.
- Did not install/run against any Python version other than what the two provided environments offer.

Scratch scripts used (self-written, not the prior reviewer's unverified `/tmp/rev-scratch` material): `/tmp/repro_finding1.py`, `/tmp/repro_finding2.py`, `/tmp/repro_finding2b.py`, `/tmp/brute_weekday_dst3.py`, `/tmp/brute_weekday_fold.py`, `/tmp/brute_weekday_equiv.py`. No tracked files were modified.
```
