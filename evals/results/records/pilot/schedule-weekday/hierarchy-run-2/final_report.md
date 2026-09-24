## Result: done

`schedule.every().weekday.at("09:00").do(job)` now runs Monday to Friday at 09:00 and skips Saturday and Sunday. The existing suite still passes, and an independent verifier and a re-checker both confirmed all six acceptance criteria.

- **Built:**
  - A new `weekday` option in `schedule/__init__.py`. It works like `every().day`, but the next run is moved past Saturday and Sunday.
  - When a timezone is given with `.at("09:00", "America/New_York")`, the weekday is judged by the date in that timezone.
  - A job printed with `repr` reads "Every 1 weekday at 09:00:00 do job()".
  - 9 new tests in `test_schedule.py`, plus one example line in `docs/examples.rst`.
- **Acceptance criteria:** 6/6 verified. The cases covered are:
  - the 09:00 boundaries on Monday and Friday, including exactly Friday 09:00, which goes to Monday;
  - Saturday and Sunday both go to Monday;
  - a week-long simulation runs on the 23rd to 27th, then the 30th, with no weekend runs;
  - use without `.at()`;
  - the error cases, and the `repr` output.
- **Tests:** `python3 -m pytest -q` → 49 passed, 43 skipped (before: 40 passed, 41 skipped).
  - The skips are because `pytz` isn't installed here, as before. The 2 new skips are timezone tests that need it.
  - In a separate environment in my scratch folder with `pytz` installed: 92 passed.
  - Formatting with black 20.8b1, the version CI pins, is clean, and the `mypy` type check is clean. No tests that existed before were changed.
- **Iterations:** the first verification passed but found three things, all fixed in one round and re-checked:
  - A line was too long for black, which would have failed CI's formatting job.
  - A unit written before `.weekday` was accepted silently. For example, `every().hour.weekday` became a once-a-day job with no error. It now raises an error.
  - No test covered the timezone or daylight-saving behaviour. Two were added, and one was shown to fail if the weekday were judged in local time.
- **Decisions I made:**
  - Only a plain `every()` is allowed; `every(2).weekday` raises `IntervalError`.
  - Combining `.weekday` with another unit or a named day (`.hours`, `.monday`, …) raises `ScheduleValueError`, so it can never quietly run on a weekend.
  - Without `.at()`, it runs at the current time of day on the next weekday, the same as `every().day`.
  - I added no HISTORY entry and installed nothing into the system Python.
- **Open items:**
  - If `run_pending()` isn't called between Friday 09:00 and Saturday (say the machine was asleep), Friday's late run fires on Saturday. This is how the library already treats late jobs, and `every().monday` does the same. Say if "never on Saturday" should also cover late runs.
  - One daylight-saving case isn't handled: a clock jump that crosses Friday midnight into Saturday. No real timezone was found that does this.
- **Not verified:** none.
- **Branch:** `orch/weekday` from `main` at 82a43db, with commits e44795b and 5d9f00e. Not pushed. To take it: `git merge orch/weekday`
- **Mode:** Lite. One Haiku worker built it, a Sonnet worker did the fix round, and the checks were an Opus verifier and a Sonnet re-checker.
- **Cost:** about $3.90, above the $2–3 estimate, because of the fix round.

The plan, notes, worker reports and patches are kept in `.orchestrator/`, as you asked; the summary is `.orchestrator/report.md`.