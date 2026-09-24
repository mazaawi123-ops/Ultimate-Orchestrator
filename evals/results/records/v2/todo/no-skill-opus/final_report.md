Due dates are in and all 15 tests pass. I checked the CLI by hand against a file in the old format, and a separate reviewer that never saw the workers' reports tried to break it and found no bugs. Nothing is committed, so you can review the changes first.

**How it works**
- **`todo add "title" --due 2026-10-01`** saves the date on the item. An impossible date like `2026-02-30` is rejected with exit code 2 and a clear message.
- **`todo list`** shows the date after items that have one: `[ ] #3 pay rent (due 2026-10-01)`. Items without a date look exactly as before.
- **`todo overdue`** lists open items due before today, oldest first. An item due today doesn't count, and neither do done items.
- **Old files still work:** items without a due date are saved with no `due` field, so old items come out of a save unchanged.

**How the work was split**
- One worker did the storage layer (`todo/store.py`), including a new `Store.overdue()`, plus 6 new tests in `tests/test_store.py`.
- A second worker did the CLI (`todo/cli.py`), 6 tests in a new `tests/test_cli.py`, and the README.
- I fixed the storage interface in the plan first, so the two could work at the same time on separate files.
- Then I read the whole diff and ran the CLI by hand with today's date (2026-09-23): an item due yesterday showed as overdue and one due today did not.

**Decisions I made on my own**
- **What "overdue" means:** it is strictly before today; done items are left out.
- **Output:** `overdue` prints nothing when nothing is overdue, the same as `list`.
- **Invalid dates:** `--due` values are checked when you run `add` and always saved as `YYYY-MM-DD`.

**Minor risks I left as they are**
- **Other date formats:** Python 3.11 also accepts `20261001` and `2026-W40-1` and saves them as normal `YYYY-MM-DD` dates. If you want only `YYYY-MM-DD` accepted, it's a one-line check.
- **Hand-edited files:** if someone types a bad `"due"` value into the JSON by hand, `todo overdue` crashes; `list` still works. I preferred that to quietly skipping the item.
- **Already there before this change:** `todo done 99` shows a raw error traceback.

The plan and the verification report are in `.orchestrator/plan.md` and `.orchestrator/report.md`. That folder is excluded by `.gitignore`, so neither file will be committed.