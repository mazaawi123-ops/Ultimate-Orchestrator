## Partial: `every().weekday` is built, tested and reviewed; the run gate won't sign it off only because one new test is skipped

`schedule.every().weekday.at("09:00").do(job)` runs Monday to Friday at 09:00 and never on Saturday or Sunday. The feature works and all criteria are met. I'm reporting Partial only because the run's final gate refuses "done" (explained below).

**Built**
- `Job.weekday` works like `.monday`: it makes the job daily, and the next-run calculation skips Saturday and Sunday. It's in `schedule/__init__.py`.
- If a run is missed and the scheduler next checks on a weekend (for example, it doesn't poll on Friday but does on Saturday), the job doesn't run late on the weekend. It moves to Monday, and a `.until()` deadline still applies.
- I added 11 tests to `test_schedule.py` and a one-line example to `README.rst`, `docs/index.rst` and `docs/examples.rst`.

**Evidence** (final version, commit `8e0fcec`)
- **Your test command:** `python3 -m pytest -q` gives 51 passed, 42 skipped. The 41 existing skips are pre-existing, because pytz isn't installed here.
- **With pytz:** in a scratchpad virtual environment, all 93 tests pass, including the new timezone test.
- **Formatting:** the project's CI formatting check (`black --check .`, using the pinned black 20.8b1) passes.
- **Tests catch breakage:** I deliberately broke each piece of the implementation in turn, and the new tests failed each time.
- **Existing tests:** none were changed.

**Why it's Partial:** the gate objects only because the skipped-test count went from 41 to 42. The new `test_tz_weekday` needs pytz, so it skips here like the 41 existing timezone tests, and passes when pytz is installed. The gate has no way to approve a rise in the skip count, and deleting or hiding a correct test to satisfy it would be wrong, so I left it in.

**Review:** an independent reviewer passed all 7 criteria. It flagged three non-blocking issues, and I fixed all three in the one repair round I used (of the 2 allowed):
- The change failed the CI formatting check; it now passes.
- The weekend skip ignored a `.until()` deadline; it now honours it, with a test.
- One error message didn't mention `.weekday`; it now does.

A second reviewer confirmed all three were fixed.

**Not verified:** I only ran Python 3.11, not the other versions CI tests, and every check used simulated clocks, not the real one.

**Decisions I made for you** (all recorded in `.orchestrator/record.md`):
- **Missed run found on a weekend:** it is skipped, not run late, including when you call `run_all()` on a weekend. I read "never on Saturday or Sunday" strictly.
- **Missed run found on a weekday:** it still runs late, like `every().day` does. So if Friday's run is first noticed at Monday 08:00, it runs then and again at 09:00.
- **Without `.at()`:** the job runs each weekday at the time it was scheduled.
- **With a timezone:** Monday to Friday is judged in the timezone passed to `.at()`.
- **Invalid combinations raise an error instead of guessing:**
  - `every(2).weekday`
  - `.weekday` combined with a named day such as `.monday`
  - `.weekday` combined with a unit other than days
  - `.weekday` combined with a random interval (`.to()`)

**Branch:** `orch/weekday`, from `main` at `82a43db`, 5 commits, not pushed. To take it: `git merge orch/weekday`. The run's notes and logs are kept in `.orchestrator/`.

**How it was run:** Reviewed mode. I built it myself (Opus), one independent reviewer (Opus) checked it, and a second (Sonnet) re-checked the fixes. About $3 of the $12 budget was used, by local estimate.