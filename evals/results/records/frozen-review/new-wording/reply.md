### Verdict: FAIL

The candidate works when the job fires on time. It can still run the job on a Saturday or Sunday when the run is late, and the request says "never".

### Criteria
- **C1: PASS.** It holds for the request's case. I created a job at 1,440 start times across a full week, one every 7 minutes, with no timezone: 0 mismatches against a brute-force "next Mon–Fri 09:00 strictly after now". I did the same for 7 timezones (Tokyo, New York, Berlin, Sydney, Kiritimati, Pago Pago, Kolkata) and for DST-change weeks in New York, Berlin and Sydney: 0 mismatches at 09:00. One edge fails: an `at` time inside a DST gap, with a timezone given (finding 3).
- **C2: PASS as written, FAIL against the request.** `next_run` never landed on Sat/Sun in any sweep. Thirty repeated runs landed only Mon–Fri, with and without `at()`. The request's "never" is about when the job runs, though, and a late run executes on the weekend (finding 1). The criterion only checks `next_run`, so it misses this.
- **C3: FAIL (partial).**
  - These are all rejected: `every(2).weekday` and `every(0).weekday` (IntervalError), `.weekday.<day>` and `.<day>.weekday` for all 7 days, `.weekday.<unit>` for every non-day unit, and `.to()` in either order. All raise ScheduleError subclasses, and the job is not added.
  - These are silently accepted as a once-a-day weekday job: `.hour.weekday`, `.hours.weekday`, `.minute(s).weekday`, `.second(s).weekday` and `.week(s).weekday` (finding 2).
- **C4: PASS.** BASE gives 40 passed / 41 skipped, the candidate 49 passed / 44 skipped, so the 12 new tests are 9 passing plus 3 timezone tests that skip without pytz. `git diff` removes no lines from `test_schedule.py`.
- **C5: PASS.** In the venv: pytest 93 passed; `black --check .` reports "4 files would be left unchanged"; `mypy -p schedule` reports "no issues found". The Sphinx `-W` docs build succeeds, and `setup.py check --strict --metadata --restructuredtext` exits 0. All ran on a `git archive` copy.
- **C6: PASS.** README, `docs/examples.rst` and HISTORY mention the new API, and the property's docstring shows up in the built reference page. `repr` reads `Every weekday at 09:00:00 do job() (last run: [never], next run: 2010-01-08 09:00:00)`, and without `at()` it reads `Every weekday do job() ...`. `str` is unchanged (`Job(interval=1, unit=days, ...)`), as decided.

### Test run
```
python3 -m pytest -q                        -> 49 passed, 44 skipped in 0.34s   (BASE: 40 passed, 41 skipped)
venv pytest -q (pytz)                       -> 93 passed in 0.18s
black==20.8b1 --check .                     -> All done! 4 files would be left unchanged.
mypy -p schedule                            -> Success: no issues found in 1 source file
sphinx-build -W -b html (docs)              -> build succeeded.
```
The working tree is clean at f142db5.

### Findings

**1. Blocking: a late run executes on Saturday or Sunday.**
- **Violates:** the request's "never on Saturday or Sunday". The new docstring at `schedule/__init__.py:470` also claims "it never runs on a Saturday or Sunday".
- **Location:** `schedule/__init__.py:695-700` (`should_run` is just `now >= next_run`) and `:702-719` (`run()` has no weekend check).
- **Reproduction:** `$S/repro_late.py`, where `$S` is my scratchpad.
  - A: a job created with `every().weekday.at("23:59:59")` on Friday, then `run_pending()` at Sat 00:00:00 (one second late, the normal outcome of a `sleep(1)` loop). The job runs on Saturday.
  - B: `at("09:00")`, and the process is blocked or asleep until Sat 10:00. The job runs on Saturday, then reschedules to Monday.
  - C: the same, with the first check on Sunday 15:00. The job runs on Sunday.
  - D: `run_all()` on a Saturday also runs it, through the same `run()` path.
