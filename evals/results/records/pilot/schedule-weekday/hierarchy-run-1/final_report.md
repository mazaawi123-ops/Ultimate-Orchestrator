## Result: done

`schedule.every().weekday.at("09:00").do(job)` now runs Monday to Friday at 09:00 and never on Saturday or Sunday. The full suite passes and an independent verifier checked the change.

- **Built:**
  - A `Job.weekday` property in `schedule/__init__.py`. It works like a daily job and pushes any run that would land on a weekend to the next Monday.
  - A job that was due on Friday but first gets checked at the weekend is not run then; it moves to Monday at 09:00. `run_all()`, which runs every job on request, still runs it.
  - The job's display text reads "Every 1 weekday at 09:00:00 …", and there's a docs example in `docs/examples.rst`.
  - 8 new tests in `test_schedule.py`.
- **Acceptance criteria:** 7/7 checkable ones verified. The timezone one (AC8) was also checked, but only with a pytz stand-in, because pytz isn't installed here.
- **Tests:** `python3 -m pytest -q` → 47 passed, 42 skipped (was 40 passed, 41 skipped). The skipped tests all need pytz. With the stand-in on `PYTHONPATH`, all 89 pass.
- **Lint:** `black --check schedule` is clean. `test_schedule.py` still has the same 6 black-style differences it had before; none are new. Clean-room: not needed, since nothing calls an external service.
- **Iterations:**
  1. The first build passed every criterion.
  2. The verifier then found that a missed Friday run could still fire on Saturday, if `run_pending` was first called at the weekend. That breaks "never on Saturday or Sunday", so a fix round added a weekend guard in `Job.should_run`.
  3. The same round added the missing timezone test (the verifier had shown the suite couldn't catch weekend days judged in local time instead of the job's timezone) and gave the docs line its own comment.
  4. The re-check passed, and confirmed the new timezone test catches that local-time bug.
- **Rulings I made:**
  - It's a daily job plus a `weekdays_only` flag, reusing the existing daily time parsing and daylight-saving handling.
  - `every(2).weekday` raises `IntervalError`. Combining `weekday` with a specific day (`.monday`), `.hours`, or `.to()` raises `ScheduleValueError`.
  - With no `.at()`, it runs daily at the time it was scheduled and skips weekends.
  - When a timezone is given, "weekday" is judged in that timezone, not local time.
  - A missed weekday run is dropped at the weekend rather than run late.
  - `str(job)` still shows `unit=days`. There is no `weekdays` alias and no `HISTORY.rst` entry.
- **Open items (nits I accepted):**
  - A weekday job whose `until()` deadline passes over a weekend stays in the job list until Monday. It is then cancelled without running.
  - `every().hours.weekday` acts as a plain weekday job, because the last unit property wins, the same as `.hours.day` today.
  - `every().monday.weekday` raises the right exception type, but with the older message "`unit` should be 'weeks'".
  - In historic timezone jumps that skipped whole days (Apia 2011, Pyongyang 2018), a run could land on a weekend. Plain daily jobs behave the same way.
- **Not verified:** timezone behaviour against real pytz. Your CI, which installs pytz, will run `test_tz_weekday`.
- **Branch:** `orch/weekday` from `main` at `82a43db`, with two commits (`7023bdf`, `051456c`). Not pushed. To take it: `git merge orch/weekday`.
- **Mode:** Lite. Planning on Opus; one Haiku worker, one Opus verifier, one Sonnet fix worker and one Sonnet re-check. The total came to about $4.5, above the $2–3 I estimated, because of the fix round.

As you asked, I kept the plan, notes, worker reports and diffs in `.orchestrator/`, which git ignores. The plan with its full log is `.orchestrator/plan.md`.