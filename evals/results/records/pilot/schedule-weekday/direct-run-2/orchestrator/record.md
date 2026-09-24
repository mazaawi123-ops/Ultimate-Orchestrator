# Run record: weekday

Route: Direct (user-specified; no delegation, no independent review).

## Acceptance criteria
1. `every().weekday.at("09:00").do(job)` runs at 09:00 Monday–Friday.
2. Never runs Saturday/Sunday; scheduled after Fri 09:00 or at the weekend, next run is Mon 09:00.
3. `every(2).weekday` raises IntervalError (same as `every(2).day`).
4. Combining with a named day (`.weekday.monday` / `.monday.weekday`) raises ScheduleValueError.
5. With `at(..., tz)`, the weekend is judged in that timezone.
6. Existing suite stays green (`python3 -m pytest -q`).

## Decisions
- Decision: `weekday` is a property setting unit="days" plus a `weekdays_only` flag; weekend days are skipped after the normal next-run computation — reuses all existing `at()`/timezone/DST logic — if wrong, only weekday jobs affected.
- Decision: only interval 1 allowed (`every(2).weekday` → IntervalError) — "every 2nd weekday" is ambiguous; mirrors `every(2).day` — cost if wrong: a later relaxation, no break.
- Decision: `every().weekday.do(job)` without `.at()` is allowed: runs once per weekday at the scheduling time-of-day, like `every().day` — cost if wrong: small.
- Decision: repr shows "Every 1 weekday ..."; `__str__` still shows unit=days (unchanged contract).
- Decision: weekend check uses the `at()` timezone when given (the user's "Monday" is in the zone they named).
- Decision: pytz (declared in requirements-dev.txt but not installed) installed to the scratchpad via `pip --target`, not globally, so tz tests run; without it they skip as before.
- Docs: one example line added to README.rst, docs/index.rst, docs/examples.rst. HISTORY.rst not touched (release notes are maintainers' call).

## Evidence
- Mutation check: disabling the weekend skip makes 4 new tests fail.
- Candidate ba8232a: `python3 -m pytest -q` → 47 passed, 42 skipped (002-check.log). The helper flagged skipped 41→42: the extra skip is the new pytz-dependent tz test. That flag has no approval path in orch.sh, so the candidate was re-checked with pytz on PYTHONPATH (scratchpad) → 89 passed, 0 skipped (004-check.log). Gate PASS.
