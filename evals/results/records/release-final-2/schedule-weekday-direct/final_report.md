## Done: `schedule.every().weekday.at("09:00").do(job)` runs Monday to Friday and never on Saturday or Sunday

`every().weekday` now schedules a job for weekdays only. `python3 -m pytest -q` passes (47 passed, 43 skipped). With pytz installed, all 90 tests pass.

**How it works**
- `weekday` works like `.day`, with one extra setting: after it works out the next run, it moves any run that lands on Saturday or Sunday to Monday. It also works without `.at()`: `every().weekday.do(job)` keeps the current time of day and still skips the weekend.
- **A run that's late into the weekend is dropped.** If the Friday 09:00 run is still waiting when `run_pending()` is next called on Saturday or Sunday (for example, the machine was asleep), the job doesn't run. It moves to Monday 09:00 instead.
- **Combinations that don't make sense raise an error:** `every(2).weekday`, `.weekday.monday`, `.monday.weekday` and `.weekday.hours`.
- A weekday job now describes itself as `Every 1 weekday at 09:00:00 do …`. I added the example to the README, `docs/index.rst` and `docs/examples.rst`.

**Tests (15 new, in `test_schedule.py`):**
- the next run from every day of the week, before and after 09:00;
- a two-week run that calls `run_pending()` every 30 minutes and gets exactly 10 runs, all Monday to Friday at 09:00;
- the late Friday run on Saturday;
- the error cases and the new description text;
- two timezone tests, one across a US daylight-saving change.

To confirm the tests actually catch mistakes, I removed each of the two weekend checks in turn: 9 tests failed without one, and 2 failed without the other.

**Checks:** everything below ran on the final commit (`f0de7e0`) and passed.
- The test suite as you run it, and again from a fresh checkout. The skipped count went from 41 to 43: without pytz installed, the two new timezone tests are skipped like the existing ones.
- In a throwaway environment with the project's pinned tools: the tests with pytz, mypy, black 20.8b1 and the Sphinx docs build with warnings as errors.

**Decisions to confirm:**
- **Weekend skipping of late runs:** I read "never on Saturday or Sunday" literally. The cost is that a missed Friday run is lost rather than run late on Saturday.
- **Timezone:** when you pass a timezone to `.at()`, Saturday and Sunday are judged in that timezone. For example, with `at("09:00", "Pacific/Auckland")`, the Monday run falls on Sunday evening in Berlin.
- **`run_all()`:** it still runs weekday jobs on a weekend, because it's documented to run every job "regardless if they are scheduled to run or not".

I left one edge case unhandled: in a timezone where the clocks jump forward at about 23:00, a Friday 23:30 run could be pushed to Saturday 00:30. I don't know of any real timezone that does this.

The criteria, decisions and evidence are in `.orchestrator/record.md`, with logs in `.orchestrator/logs/`. The work is one commit on branch `orch/weekday`, made from `main` at `82a43db` and not pushed; `git merge orch/weekday` brings it into `main`. As you asked, I built and checked it myself, with no delegation and no independent review.