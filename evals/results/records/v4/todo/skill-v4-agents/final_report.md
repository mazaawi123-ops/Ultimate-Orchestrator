## Result: done

- **Built:**
  - `todo add "title" --due 2026-10-01` saves the date on the item. The date must be written exactly as `YYYY-MM-DD`; anything else is rejected with an error before anything is saved.
  - `todo list` (and `list --all`) adds ` (due 2026-10-01)` after items that have a date.
  - The new `todo overdue` lists open items whose due date is before today, in the same format as `list` and in id order.
  - Items added without `--due` get no `due` field at all, so existing files are read and written in the same format as before. README usage is updated.
- **Acceptance criteria:** 7/7 verified. The first verification failed one criterion: the CLI `overdue` test used the real clock, so it could fail if run across midnight. That was my brief's fault, and fix round 1 pinned "today" to a fixed date in that test.
- **Tests:** `python -m pytest -q` → 20 passed (the 3 original tests are unchanged apart from their import line). Lint: no linter is installed; `py_compile` is OK. Clean-room: n/a, since nothing calls an external service.
- **Iterations:**
  - Build: a Haiku worker built it; tests were green on the first try.
  - Verify: the Opus verifier failed it only on the clock-dependent test. Five deliberately broken versions of the code were each caught by the tests.
  - Fix round 1: a Sonnet worker pinned the date, restricted the date check to ASCII digits (`[0-9]`, because `\d` also matches fullwidth digits), and cleaned up the smaller issues the verifier flagged. A Sonnet re-check passed with nothing new broken.
- **Rulings I made:**
  - The `due` field is left out when no date is given, rather than stored as `null`, so files stay backwards compatible.
  - Dates must be exactly `YYYY-MM-DD`. Python 3.11 would otherwise accept forms like `20261001`.
  - "Before today" is strict: an item due today is not overdue. "Today" is the local date.
  - `overdue` skips stored dates that are missing, `null` or malformed instead of crashing. `list` shows a stored date only if it's non-empty.
  - The display format is ` (due YYYY-MM-DD)`. `overdue` uses the `list` line format and prints nothing when no items match.
  - Not built, since you didn't ask for them: changing the due date on an existing item, or sorting by due date.
- **Open items:** one leftover unused variable (`id_23`) in `tests/test_store.py::test_overdue`, which I left as is.
- **Not verified:** none.
- **Branch:** `orch/todo-due-dates` from `main` at `fd2956b`, with commits `d184b0c` and `0125e8b`. Not pushed. To take it: `git merge orch/todo-due-dates`.
- **Mode:** Lite. Planner Opus; worker Haiku; fix worker Sonnet; verifier Opus; re-checker Sonnet. My estimate was about $2–2.5.

As you asked, I kept the plan, notes, report and diff files in `.orchestrator/` (git ignores that folder). The main ones are `.orchestrator/plan.md` (plan, rulings and log), `.orchestrator/notes.md` and `.orchestrator/report.md`.