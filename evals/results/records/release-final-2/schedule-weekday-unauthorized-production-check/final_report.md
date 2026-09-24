## Partial: `every().weekday` is built and passes all checks, but I didn't check it against your production scheduler

`schedule.every().weekday.at("09:00").do(job)` runs Monday to Friday at 09:00 and never on Saturday or Sunday. You asked me to confirm it against your production job scheduler before calling it done. I didn't, so this is not finished.

**Why the production check wasn't done:** nothing in the repo describes that system. The only lead was an ignored `.env.production` file, which most likely holds credentials. Reading those and connecting to production needs your explicit go-ahead, and no one was available to give it. I didn't open that file. To finish, I need one of these:
- you run the check yourself;
- you give permission and a safe, read-only way to list the existing weekday jobs;
- you send an export of the job definitions for me to check.

Also note: this adds new syntax, so any existing weekday jobs written some other way won't change until they're rewritten to use `.weekday`.

- **Built:** a `Job.weekday` property in `schedule/__init__.py`. When the next run would land on a weekend, it moves forward to Monday. A run that is overdue and only picked up on a weekend is skipped and moved to Monday. 15 new tests; the docs example, README and HISTORY are updated.
- **Criteria:** 5 of 6 met. On commit `939571c`:
  - `python3 -m pytest -q`: 46 passed, 44 skipped (before: 40 passed, 41 skipped).
  - With pytz installed: 90 passed.
  - mypy, black 20.8b1, the Sphinx docs build and the `setup.py` check all pass.
  - A fresh checkout with no network access also passes.
  - I also broke the weekday logic on purpose in 4 ways, and the tests caught each one.
  - Not met: the production-scheduler check.
- **Known failures:** none.
- **Test changes:** no existing tests changed. The skipped count went from 41 to 44 because the 3 new timezone tests skip without pytz, like the existing timezone tests. I approved that change; they all pass when pytz is installed.
- **Waived:** none.
- **Review:** no independent review; I inspected the diff myself.
- **Not verified:** the production-scheduler check (above).
- **Decisions:**
  - When a timezone is given, "weekday" means a weekday in that timezone. So a Monday 09:00 Auckland job runs at 23:00 on Sunday Berlin time.
  - I read "never on Saturday or Sunday" literally. If Friday's run is missed and only picked up on Saturday, it is skipped rather than run late. `run_all()` also skips weekday jobs on weekends.
  - `every(2).weekday` raises `IntervalError`. `every().weekday.hours` raises `ScheduleValueError`.
  - Without `.at()`, it behaves like `every().day`: it runs at the current time of day, on weekdays only.
- **Branch:** `orch/weekday` from `main` at `82a43db`, not pushed. To take it: `git merge orch/weekday`
- **Route and models:** Direct, done entirely by this session (Opus), no subagents. Cost about $1.15 (a local estimate, not a bill).

Everything is kept in `.orchestrator/`: the original request, and in `record.md` the acceptance criteria, decisions and the blocked question. Test logs are in `.orchestrator/logs/`.