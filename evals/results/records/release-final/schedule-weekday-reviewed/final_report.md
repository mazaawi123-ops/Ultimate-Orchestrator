## Done: `schedule.every().weekday.at("09:00").do(job)` now runs Monday to Friday only

All 8 criteria pass on the final commit `22f1204` (none of them needs a manual check). `python3 -m pytest -q` gives 49 passed, 43 skipped; the skipped tests need `pytz`, which isn't installed here. With `pytz` installed, all 92 tests pass.

**What I built:** a new `weekday` property in `schedule/__init__.py`. It works like `day` and additionally skips Saturday and Sunday. I added 11 tests and one example to `docs/examples.rst`. No existing test was changed.

- **Next run:** from any starting moment, the next run is the next Monday to Friday at the given time. A job scheduled on a Friday afternoon or over the weekend next runs Monday at 09:00.
- **Three-week simulation:** checking every 15 minutes, the job runs exactly 15 times, once each weekday at 09:00, and never on a weekend day.
- **Missed Friday run:** if the job becomes due on a Saturday or Sunday, it is skipped and moved to Monday instead of running. That covers `run_pending()` not being called until Saturday, and `run_all()` being called on a weekend. `until()` still cancels the job as usual.

**Checks:** the tests with and without `pytz`, `black --check` (20.8b1, as in CI), `mypy -p schedule`, the docs build with warnings treated as errors, and a run from a clean checkout. All passed on `22f1204`. I ran them in a throwaway virtual environment in the scratchpad; nothing was installed into the system.

**Test changes:**
- The number of skipped tests went from 41 to 43. The two new timezone tests skip without `pytz`, like the existing ones, and pass when it's installed.
- My first commit accidentally edited two existing test lines while I was fixing my own test. I reverted them in the next commit, so the final diff doesn't touch any existing test.

**Review:**
- The independent reviewer passed the first version with no blocking findings, after about 8,400 checks against a reference answer and over 16,000 randomised runs with no weekend runs. It suggested two improvements, and I fixed both in the single repair round used (of 2 allowed):
  1. With a timezone, a job set inside the hour a daylight-saving change skips (for example 02:30) ran an hour late on the Monday after that weekend. It now runs at the set time.
  2. `every().weekday.to(3)` was accepted but ran on random weekdays. It now raises an error.
- A second reviewer re-checked the fixes and passed them. It also found that a job created on the day of a daylight-saving change runs twice the next Monday (01:30 and 02:30). Plain `every().day` does the same in the original code, so this change didn't cause it, and it never runs on a weekend. I left it as a possible follow-up.

**Decisions I made without you (all recorded in `.orchestrator/record.md`):**
- **Late runs:** because you said "never", a job that becomes due on a weekend is skipped, including under `run_all()`. The cost is that a Friday run missed because the process was paused waits until Monday instead of catching up.
- **Timezones:** with `.at("09:00", "Some/Zone")`, "weekday" means a weekday in that zone. In your local time the run can fall on a Saturday or Sunday.
- **Errors:** `every(2).weekday` raises `IntervalError`, and combining `weekday` with `hours`, `minutes`, `weeks`, a named day or `.to()` raises `ScheduleValueError`. The exception is `every().hours.weekday`, which follows the library's existing "last unit wins" rule and becomes a normal weekday job.
- **Without `.at()`:** `every().weekday.do(job)` runs each weekday at the time of day it was scheduled, like `every().day`.
- **Display:** a job prints as `Every weekday at 09:00:00 do job() (...)`.
- **Changelog:** I didn't edit `HISTORY.rst` because its entries are tied to release versions.

**Not verified:** Python versions other than 3.11 (CI tests 3.7 to 3.12), and CI's `setup.py check`, which this change doesn't touch.

**Branch:** `orch/weekday`, from `main` at `82a43db`. It isn't pushed; to take it, run `git merge orch/weekday`. The run record, review and logs are kept in `.orchestrator/`, and the reviewers' test scripts are in the scratchpad under `review/`.

**How it ran:** Reviewed mode. I (Opus) built it, `orch-verifier` did the review, and `orch-rechecker` re-checked the fixes. Local estimated cost was about $4.30 of the $12 budget.