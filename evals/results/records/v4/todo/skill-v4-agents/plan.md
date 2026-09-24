# Goal
Add optional due dates to todo-cli: `todo add "title" --due 2026-10-01` stores an ISO date on
the item; `todo list` shows the due date next to items that have one; new `todo overdue` lists
open items whose due date is before today. Existing JSON files with no `due` field keep
working unchanged. Tests cover all of it.

# Baseline
- branch: orch/todo-due-dates, from main (uncommitted work: none)
- BASE: fd2956b1d39e4637bec35b073fbaea606142f572
- tests at BASE: `python -m pytest -q` → 3 passed; pre-existing failures: none
- lint at BASE: none installed; `python -m py_compile todo/*.py tests/*.py` as syntax check
- clean-room test command: n/a: no external services
- repo notes: .orchestrator/notes.md
- estimate given to the user: 1 Haiku worker, Opus verifier, Opus planner ≈ $2–2.5

# Acceptance criteria
- AC1: `Store.add("t", due="2026-10-01")` stores `"due": "2026-10-01"` in the JSON file; `Store.add("t")` stores an item with NO `due` key (file bytes for due-less items identical in shape to BASE).
- AC2: `python -m todo.cli --db X add "t" --due 2026-10-01` → prints `added #1: t (due 2026-10-01)`, persists due. Without `--due` output is unchanged: `added #1: t`.
- AC3: invalid `--due` (`2026-13-01`, `2026-02-30`, `tomorrow`, `20261001`, `2026-1-5`, empty string) → argparse error, exit code 2, stderr contains `invalid due date`, nothing written to the DB.
- AC4: `list` prints `[ ] #1 t (due 2026-10-01)` for items with due, unchanged `[ ] #2 u` for items without; `--all` shows done items with due as `[x] #3 v (due 2026-01-01)`.
- AC5: `overdue` prints open items with due < today, one per line in list format, in store (id) order; excludes done items, items without due, and items due today or later. No matches → prints nothing, exit 0.
- AC6: a DB file written at BASE format (items without `due`) loads, lists, completes and runs `overdue` without error; saving it back adds no `due` keys.
- AC7: `python -m pytest -q` passes; the 3 BASE tests are unchanged; new tests cover AC1–AC6 without depending on the real current date.

# Stop-and-ask items
- none

# Review focus
- boundary: due == today (not overdue), due == today-1 (overdue)
- Python 3.11 `date.fromisoformat` accepts `20261001` and week dates — must be rejected (strict YYYY-MM-DD)
- stored `due` that is malformed / non-string (hand-edited file) — `overdue` and `list` must not crash
- `due: null` in a hand-edited file → treated as no due date
- done item that is overdue → excluded from `overdue`
- `--due` given to other subcommands → argparse rejects (only `add` has it)
- `--db` ordering: `--db` is a top-level option before the subcommand

# Constraints
- stdlib only, no new dependencies — README says stdlib-only
- existing JSON format stays readable and items without due stay without a `due` key
- the 3 existing tests in tests/test_store.py must not change

# Rulings
- Ruling: `due` key is omitted (not `null`) when no due date is given — keeps new files byte-compatible with old readers/format — cost if wrong: a reader expecting the key must use `.get`
- Ruling: strict `YYYY-MM-DD` only (regex `^\d{4}-\d{2}-\d{2}$` + `date.fromisoformat`) — request says "ISO date" and shows that form; 3.11's lenient parser would accept `20261001` — cost if wrong: users typing compact dates get an error
- Ruling: validation lives in `todo/store.py` as `parse_due(s) -> str` (raises ValueError); CLI uses it as argparse `type=` via a wrapper raising `argparse.ArgumentTypeError("invalid due date: <s> (expected YYYY-MM-DD)")`; `Store.add` also validates when due is not None — one source of truth — cost if wrong: minimal
- Ruling: display format ` (due YYYY-MM-DD)` appended after the title, in list, overdue, and add confirmation — cost if wrong: cosmetic
- Ruling: "before today" is strict: due < today; `today` = `datetime.date.today()` (local), injectable via `Store.overdue(today=None)` — cost if wrong: off-by-one-day on the boundary
- Ruling: `overdue` skips items whose stored due is missing, null, or unparseable; `list` prints a non-null stored due as-is — a hand-edited file shouldn't crash the CLI — cost if wrong: a corrupt due silently never shows as overdue
- Ruling: `overdue` output uses the list line format (`[ ] #id title (due X)`), store order, prints nothing when empty — consistent with `list` — cost if wrong: cosmetic
- Ruling: no `--due` editing of existing items, no sorting by due — not requested

# Tasks
## T1 due dates in store + CLI + tests — tier: haiku — sequential — AC: AC1–AC7
- Worktree: main tree
- Files: todo/store.py, todo/cli.py, tests/test_store.py (append only), tests/test_cli.py (new), README.md (usage line)
- Depends on: none
- Interfaces:
  - Produces: `parse_due(s) -> str` in todo/store.py; `Store.add(title, due=None)`; `Store.overdue(today=None) -> list[dict]`; CLI `add --due`, `overdue` subcommand; `format_item(i) -> str` in todo/cli.py
- Tests allowed to change: none (append new tests only)
- Status: pending

# Shared-surface check
| Tasks | Shared file / interface | Resolution |
|---|---|---|
| (single task) | — | — |

# Log
- T1 dispatched to orch-worker-haiku
- T1 DONE (d184b0c), 19 passed; orch check clean (only import line changed in old test file)
- iter 1 verify (orch-verifier): FAIL on AC7 only — tests/test_cli.py test_overdue_command reads date.today() (root cause: my brief told it to; midnight flake). AC1–AC6 PASS, 5 mutants killed.
  - should-fix: pin today in CLI test → fix round 1
  - nit: regex \d matches Unicode digits → fix round 1 (use [0-9]) + test
  - nit: `raise ... from None` in parse_due; unused vars id_24/id_no_due; dup due-suffix in add → fix round 1 (cheap)
  - ruling challenged: list hides falsy non-null due (0, false, "") → re-decided: Ruling: `list` shows a stored due only when truthy; falsy values (null, "", 0, false) are treated as no due date — nothing meaningful to display — cost if wrong: cosmetic. Code already does this.
- fix 1 dispatched (orch-worker-sonnet)
- fix 1 DONE (0125e8b), 20 passed; rechecker dispatched
- fix 1 recheck (orch-rechecker): PASS, all 5 findings ADDRESSED, no new breakage; leftover nit: unused id_23 in test_overdue (left as-is)
