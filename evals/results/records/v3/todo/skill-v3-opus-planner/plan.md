# Goal
Add optional due dates to todo-cli: `todo add "t" --due 2026-10-01` stores an ISO date on the item; `todo list` shows it next to items that have one; new `todo overdue` lists open items whose due date is before today. Existing JSON files without a `due` key must keep loading and working unchanged. Tests for all of it.

# Baseline
- branch: orch/due-dates, from main (uncommitted work: none)
- BASE: fd2956b1d39e4637bec35b073fbaea606142f572
- tests at BASE: `python3 -m pytest -q` → 3 passed; pre-existing failures: none
- lint at BASE: `ruff check .` → 4 errors, all pre-existing in todo/cli.py:10-12 (E702 x3, E741)
- clean-room: n/a, no external services
- repo notes: .orchestrator/notes.md
- estimate given to the user: Lite, 1 Haiku worker + 1 Opus verifier, ~$1.5–2.5 total mostly planner

# Acceptance criteria
- AC1: `python -m todo.cli --db X add "pay rent" --due 2026-10-01` prints `added #1: pay rent (due 2026-10-01)` and the stored item has `"due": "2026-10-01"`.
- AC2: `add` without `--due` stores an item with NO `due` key (file byte-shape identical to before: `{"id","title","done"}`).
- AC3: invalid `--due` (`2026-13-01`, `tomorrow`, `2026-1-5`, `20261001`, `""`) → argparse error, exit code 2, nothing written.
- AC4: `list` shows `[ ] #1 pay rent (due 2026-10-01)` for items with due; items without due print exactly as before (`[ ] #2 buy milk`). `list --all` shows due on done items too.
- AC5: `overdue` prints, in the same line format as list, open items with due < today (local `date.today()`); excludes done items, items due today, future items, and items without due. Prints nothing when none.
- AC6: a pre-existing JSON file with items lacking `due` (hand-written fixture) loads; list/done/overdue work on it; saving after `add --due` leaves the old items without a `due` key.
- AC7: `python3 -m pytest -q` passes, with new tests covering AC1–AC6 (Store-level and CLI-level); `ruff check .` has no errors beyond the 4 pre-existing ones.

# Stop-and-ask items
- none

# Review focus
- due == today (not overdue); due yesterday (overdue); done + past due (not listed)
- stored `due` value that is null or malformed in a hand-edited file: overdue must not crash (skip it); list prints it only if truthy
- `due: null` in file treated same as missing
- invalid dates incl. Feb 30, non-padded, compact ISO, week dates
- old files: no key added to items that were never given a due date on re-save
- `done` on an item keeps its due

# Constraints
- stdlib only, no new deps. JSON format: only additive optional `due` key (string "YYYY-MM-DD").
- Existing tests unchanged.

# Rulings
- Ruling: `--due` accepts only strict `YYYY-MM-DD` (regex `^\d{4}-\d{2}-\d{2}$` then `date.fromisoformat`); 3.11's lenient forms like `20261001` are rejected — the request says ISO date and predictable storage matters — cost if wrong: users typing compact dates get a clear error.
- Ruling: omit `due` key when not given (not `"due": null`) — keeps files for non-due users identical to today — cost if wrong: none, readers use `.get("due")`.
- Ruling: overdue is strictly `due < today`, today = `date.today()` (local time); Store.overdue takes `today` param for testability — "before today" in request — cost if wrong: one-day boundary shift.
- Ruling: overdue output reuses list's line format and file order; prints nothing if empty (like list) — consistency — cost if wrong: cosmetic.
- Ruling: Store.overdue skips items whose stored `due` is missing, null, or unparseable — hand-edited files must not crash the CLI — cost if wrong: a garbage date silently isn't reported overdue.
- Ruling: `add` echo gains ` (due YYYY-MM-DD)` suffix only when due given — cost if wrong: cosmetic.
- Ruling: CLI tests call `main([...])` with `capsys`; overdue CLI tests use far past/future dates (2000-01-01 / 2999-12-31) so they don't depend on the real date; boundary tests go through `Store.overdue(today=...)`.
- Ruling: README usage line updated to mention `--due` and `overdue`.

# Tasks
## T1 due dates end-to-end — tier: haiku — sequential — AC: AC1–AC7
- Worktree: main tree
- Files: todo/store.py, todo/cli.py, README.md, tests/test_store.py (append only), tests/test_cli.py (new)
- Depends on: none
- Interfaces:
  - Produces: `Store.add(self, title, due=None)` — `due` is a "YYYY-MM-DD" str or None; key set only when not None.
  - Produces: `Store.overdue(self, today)` — `today` is a `datetime.date`; returns open items with parseable due < today, file order.
  - Produces: in cli.py `parse_due(s) -> str` (argparse `type=`; raises `argparse.ArgumentTypeError`), and `format_item(item) -> str` used by list and overdue.
- Tests allowed to change: none (append new tests only)
- Status: pending

# Shared-surface check
| Tasks | Shared file / interface | Resolution |
|---|---|---|
| (single task) | — | — |

# Log
- T1 dispatched (haiku), 22:28
- T1 DONE (f5d9cfd), 21 passed per worker
- verify 1 (opus): PASS; should-fix: old-file done/overdue not tested at CLI level, Store old-file test passes against `return []` mutant; nits: \d matches non-ASCII digits, invalid-due test didn't assert no write, docstring
- fix 1 (round 1, sonnet, 0e04ff5): added old-file CLI + Store tests (mutant-proven), ASCII [0-9] regex, no-write asserts + non-ASCII cases, docstring. 23 passed
- Ruling: fix 1 renamed per-case db file to loop index in test_add_invalid_due_formats_various — raw invalid strings as filenames break for "" — cost if wrong: none
- Ruling: not fixing nit "overdue parses lenient fromisoformat for hand-edited 20000101" — the CLI never writes that form and flagging it as overdue is reasonable — cost if wrong: a hand-edited compact date is treated as valid
- Ruling: not fixing nit "add echo duplicates suffix logic of format_item" — cosmetic, 1 line
- verify 2 (scoped, sonnet): PASS, all 4 findings ADDRESSED, mutant kills 4 tests, no new breakage. DONE.
