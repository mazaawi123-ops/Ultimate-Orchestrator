# Goal
Add optional due dates to todo-cli. `todo add "title" --due 2026-10-01` stores an ISO date
(YYYY-MM-DD) on the item; `todo list` shows the due date next to items that have one; a new
`todo overdue` command lists open (not done) items whose due date is strictly before today.
Existing JSON files with no `due` field must keep loading and working, and items added without
`--due` must be stored exactly as before. Done = features work, tests cover them, full suite green.

# Baseline
- branch: orch/due-dates, from main (uncommitted work: none)
- BASE: fd2956b1d39e4637bec35b073fbaea606142f572
- tests at BASE: `python -m pytest -q` → 3 passed; pre-existing failures: none
- lint at BASE: no linter installed; `python -m compileall -q todo tests` → exit 0 (covers both packages)
- clean-room test command: n/a: no external services
- repo notes: .orchestrator/notes.md (pasted into every brief)
- estimate given to the user: 2 Haiku workers, 1 Opus verifier, likely 1 Sonnet fix + 1 Sonnet
  re-check: ~400k tokens, ~90k on Opus (plus planner)

# Acceptance criteria
- AC1: `python -m todo.cli --db X add "pay rent" --due 2026-10-01` exits 0 and the item in X has
  `"due": "2026-10-01"`.
- AC2: `add` without `--due` writes an item with exactly the keys id, title, done (no `due` key).
- AC3: `--due` values that are not a real calendar date in exact YYYY-MM-DD form (e.g. `2026-13-01`,
  `2026-02-30`, `20261001`, `2026-1-01`, `2026-10-01T00:00`, empty string) exit with code 2, print
  `invalid due date '<value>': expected YYYY-MM-DD` on stderr, and do not create/modify the db file.
- AC4: `list` (and `list --all`) prints `[ ] #1 pay rent (due 2026-10-01)` for items with a due date
  and the unchanged `[ ] #2 milk` for items without.
- AC5: `overdue` prints, in the same line format as `list`, exactly the items that are not done and
  whose due date < today (local date). Due today is not overdue. Done items, items without a due date,
  and items whose `due` is null/non-string/malformed are excluded, without crashing.
- AC6: A JSON file in the old format (`[{"id": 1, "title": "old", "done": false}]`) loads; `list`,
  `overdue`, `done`, and `add` (with and without `--due`) work on it; after saving, the old item
  still has no `due` key.
- AC7: `python -m pytest -q` passes with new tests for AC1–AC6; the 3 tests in tests/test_store.py
  are unchanged; `python -m compileall -q todo tests` exits 0; README usage mentions `--due` and `overdue`.

# Stop-and-ask items
- none (no deps, no external services, no data outside tmp dirs)

# Review focus
- Date parsing leniency: Python 3.11 `date.fromisoformat` accepts `20261001` / `2026-W40-4`;
  `strptime` accepts `2026-1-1`; `$` in regex matches before a trailing newline; `\d` matches
  non-ASCII digits (e.g. fullwidth ２０２６).
- Boundary: due == today (not overdue), due == yesterday (overdue), leap day 2024-02-29 / 2026-02-29.
- Hand-edited files: `"due": null`, `"due": 5`, `"due": "tomorrow"`, missing key.
- Invalid --due must not leave a created/modified db file behind.
- `list --all` on done items with due dates; `overdue` on an empty or nonexistent db.
- Output format drift: existing `list`/`add`/`done` output for items without due must be byte-identical.

# Constraints
- stdlib only (README promises it) — no new deps.
- Existing tests in tests/test_store.py are fixed points.
- JSON format: additive only; no migration/rewrite of existing items.

# Rulings
- Ruling: `due` key is omitted (not `null`) on items without a due date — keeps files byte-compatible
  with the old format and old readers — cost if wrong: trivial; readers use `.get("due")` either way.
- Ruling: only exact `YYYY-MM-DD` (ASCII digits, real calendar date) is accepted; compact/week/datetime
  forms are rejected, not normalised — "store an ISO date" means one canonical form in the file —
  cost if wrong: users typing `20261001` get an error and retype.
