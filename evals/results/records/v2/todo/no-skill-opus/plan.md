# Plan: due dates for todo-cli

## Goal
- `todo add "title" --due 2026-10-01` stores an optional ISO date on the item.
- `todo list` shows the due date next to items that have one.
- New `todo overdue` lists open (not done) items whose due date is before today.
- JSON file stays backwards compatible: files with no `due` field load and work unchanged.
- Tests for all of the above.

## Decisions (made without the user available; revisit if wrong)
1. **Storage shape**: `due` is stored as a `"YYYY-MM-DD"` string and the key is only
   written when a due date is set. Items without a due date are byte-for-byte the
   same shape as before (`{"id", "title", "done"}`), so old files and old readers
   are unaffected. Code always reads it with `item.get("due")`.
2. **Validation**: CLI parses `--due` with `datetime.date.fromisoformat`; invalid
   input is an argparse error (exit code 2, message on stderr). The stored value is
   the normalized `date.isoformat()` form. Only calendar dates, no times.
3. **Store API** (contract shared by both workers):
   - `Store.add(title, due=None)` — `due` is `None`, a `datetime.date`, or an ISO
     date string; stored as `date.isoformat()`; key omitted when `None`.
     Invalid strings raise `ValueError`.
   - `Store.overdue(today=None)` — returns open items with a due date strictly
     before `today` (defaults to `date.today()`), sorted by due date then id.
     `today` is injectable for deterministic tests.
   - `Store.list()` / `Store.complete()` unchanged in behaviour.
4. **Output format**:
   - list/overdue line: `[ ] #3 pay rent (due 2026-10-01)`; items without due print
     exactly as before: `[ ] #3 pay rent`.
   - `overdue` with no matches prints nothing (consistent with `list`).
5. **"Before today"** is strict: an item due today is *not* overdue.
6. **Done items** never appear in `overdue`.

## Work split
- **Worker A (store)**: `todo/store.py`, `tests/test_store.py`.
- **Worker B (cli)**: `todo/cli.py`, new `tests/test_cli.py`, `README.md`.
  Codes against the Store contract above; files are disjoint so both run in parallel.

## Verification (orchestrator, independent of worker reports)
- Read the full diff myself.
- Run the full test suite.
- Manual CLI run against a hand-written legacy JSON file (no `due` keys), then add
  items with/without due dates, list, overdue, done; confirm legacy items are
  untouched in the saved file.
- Edge cases: invalid date, due today, done+overdue, `--all` listing.
- Independent verifier agent (fresh context, no worker reports) tries to break it.