- **Impact:** any missed Friday run, or any weekday run late enough to cross midnight, fires on the weekend. That is the exact case the user excluded.
- **Smallest fix:** in `Job.run()`, after the overdue check, if `self.weekdays_only` and `datetime.datetime.now(self.at_time_zone).weekday() >= 5`, call `self._schedule_next_run()` and `return None` without running the job. Add a test: created Friday at 23:59:59, checked Saturday at 00:00:00, not called, `next_run` is Monday. I applied this to a scratch copy: A to D no longer run, and both suites stay green (49/44 and 93). If `run_all()` should still force weekend runs, the main session should record that as a decision.

**2. Blocking against C3: `.weekday` after a non-day unit is silently turned into a daily job.**
- **Violates:** C3, which says `.weekday` with a non-day unit must fail loudly. The request text itself doesn't ask for this; C3 does.
- **Location:** `schedule/__init__.py:482`. The `weekday` property overwrites `unit` by returning `self.days`. The check at `:737` only sees the final unit, so it catches `.weekday.hours` but not `.hours.weekday`.
- **Reproduction:** `every().hour.weekday.do(job)` raises nothing and produces `Every weekday do job()`, with `unit=days` and one run per day. The same happens with seconds, minutes and weeks, in singular and plural (`$S/repro_edges.py`).
- **Impact:** `every().hour.weekday` is a natural way to write "hourly on weekdays", and it silently runs once a day instead.
- **Smallest fix:** at the start of the property, raise ScheduleValueError when `self.unit not in (None, "days") or self.start_day is not None`. Verified in the scratch copy: all such chains now raise, and the suites stay green.

**3. Optional improvement: a DST-gap `at` time is carried into Monday one hour late.**
- **Violates:** C1 ("next Mon–Fri at the at-time"), but only at this edge. The request's 09:00 is unaffected.
- **Location:** `schedule/__init__.py:774-779`. The weekend skip adds days to a time that `_move_to_at_time` has already moved out of Sunday's DST gap.
- **Reproduction:** `$S/repro_gap.py`.
  - `every().weekday.at("02:30", "Europe/Berlin")` created Sun 2023-03-26 00:35 CET gives Mon 03:30 CEST. It should be 02:30.
  - `at("02:15", "America/New_York")` created Sun 2024-03-10 01:00 EST gives Mon 03:15 EDT.
  - `every().day` gets Sunday right, so this is specific to weekday jobs. EU and US DST starts on Sundays, which are the days a weekday job skips.
- **Impact:** one run an hour late. It needs a timezone, an `at` time in 02:00–02:59, and a job created on DST-start Sunday before the gap. Later runs correct themselves.
- **Smallest fix:** after the skip loop, `next_run = self._move_to_at_time(next_run)`. Verified in the scratch copy: both cases give 02:30 and 02:15, and the suites stay green.

**4. Observation: the timezone rule is the main session's decision, not the user's.**
- With a timezone given, the day of the week is judged in that timezone, so a Fri 20:00 New York run falls on Saturday 02:00 on a Berlin machine. The candidate's own test `test_tz_weekday_judged_in_given_timezone` asserts exactly this.
- It's a coherent reading: the other choice would run on Sunday in New York. But the user never accepted this exception to "never".
- It is documented only in the property's docstring, not in README, `docs/examples.rst` or `docs/timezones.rst`.
- It is worth recording for the user, and mentioning in the docs if kept.

**5. Observation: the weekend check runs before the timezone offset correction.**
- **Location:** `schedule/__init__.py:774-779`. The check happens before `_correct_utc_offset`, which can move the date.
- **Historical reproduction:** `every().weekday.at("09:00", "Pacific/Apia")` created Thu 2011-12-29 10:00 local gives `next_run` Sat 2011-12-31 09:00 +14. Samoa skipped Friday 30 December that year.
- I found no zone in current timezone data where this can happen for a future date. The run-time guard from finding 1 would cover it anyway.

### Not verified
- Python 3.7–3.11 and the full tox/CI matrix. I only ran the system python3 and the one venv interpreter.
- Coveralls, which needs network.
- Real wall-clock runs. All timing checks used the repo's `mock_datetime`.
- Finding 2's fix only in the order the user writes the chain. I didn't look for other valid chains the new check would reject beyond the existing tests and the combinations listed above.

The scratch scripts (`repro_late.py`, `repro_edges.py`, `repro_tz.py`, `repro_gap.py`) and the patched copy (`fix/`) are kept in my scratchpad, `<workspace>/`.