- Ruling: invalid `--due` is an argparse usage error (exit 2, message on stderr) — matches how argparse
  already reports bad `done <id>` — cost if wrong: exit code differs from what a script expects.
- Ruling: "before today" uses the local date (`date.today()`); due today is NOT overdue — literal
  reading of "before today" — cost if wrong: off-by-one-day for users expecting due-today inclusion.
- Ruling: items whose stored `due` is null / non-string / malformed are skipped by `overdue` and shown
  without a due suffix by `list` only when falsy; a malformed non-empty string is printed as-is by
  `list` — never crash on hand-edited files — cost if wrong: a typo'd date silently never shows as overdue.
- Ruling: `add` output stays `added #N: title` (no due suffix) — not requested, keeps output stable —
  cost if wrong: trivial cosmetic change later.
- Ruling: `overdue` prints nothing when there are no overdue items (same as `list` on an empty store),
  in file order — consistency with `list` — cost if wrong: cosmetic.
- Ruling: `Store.add` also validates `due` via `parse_due` (ValueError) so the library can't write a
  bad date either — cost if wrong: none.

# Tasks
## T1 Store: due field, parse_due, overdue — tier: haiku — mode: sequential — AC: AC2, AC5, AC6 (store side), AC7
- Worktree: main tree
- Files: todo/store.py, tests/test_due.py (new)
- Depends on: none
- Interfaces:
  - Produces: `todo.store.parse_due(value: str) -> str` (returns value unchanged if valid, else
    `ValueError(f"invalid due date {value!r}: expected YYYY-MM-DD")`);
    `Store.add(self, title, due=None) -> dict`;
    `Store.overdue(self, today=None) -> list[dict]` (today: datetime.date, default date.today())
- Tests allowed to change: none
- Status: pending

## T2 CLI: --due, list suffix, overdue command, README — tier: haiku — mode: sequential after T1 — AC: AC1, AC3, AC4, AC5, AC6 (CLI side), AC7
- Worktree: main tree
- Files: todo/cli.py, tests/test_cli.py (new), README.md
- Depends on: T1
- Interfaces:
  - Consumes: `parse_due`, `Store.add(title, due=None)`, `Store.overdue()` from T1
  - Produces: `todo overdue` subcommand; `add --due`
- Tests allowed to change: none
- Status: pending

# Shared-surface check
| Tasks | Shared file / interface | Resolution |
|---|---|---|
| T1, T2 | parse_due / Store.add / Store.overdue | sequential; T2 consumes T1's real code |

# Log
- T1 (haiku) → reported DONE, commit 0a67aeb, 25 passed. Planner check found 2 unreported
  deviations: overdue() used date.fromisoformat directly instead of parse_due (root cause: worker
  "simplified" the specified try/parse_due step; brief's junk test used "2026-02-30", which
  fromisoformat also rejects, so no test pinned the compact-form case), and tests written as classes.
  Sent back to the same worker with a failing-first test ("20000101", "2000-W01-1" skipped).
- T1 fix (same haiku worker): overdue now calls parse_due; tests flattened; commit 5012b75, 26 passed. Accepted.
  Note: T1's first RED section is described ("would fail") rather than pasted output.
- T2 (haiku) → DONE, commit 0a19027, 42 passed. Planner check: full suite 42 passed, compileall ok,
  old-tests OK, no stray files, diff matches brief. Accepted.
- iter 1 verify: diff-1.patch (BASE fd2956b..0a19027) → Opus full verifier dispatched.
- iter 1 verify (opus): PASS on AC1–AC7; 0 blockers, 0 should-fix, 4 nits; 11/13 mutations caught
  (the 2 survivors are equivalent on py3.11). Report: .orchestrator/verify-1-report.md
- Ruling: park all 4 nits (non-str `due` to Store.add raises TypeError not ValueError; list prints
  truthy non-string due like "(due 5)"; overdue parses twice; one test uses `in` not `==`) — none
  writes bad data or affects the CLI's criteria, and a fix round costs ~180k tokens — cost if wrong:
  a library caller passing a datetime.date gets a TypeError message.
- Done. No fix rounds. Agents: 2 haiku workers (+1 send-back to the T1 worker), 1 opus verifier.
