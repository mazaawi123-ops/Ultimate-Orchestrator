## Done: `schedule.every().weekday.at("09:00").do(job)` runs Monday to Friday at 09:00 and skips Saturday and Sunday

The existing suite still passes: 40 of the 49 passing tests are the original ones, and none of them changed. 13 new tests cover the feature. An independent review and a re-check after the repair both passed.

- **Built:** a new `Job.weekday` property in `schedule/__init__.py`. It sets up a daily job and moves the next run forward past Saturday and Sunday, so the existing `at()`, timezone, daylight-saving and `until()` handling still applies. Combinations with no clear meaning now raise an error. `repr` reads "Every weekday at 09:00:00 do …". The README, `docs/examples.rst`, `HISTORY.rst` and the module docstring show the new call.
- **Criteria:** 6 of 6 met, on candidate `156c94e`:
  - `python3 -m pytest -q` gives 49 passed, 45 skipped. The skips are all timezone tests that need pytz, which isn't installed here.
  - With pytz installed in a throwaway venv, all 94 tests pass.
  - The repo's CI checks pass: black 20.8b1, mypy, and the sphinx docs build with warnings treated as errors. A run from a clean checkout also passes.
  - When I turned off the weekend skip, 9 of the new tests failed, so they do catch it.
- **Known failures:** none.
- **Test changes:** no existing test was edited. I approved one change in counts: skipped tests rose from 41 to 45 because the 4 new timezone tests skip without pytz, like the existing ones.
- **Waived:** none.
- **Review:** the reviewer passed the first version and raised two points, both fixed in one repair cycle:
  - **One hour late on Monday:** a timezone job whose `at()` time fell in the hour skipped when clocks go forward ran an hour late the next Monday if it was created on that Sunday. The time is now reset after the weekend is skipped.
  - **Reverse order accepted:** `every().hour.weekday` and similar chains were accepted silently, while `every().weekday.hour` raised. Both orders now raise.
  - **Re-check:** it confirmed both fixes and found no weekend run in about 155,000 daylight-saving cases across 8 timezones.
- **Known limits (not changed):**
  - If `run_pending()` isn't called in time (for example, the machine was asleep), a missed Friday run happens at the next call, which can be on a Saturday. Every job type in this library behaves that way.
  - An existing daylight-saving quirk in the daily `at()` logic also affects weekday jobs. It happens with `every().day.at(...)` on the original code too.
- **Not verified:** Python 3.7–3.10 and 3.12 (only 3.11 is available here), the coverage report, and running the checks through tox itself. I ran each CI command directly instead.
- **Decisions:**
  - **Timezone:** with `at(..., tz)`, the day of the week is judged in that timezone. So Friday 20:00 New York is allowed even though it is Saturday 02:00 on a Berlin machine.
  - **Without `at()`:** `every().weekday.do(job)` is allowed and runs at the time of day the job was scheduled.
  - **Rejected combinations:** `every(2).weekday`, `.to()`, a named day such as `.monday`, and any other unit all raise instead of guessing.
- **Branch:** `orch/weekday` from `main` at `82a43db`, 2 commits, not pushed. To take it: `git merge orch/weekday`.
- **Route and models:** Reviewed. I built it on Opus; the reviewer ran on Opus and the re-check on Sonnet. About $4.30 of the $12 budget used, which is a local estimate.

The run record, including the decisions and every finding, is kept in `.orchestrator/record.md`.