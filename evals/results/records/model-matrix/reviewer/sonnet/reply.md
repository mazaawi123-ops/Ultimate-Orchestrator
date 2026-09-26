No new dependencies, no secrets/network calls, no CI config edits.

### Verdict: PASS

### Criteria:
- **C1 PASS** — `every().weekday.at("09:00")` computes next-run correctly: same day when before 09:00, next day otherwise (verified: Monday 08:59 → same-day 09:00; Monday 10:00 → Tuesday 09:00, per `test_weekday_next_run_from_every_day_of_week` and my own reproduction).
- **C2 PASS** — Verified from every starting weekday (Mon–Sun) that `next_run.weekday() < 5`, and that repeated `.run()` calls from Friday jump to the following Monday (`schedule/__init__.py:774-777`). One documented, recorded exception exists: when `at()` is given a timezone different from the machine's local zone, the *local* calendar day of `next_run` can land on Sat/Sun (reproduced: NY 20:00-Friday → Berlin-local Sat 01:00, `next_run.weekday()==5`). This is an explicitly recorded main-session decision ("the day of week is judged in the `at()` timezone... the run's local calendar day can be Sat/Sun in cross-zone setups"), so per the review brief it is not blocking — see Findings for the observation.
- **C3 PASS** — `every(2).weekday` raises `IntervalError` (a `ScheduleValueError`/`ScheduleError` subclass, `schedule/__init__.py:66`); `.weekday` combined with `.monday`/other named days, with `.hours`, or with `.to()` all raise `ScheduleValueError` at `do()`-time via `_schedule_next_run` (`schedule/__init__.py:737-746`), verified both orderings (`.weekday.monday` and `.monday.weekday`, `.to(1).weekday`).
- **C4 PASS** — Baseline at BASE (82a43db1b938) is exactly 40 passed/41 skipped (verified by checking out base files and running `python3 -m pytest -q`); candidate diff to `test_schedule.py` is purely additive (no existing test modified), full suite at candidate: 49 passed/44 skipped with system python (no pytz), 93 passed with the pytz-enabled venv.
- **C5 PASS** — `black==20.8b1 --check .`: "4 files would be left unchanged"; `mypy -p schedule`: "Success: no issues found in 1 source file"; full suite with pytz installed: 93 passed, 0 failed/skipped.
- **C6 PASS** — README.rst, docs/examples.rst and HISTORY.rst all updated with the new `every().weekday.at("09:00").do(job)` example; `repr()` of a weekday job reads "Every weekday at 09:00:00 do job_fun() (last run: [never], next run: 2010-01-08 09:00:00)" (verified via `test_weekday_repr` and matches the recorded decision).

### Test run:
```
$ python3 -m pytest -q
ss.ssss.................sss.ss.....................sssssssssssssssssssssss [ 77%]
ssssssssssss.........                                                       [100%]
49 passed, 44 skipped in 0.38s

$ /tmp/orch-weekday-venv/bin/python -m pytest -q -p no:cacheprovider
........................................................................ [ 77%]
.....................                                                    [100%]
93 passed in 0.16s

$ /tmp/orch-weekday-venv/bin/black --check .
All done! ✨ 🍰 ✨
4 files would be left unchanged.

$ /tmp/orch-weekday-venv/bin/python -m mypy -p schedule
Success: no issues found in 1 source file
```

### Findings:
1. **Observation** — Cross-timezone weekday judged in `at()`'s zone, not the machine's local zone (`schedule/__init__.py:774-777`, weekday-skip applied to the tz-aware `next_run` before `_correct_utc_offset`/local conversion). Reproduction: system local time Fri 2010-01-08 12:00 (Berlin-equivalent), `every().weekday.at("20:00", "America/New_York").do(job)` → `next_run` local wall-clock is `2010-01-09 01:00` (a Saturday, `weekday()==5`). This is a literal instance of "next_run is a Saturday," which the plain-language request's "never on Saturday or Sunday" would forbid. However, this exact behavior is a **recorded main-session decision** ("day of week is judged in the `at()` timezone... consequence: the run's local calendar day can be Sat/Sun in cross-zone setups"), explicitly covered by the test `test_tz_weekday_judged_in_given_timezone`, so per the review brief's rule ("...unless the request or a recorded user decision accepts the exception") this is not classified as blocking. Flagging only so it's visible: a user relying on "never Sat/Sun" in their own local wall-clock across the DST/tz boundary case could still observe a Saturday/Sunday run. Smallest correction if the main session wants strict local-only semantics: judge weekday-ness after `_correct_utc_offset`+`astimezone()` conversion to local time rather than before it — but that would itself be a policy change requiring a new decision, not a code defect per current decisions.

No other findings — patch is minimal, additive, reuses the daily/tz/DST `_schedule_next_run` path as decided, does not touch `to()`, `until()`, `tag()`, or non-weekday `__repr__`/`__str__` behavior, introduces no new dependencies, no CI config edits, no secrets/network calls.

### Not verified:
- Full CI matrix across Python 3.7–3.12 (only tested against the system interpreter and the provided venv's interpreter version) — no multi-version toolchain available in this environment.
- Sphinx docs build with `-W` (not run; `Sphinx` was present in the venv listing but I did not invoke a docs build) — low risk since the only doc changes are one bullet in HISTORY.rst and one code line each in README.rst/examples.rst, both plain reST consistent with surrounding content.
- `black`/`mypy` were run only via the provided pre-built venv, not built fresh from scratch, per the task's instruction not to install into the shared environment.