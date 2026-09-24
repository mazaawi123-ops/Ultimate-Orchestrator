# Goal
Add optional due dates to todo-cli: `todo add "title" --due 2026-10-01` stores an ISO date
on the item; `todo list` shows the due date next to items that have one; a new `todo overdue`
command lists open (not done) items whose due date is before today. Existing JSON files with
no "due" field must keep loading without error.

# Baseline
- branch: orch/todo-due-dates, from main (no uncommitted work)
- BASE: fd2956b1d39e4637bec35b073fbaea606142f572
- tests at BASE: `python -m pytest -q` → 3 passed; pre-existing failures: none
- lint at BASE: none configured
- clean-room test command: n/a: no external services
- repo notes: .orchestrator/notes.md (pasted into every brief)
- estimate given to the user: 1 sonnet worker + 1 opus verifier, ~$0.6-1.0 total, small share on opus

# Acceptance criteria
- AC1: `todo add "title" --due 2026-10-01` stores `"due": "2026-10-01"` on the item; `todo add "title"` (no --due) stores no due date (field absent or null) and doesn't break anything
- AC2: `todo add "title" --due not-a-date` fails with a clear error, not a traceback (argparse error or caught ValueError with a message), and does not write a corrupt item
- AC3: `todo list` prints the due date next to items that have one (e.g. `[ ] #1 title (due 2026-10-01)`), and items without a due date print exactly as before (no regression to existing format)
- AC4: `todo overdue` lists only open (not done) items whose due date is strictly before today's date; an item due exactly today is NOT listed; an item due in the future is NOT listed; a done item past its due date is NOT listed; an item with no due date is NOT listed
- AC5: loading a pre-existing JSON file whose items have no "due" key works without error for `list`, `add`, `done`, and `overdue`
- AC6: `python -m pytest -q` passes, including new tests for AC1-AC5

# Stop-and-ask items
none

# Review focus
- item with due date exactly equal to today (must not be overdue)
- item with due date one day before today (must be overdue)
- item with no "due" key at all in the loaded JSON (legacy file) vs. item with `"due": null`
- done item whose due date is in the past (must not appear in overdue)
- invalid --due value (garbage string, wrong format like "10/01/2026") on add
- list output format for mixed items (some with due, some without) in one call
- overdue command respects --db like other commands

# Constraints
- No new dependencies: use stdlib `datetime.date` only.
- Keep JSON backwards compatible: reading an old item dict without "due" must not KeyError;
  writing can include "due": null for items without one (that's still valid JSON and old
  code that ignores unknown keys is unaffected — this repo has no external readers to worry
  about).
- Don't change existing item ordering or the id-assignment scheme.

# Rulings
- Ruling: `Store.overdue(today=None)` takes an optional `today: date` parameter defaulting to
  `date.today()` — this makes the "before today" comparison testable without monkeypatching
  the stdlib `date` type — cost if wrong: tests would need to fake the system clock instead,
  more fragile
- Ruling: invalid --due strings are rejected via `date.fromisoformat` inside the CLI add
  handler, caught and turned into a `SystemExit`/clear printed error (not a raw traceback) —
  matches the CLI's existing plain, minimal style — cost if wrong: users get a Python
  traceback for a typo, which is unfriendly but not a correctness bug
- Ruling: display format on `list` is `[<mark>] #<id> <title> (due <date>)` — appended only
  when a due date is present — cost if wrong: cosmetic only, easy to adjust later

# Tasks
## T1 add due dates (store + cli + tests) — tier: sonnet — mode: sequential — AC: AC1, AC2, AC3, AC4, AC5, AC6
- Worktree: main tree
- Files: todo/store.py, todo/cli.py, tests/test_store.py, README.md
- Depends on: none
- Interfaces:
  - Produces: `Store.add(title, due=None)` — `due` is `str` (ISO `YYYY-MM-DD`) or `None`;
    stores it on the item as `item["due"]`
  - Produces: `Store.overdue(today=None)` — `today: date | None`, defaults to `date.today()`;
    returns open (not done) items whose `due` is a non-null ISO date strictly before `today`
  - Produces: `Store.list(include_done=False)` unchanged signature; items may or may not have
    a `"due"` key/value, callers must use `.get("due")`
  - Produces: CLI `add` subcommand gains `--due DATE` optional arg (ISO format)
  - Produces: new CLI `overdue` subcommand (no extra args beyond global `--db`), prints one
    line per overdue item in the same `[<mark>] #<id> <title> (due <date>)` style as `list`
    (mark is always " " since overdue items are open by default, but reuse the same
    formatting code as `list` to avoid duplicating it)
- Tests allowed to change: none (test_store.py existing tests must keep passing unmodified;
  add new test functions to it)

# Shared-surface check
n/a: single task

# Log
- (filled as the run proceeds)
- iter 1: T1 dispatched to sonnet worker (agent ad074b8186348a8ef)
- iter 1: T1 DONE (f6e6ffa), 15 passed. orch.sh check clean, no old-test deletions. Verifier dispatched (opus, agent aec1808cb41967e52).
- iter 1: verifier PASS. AC1-AC6 all PASS. should-fix: cli.py add handler uses bare date.fromisoformat(due) which accepts non-YYYY-MM-DD ISO variants (e.g. "20261001", "2026-W40-4") and stores them verbatim, inconsistent with the "expected YYYY-MM-DD" error and the plan's storage format. nits: error printed to stdout not stderr; Store.overdue()/add() don't guard against malformed due strings from non-CLI callers; test_add_with_invalid_due_fails_cleanly's `err` capture unused. Decision: fix the should-fix (round 1, sonnet); log nits as open items, not worth a fix round.
- fix 1 (finding: due normalization, round 1, sonnet): commit 88161de, normalizes parsed --due to .isoformat() before storing; 16 passed, no old-test deletions. Scoped re-verify dispatched (sonnet, agent a313e81ef4b6f00e5).
- iter 2 (scoped re-verify, sonnet): PASS. Finding 1 ADDRESSED. No new breakage. 16 passed.

# Final result
Done. Branch orch/todo-due-dates ready to merge into main. Not pushed. Report files kept per user instruction (not cleaning up .orchestrator/).
