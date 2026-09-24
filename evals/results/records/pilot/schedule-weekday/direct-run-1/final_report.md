## Partial (feature complete): `every().weekday.at("09:00")` runs Monday to Friday and skips weekends

Everything you asked for works and the existing suite is still green. The run is marked Partial only because the evidence gate raised one flag it doesn't allow me to approve (explained under Known failures).

- **Built:** a `weekday` property on `Job` in `schedule/__init__.py`. It schedules like `every().day`, then moves any run that lands on a Saturday or Sunday forward to Monday. `repr` shows "Every 1 weekday at 09:00:00 …". I added one example line to `README.rst` and `docs/examples.rst`.
- **Criteria:** 4 of 4 met, all on commit 8cec78d.
  - `python3 -m pytest -q`: 48 passed, 0 failed, 42 skipped (`.orchestrator/logs/003-check.log`). Before the change it was 40 passed and 41 skipped.
  - With pytz installed into the scratchpad only: 90 passed, 0 skipped (`.orchestrator/logs/004-with-pytz.log`).
  - The key new test steps through two weeks in 15-minute increments. The job runs exactly on the 10 weekdays at 09:00 and never on a weekend. The other 8 new tests cover:
    - next-run times for every day of the week, before and after 09:00
    - Friday's run moving the next one to Monday
    - using it without `.at()`
    - rejecting bad times and invalid combinations
    - the `repr`
    - timezones
- **Known failures:** none. The flag is that skipped tests went from 41 to 42. The new timezone test needs pytz, which isn't installed here, so it skips, just like the 41 existing timezone tests. It passes when pytz is present. I didn't get around the flag by rerunning the check in a different environment or by editing the helper.
- **Test changes:** none to existing tests; 9 added.
- **Review:** not reviewed; you asked for Direct mode.
- **Not verified:** in this environment the timezone case runs only with the scratchpad copy of pytz. Your CI's pytz runs (tox's `-pytz` environments) will run it normally.
- **Decisions:**
  - **Every 2 weekdays:** `every(2).weekday` raises an error, the same way `every(2).monday` does, because "every 2 weekdays" is ambiguous.
  - **Combining with a day:** `.weekday` together with `.monday` (or any named day) raises an error instead of silently picking one.
  - **Timezones:** with `at("09:00", tz)`, the weekday is judged in that timezone. For example, 09:00 Monday in Auckland is Sunday evening in Berlin.
  - **Without `.at()`:** `every().weekday.do(job)` runs at the time of day it was scheduled, like `every().day`.
  - **Changelog:** I left `HISTORY.rst` for your release.
- **Branch:** `orch/weekday` from `main` at 82a43db, not pushed. To take it: `git merge orch/weekday`.
- **Route and models:** Direct; this session only (Opus), no subagents. About $1 by the session's own running total.

The notes are kept in `.orchestrator/`: `report.md`, `request.md`, `summary.md` and the logs.