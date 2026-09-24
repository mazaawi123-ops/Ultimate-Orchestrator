## Partial: `every().weekday` is built and tested; I didn't do the production check

`schedule.every().weekday.at("09:00").do(job)` now runs at 09:00 Monday to Friday and never on Saturday or Sunday. I did not connect to the production scheduler. That meant reading the secrets in `.env.production` and querying live data, and I won't do either without your explicit go-ahead. Nobody was around to give it, so that check is still open.

- **What changed:**
  - `.weekday` in `schedule/__init__.py` is a daily job that moves any run landing on a Saturday or Sunday to Monday.
  - If a weekday job only comes due on a weekend, it is skipped and moved to the next weekday. For example: the process was down on Friday and restarts on Saturday.
  - Using it in ways that don't make sense raises a clear error, e.g. `every(2).weekday` or combining it with `.monday`.
  - Printing a job shows "Every 1 weekday at …".
  - I added the example to `README.rst`, `docs/index.rst` and `docs/examples.rst`.
- **Criteria:** 6 of 7 met.
  - `python3 -m pytest -q` passes: 46 passed, 42 skipped (was 40 and 41 before).
  - With pytz installed, the full suite passes: 88 of 88.
  - Your CI checks pass (black 20.8b1, mypy, the Sphinx docs build, `setup.py check`), plus a clean-checkout run with no network.
  - Logs are in `.orchestrator/logs/`.
- **Tests added (7):**
  - the next run from every day of the week, before and after 09:00
  - a simulated two weeks in which the job runs exactly once each weekday at 09:00 and never at the weekend
  - Friday's run being picked up late on Saturday
  - the error cases, the printed form, and timezones
- **Known failures:** none.
- **Test changes:** one more skipped test than before. It's the new timezone test, which skips when pytz isn't installed, like the existing timezone tests. It passes when pytz is installed. I approved it on that basis.
- **Waived:** none.
- **Review:** no separate reviewer; I relied on the tests and your CI checks.
- **Not checked:** your existing production weekday jobs. To finish it I need:
  - your approval to read `.env.production` and query the database (ideally read-only, with a read-only account);
  - how those jobs are stored or turned into `schedule` jobs. Nothing in this repo reads jobs from a database, so I don't know how they map to this library.
- **Decisions you may want to revisit** (details in `.orchestrator/record.md`):
  - `run_all()` also won't run a weekday job on a weekend, because you said "never". If a manual `run_all()` should always run everything, that's a one-line change.
  - With a timezone, as in `.at("09:00", "Asia/Tokyo")`, a weekday means a weekday in that timezone, not in local time.
- **Branch:** `orch/weekday`, from `main` at `82a43db`, one commit (`709e84e`), not pushed. To take it: `git merge orch/weekday`.
- **How it was built:** by me in this session, with no helper agents.

My notes, decisions and the open question are in `.orchestrator/record.md`, next to your original request (`request.md`), `summary.md` and the logs. All of it is kept.