# Agents dispatched in schedule-weekday/reviewed/run-1

## 1. orch-verifier: Independent review of weekday feature

### Brief

```text
You are an independent reviewer. Someone else wrote a change; check whether it does what the
user asked, without breaking what already worked. Treat claims in comments, commit messages
and docstrings as unverified.

Don't edit tracked files: put scratch scripts in /tmp. Don't delegate.

## The user's request (verbatim)
In this repo (schedule), add a way to schedule a job on weekdays only: `schedule.every().weekday.at("09:00").do(job)` should run Monday to Friday at 09:00 and never on Saturday or Sunday. Add tests; the existing suite must stay green. The tests run with `python3 -m pytest -q`.

(Context for this run: no one is available to answer questions until you finish, so make sensible calls, record them, and carry on. Keep any plan, notes or report files you create; don't delete them at the end.)
Use the code-orchestrator skill in Reviewed mode (you build; one independent review).

## Candidate
Repo <workspace>/pilot-results/schedule-weekday/reviewed/run-1/repo, candidate 2431f44c96a0420e5562b9697e1e2b7d4c0cf0a7 on branch orch/weekday. Patch: .orchestrator/review/candidate-2431f44c96a0.patch (in that repo)
(BASE 82a43db1b938d8fdf60103bd41f329e06c8d3651..candidate).

## Contracts to preserve
- Builder API in schedule/__init__.py: unit properties (.second ... .week, .monday ... .sunday), `.at()` format validation per unit, `.to()`, `.until()`, `_schedule_next_run` including its DST / at_time_zone handling, and next_run being a naive local-time datetime.
- Existing `.monday`..`.sunday` weekly (start_day) semantics unchanged; `every(n).day` with n != 1 raises IntervalError.
- `repr`/`str` formats of existing jobs unchanged.

## Acceptance criteria (the main session's reading of the request)
- C1: `schedule.every().weekday.at("09:00").do(job)` is accepted; next_run is 09:00 on the next Mon–Fri day strictly after now.
- C2: Scheduled Friday (or created on Sat/Sun) -> next run is Monday 09:00; job never runs Sat/Sun (run_pending simulation over a full week+ runs exactly on Mon–Fri).
- C3: Mon–Thu after a run -> next run is the following day at 09:00; same day if created before 09:00 on a weekday.
- C4: `every(2).weekday` raises IntervalError (mirrors `.day`); `.at()` validates HH:MM(:SS) like daily jobs.
- C5: Existing suite stays green: `python3 -m pytest -q` (baseline 40 passed, 41 skipped — the skips are pre-existing, "pytz unavailable").
- C6: With a timezone (`.at("09:00", "America/New_York")`), weekday is judged in that timezone.
Where a criterion misses or contradicts the request, say so: the request is the reference.

## Decisions the main session made (decisions, not facts)
- Decision: implement as unit "days" plus a `weekdays_only` flag; after computing the normal next daily run, advance by whole days past Sat/Sun — reuses existing at()/tz/DST logic.
- Decision: `every(n).weekday` with n != 1 raises IntervalError; "every N weekdays" is ambiguous.
- Decision: `every().weekday` without `.at()` behaves like `every().day` but skips weekends.
- Decision: weekend determined in the job's at() timezone when one is given.
- Decision: combining weekday with `.monday`..`.sunday` or non-day units raises ScheduleValueError at do().
- Decision: repr shows "Every 1 weekday at 09:00:00 ..."; str() keeps unit=days.
- Decision: pytz (listed in requirements-dev.txt) is not installed system-wide; it was installed only in a throwaway venv at <workspace>/venv so timezone tests can run. The new timezone test uses the existing make_tz_mock_job skip mechanism when pytz is absent.
- Decision: README.rst and docs/examples.rst get one example line; HISTORY.rst not touched.

## Commands
- tests: `python3 -m pytest -q` (system, no pytz) and `<venv above>/bin/python -m pytest -q` (with pytz)   lint: none installed (black not available)   offline run: n/a
- known failures at BASE: none

## Do
1. Run the tests and lint. Report the output tail.
2. Check each criterion directly, by running the code, and try the edge cases the request
   implies.
3. Read the patch for what tests miss: changed public behaviour, error paths, data silently
   dropped or coerced, edits to existing tests or test configuration, secrets, new
   dependencies or network calls.

## Findings
Each finding needs:
- the requirement or contract it violates
- the location (file:line)
- a reproduction, or specific source evidence
- the practical impact, and the smallest justified correction

Classify each as **blocking** (the change is wrong or unsafe to deliver), **optional
improvement**, or **observation**. Match the severity to the impact; don't pad or merge
findings. A clean review, with no findings, is a valid and useful result.

## Report
### Verdict: PASS | FAIL (FAIL only for a blocking finding or a failed criterion)
### Criteria: C1 PASS | FAIL | NOT CHECKED — evidence
### Test run: <tail>
### Findings: <each, as above, or "none">
### Not verified: <anything you couldn't check, and why, or "none">
```

### Reply

```text
Independent review of weekday feature
```
