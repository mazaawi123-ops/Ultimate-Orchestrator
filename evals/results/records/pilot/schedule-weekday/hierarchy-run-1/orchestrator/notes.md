# Repo notes (schedule)
- Library is one module: schedule/__init__.py (Scheduler, Job). Tests: test_schedule.py (unittest TestCase, run by pytest).
- Tests: `python3 -m pytest -q` → baseline 40 passed, 41 skipped (skips = "pytz unavailable"; pytz NOT installed, don't install it).
- Lint: `black --check schedule` passes at BASE. test_schedule.py already has 6 black-diff lines at BASE (tuple-unpacking `(job, tz) = ...`); check yours with `black --diff -q test_schedule.py | grep -c '^+[^+]'` → must stay 6. mypy is not installed.
- Time is faked with the `mock_datetime(y, m, d, h, min)` context manager in test_schedule.py; local TZ is forced to Europe/Berlin at import. Imitate `test_run_every_weekday_at_specific_time_today` (~line 1427) for run_pending tests, `test_to_repr` (~line 1338) for repr.
- Fluent API: unit set by properties (`days`, `weeks`...); `monday`..`sunday` properties set `self.start_day` and return `self.weeks`, raising IntervalError if interval != 1.
- `Job.at()` accepts HH:MM(:SS) when `self.unit == "days"`. `_schedule_next_run()` computes next_run: now → move to at_time → `while next_run <= now: next_run += period` → `_correct_utc_offset(...)` → tz conversion.
- `Job.__repr__` prints "Every 1 day at 09:00:00 do job() (last run: ..., next run: ...)".
- Dates: 2010-01-06 Wed, 07 Thu, 08 Fri, 09 Sat, 10 Sun, 11 Mon.
- black at <root>/.local/bin/black (v26, py3.11).
