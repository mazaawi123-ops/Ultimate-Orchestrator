### Verdict: PASS
`every().weekday.at("09:00")` computes the next run as the next Monday–Friday 09:00 and never Saturday or Sunday. The new tests pass, the existing ones are untouched and green, and all the CI checks pass. There's no blocking finding. There's one optional improvement: in certain timezones, a job created during a clock-change weekend runs 23 hours late on the Monday, still on the Monday. There are also two observations.

### Criteria
- **C1 PASS.** I compared 24,840 no-timezone cases against a separate, simple reference calculation. They used four local zones (Berlin, UTC, Auckland, New York), start times every 37 or 41 minutes across two weeks each in March and October 2023, and six at-times including 00:00:01 and 23:59:59. There were 0 mismatches. The candidate's own tests cover same-day-before-09:00 and exactly-09:00-rolls-to-tomorrow.
- **C2 PASS.**
  - No-timezone runs never land on Saturday or Sunday.
  - I simulated 30 schedulers over 35 days each, checking at random intervals of 1–3600 seconds. Each weekday got exactly one run and no weekend day got any.
  - With a timezone, I ran about 161k cases per local zone setting (Berlin and UTC local, 322,932 in total). They covered every `pytz.common_timezones` zone, with start times near each 2022–2024 clock change. None fell on a weekend in the given zone, none was in the past, and none had the wrong date.
  - A weekend-dated caveat for missed runs is under Observations.
- **C3 PASS.**
  - `every(2).weekday` and `every(0).weekday` raise IntervalError straight away.
  - `.weekday` combined with `.monday` (either order), `.hours`, `.week` or `.to(3)` raises ScheduleValueError at `do()`, before the job is added, so `schedule.jobs == []`.
  - Both errors are ScheduleError subclasses (schedule/__init__.py:60,66).
- **C4 PASS.** The system python gives 49 passed, 44 skipped. The base commit (82a43db) gives 40 passed, 41 skipped, so that's 9 new tests that run and 3 new timezone tests that skip. The diff removes no lines from `test_schedule.py`, `tox.ini`, the setup files, `requirements-dev.txt` or `.github`.
- **C5 PASS.** The venv with pytz passes all 93 tests. `black==20.8b1 --check .` passes, and so does `mypy -p schedule`. I also ran `sphinx-build -W` on an exported copy: it succeeded, and `setup.py check --strict --restructuredtext` gave no errors.
- **C6 PASS.** README, `docs/examples.rst`, HISTORY and the module docstring all mention the new API. `Job.weekday` shows up in the built reference page.
  - repr with a time: `Every weekday at 09:00:00 do f() (last run: [never], next run: …)`
  - repr without one: `Every weekday do <lambda>() (…)`
  - `str` is unchanged: `Job(interval=1, unit=days, …)`

### Test run
```
$ python3 -m pytest -q
49 passed, 44 skipped in 0.32s
$ /tmp/orch-weekday-venv/bin/python -m pytest -q -p no:cacheprovider
93 passed in 0.14s
$ black --check .                 -> All done! 4 files would be left unchanged.
$ python -m mypy -p schedule      -> Success: no issues found in 1 source file
$ sphinx-build -W -b html (docs)  -> build succeeded.
```

### Findings

**1. Optional improvement: the Monday run can come 23 hours late when a job is created during a clock-change weekend.**
- **Contract:** the at-time handling under clock changes (C1/C2 with a timezone). The run still lands on the right weekday, so the request's core holds.
- **Location:** `schedule/__init__.py:774-777`, the loop that skips Saturday and Sunday.
- **Mechanism:** the weekday flag skips Saturday and Sunday after the normal daily calculation. If the weekend slot was shifted to avoid a skipped clock hour, that shifted clock time is carried forward to Monday. Monday has no skipped hour, so the job runs at the wrong time.
- **Reproduction** (script: `scratchpad/repro_gap.py`, local zone Berlin as in the test suite):
  ```
  Atlantic/Azores   now=Sun 2022-03-27 12:00  every().weekday.at('00:30') -> Mon 2022-03-28 23:30  (expected Mon 00:30)
  America/Asuncion  now=Sun 2022-10-02 12:00  every().weekday.at('00:00') -> Mon 2022-10-03 23:00  (expected Mon 00:00)
  ```
- **How it compares with every().day:** `every().day` already gets these inputs wrong. It returns Sunday 23:30 and 23:00, one hour early. The weekday change turns that into a 23-hour delay on Monday.
- **Scale:** the full sweep gave 165 affected cases out of about 121k. They occur only in zones whose clock change happens around midnight at the weekend: Azores, Asuncion, Havana, Beirut, Gaza/Hebron, Nuuk, Scoresbysund, Troll, Casey, Coyhaique and Santiago.
- **Impact:** narrow. It needs the timezone argument, one of those zones, a job created or rescheduled during the clock-change weekend, and an at-time near the skipped hour. The run is still on the right weekday, and the problem clears after that one run.
- **Smallest correction:** inside the `if self.weekdays_only:` block, after the skip loop, add `if self.at_time is not None: next_run = self._move_to_at_time(next_run)`. Add a regression test for the Azores case.
- **Fix checked on a scratch copy:**
  - It gives 0 discrepancies in the full timezone sweep, down from 1,227. The other 1,062 were existing daily clock-change errors that weekday jobs share with `every().day`, and the fix clears those for weekday jobs too.
  - The no-timezone checks still pass, and all 93 tests still pass.

**2. Observation: a missed Friday run is executed on Saturday.**
- **Where:** `should_run` at schedule/__init__.py:700, existing code.
- **Reproduction:** create the job Friday 08:00. If `run_pending()` is first called Saturday 10:00, the job runs on Saturday; the next run is then Monday 09:00.
- **Why it's only an observation:** this is the library's existing rule that overdue jobs run at the next check, and `every().monday` behaves the same way. The *scheduled* next run is never on a weekend. It only happens if the loop is blocked or the machine sleeps past the slot, and `run_all()` also ignores the day. Changing it would break with the library's semantics, so I'd leave it. The user might want a line in the docs, though, given "never on Saturday or Sunday".

**3. Observation: with a timezone, the run can fall on Saturday or Sunday in the machine's own zone.**
This follows from the recorded decision to judge the day of the week in the given timezone. The test `test_tz_weekday_judged_in_given_timezone` shows it: Friday 20:00 in New York runs at Saturday 02:00 Berlin time. The `weekday` docstring states it. It doesn't affect the request's example, which has no timezone. It's reported so the choice stays visible.

### Not verified
- Python 3.7–3.10 and 3.12, and tox itself. Only Python 3.11.15 is available here, and the change adds no new syntax.
- The timezone sweep uses pytz 2026.3's rules and covers only 2022–2024 clock changes plus a sample week for zones without changes.
- Scratch scripts (`prop_check.py`, `prop_tz.py`, `classify_tz.py`, `diff_tz.py`, `repro_gap.py`) and the exported base, candidate and trial-fix copies are kept in the session scratchpad. The tracked tree was not modified; `git status` is clean.