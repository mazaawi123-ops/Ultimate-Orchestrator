# Goal
Stop `Inventory.ship()` driving stock negative when shipping more than is in stock (raise the
existing `InsufficientStock` instead), and add `Inventory.import_csv(path)` for bulk receiving
from a `sku,qty` CSV, skipping blank lines and raising a clear line-numbered error for bad rows.
Tests for both.

# Baseline
- branch: orch/inventory-fix-csv-import, from main (uncommitted work: none)
- BASE: 167b0db3cbb04d0c03e3cdb2101f11b0af732e1b
- tests at BASE: `python -m pytest -q` → 4 passed; pre-existing failures: none
- lint at BASE: n/a — no lint config in repo
- clean-room test command: n/a — no external services, stdlib-only
- repo notes: .orchestrator/notes.md (pasted into every brief)
- estimate given to the user: 1 haiku worker (~$0.10-0.35) + 1 opus verifier (~$0.20-0.40),
  most of the run's tokens on the planner (Sonnet, this session)

# Acceptance criteria
- AC1: `ship(sku, qty)` with `qty > level(sku)` raises `InsufficientStock`, and `level(sku)`
  is unchanged after the raise; `qty == level(sku)` succeeds and leaves level at 0.
- AC2: `import_csv("sku,qty\nA,5\n\nB,2\n")` (blank line skipped) results in `level("A") == 5`
  and `level("B") == 2`.
- AC3: a bad row (non-integer qty, non-positive qty, wrong column count) raises an error whose
  message contains "line N" where N is the 1-based physical line number of that row (header is
  line 1); rows already applied before the bad row are not rolled back (see Ruling below).
- AC4: `python -m pytest -q` passes, including new tests covering AC1-AC3.

# Stop-and-ask items
none

# Review focus
- CRLF line endings in the CSV
- blank lines interspersed between valid rows, and a blank line right before a bad row
- trailing newline vs. no trailing newline at end of file
- header with columns in different order or missing/extra columns
- row with only a comma (empty sku, empty qty)
- ship() qty exactly equal to current level (boundary, should succeed, land at 0)
- ship() on a sku never received (level 0, any positive qty should raise)
- import_csv qty of 0 or negative (receive() already rejects via ValueError — decide whether
  import_csv wraps that into the same "line N" error format)

# Constraints
- stdlib-only: no new dependencies (use the `csv` module, not pandas etc.)
- keep `InsufficientStock` as the exception type for AC1 — it already exists in stock.py
- don't change existing test behavior in tests/test_stock.py; only add new tests

# Rulings
- Ruling: import_csv does NOT roll back rows already received before hitting a bad row (it
  fails fast, partial state stays) — matches receive()'s own fail-fast style and keeps the
  implementation simple — cost if wrong: a caller doing a bulk import must call import_csv
  before making other changes, or check state after a failure; this should be documented in a
  short docstring on import_csv.
- Ruling: header row is required and must be exactly `sku,qty` (case-sensitive, no extra
  columns) — the request specifies "a CSV with columns sku,qty" — cost if wrong: a headerless
  file is rejected with a "line 1" error naming the bad header.
- Ruling: import_csv wraps a receive() qty-validation failure (e.g. qty <= 0) into the same
  line-numbered error format rather than letting a bare ValueError from receive() propagate,
  so every bad-row error consistently names its line — cost if wrong: caller sees an
  inconsistent error message for that one case.

# Tasks
## T1 fix ship overdraw + add import_csv — tier: haiku — mode: sequential — AC: AC1, AC2, AC3, AC4
- Worktree: main tree
- Files: inventory/stock.py, tests/test_stock.py
- Depends on: none
- Interfaces:
  - Produces: `Inventory.import_csv(self, path)` — reads the CSV at `path` (a string or
    Path), first row must be header `sku,qty`; for each subsequent non-blank row, parses
    `sku` (str) and `qty` (int), calls `self.receive(sku, qty)`; raises `ValueError` with a
    message containing "line N" (N = 1-based physical line number, header counted as line 1)
    for: a bad/missing header, a row with wrong column count, a non-integer qty, or a qty
    that fails `receive`'s own validation (qty <= 0). Blank lines (empty after stripping) are
    skipped and don't count as errors. Returns None.
  - Consumes: existing `Inventory.receive(self, sku, qty)`, existing `InsufficientStock`
- Tests allowed to change: none (only additions to tests/test_stock.py)
- Status: pending

# Shared-surface check
(single task, no parallelism)

# Log
- (plan created)
- T1 dispatched to haiku worker (agentId ab3f828d1ec32e4d1)
- T1 DONE (285012b), 22 passed, no deviations
- orch.sh check: clean (only import line changed in test_stock.py)
- verifier dispatched (opus, agentId a9e928517679932d5)
- verifier: FAIL. AC1/AC2/AC4 PASS. AC3 fails on 2 input classes:
  (a) hand-rolled line_num counter breaks on a quoted multi-line field (record spans
      physical lines but counter increments once per record)
  (b) blank-row skip at stock.py:48 uses `all(cell.strip()=='' for cell in row)`, so a row
      like "," (2 empty cells) or ",," (3 empty cells) is silently skipped instead of
      raising a column-count/empty-sku error — this was explicitly named in the plan's
      review focus ("a row with only a comma")
  Also should-fix: file opened without newline='' (csv module requires it for correct
  quoted-newline handling). Nits: header error doesn't show what was found, no BOM
  handling, no `from e` exception chaining, InsufficientStock has no message.
- Ruling: fix (a), (b), and the newline='' should-fix, since they're direct AC3 failures
  in the same few lines — cost of not fixing: import_csv corrupts/misreports line numbers
  and silently drops bad rows instead of raising, which is the exact bug class AC3 exists
  to prevent.
- Ruling: also fix the from-e chaining, header error detail, BOM handling, and
  InsufficientStock message nits in the same round — all are 1-line changes in the same
  method/file already being edited — cost of not fixing: confusing tracebacks and
  unhelpful error text, no functional risk.
- Ruling: int()'s looseness (accepts `1_000`, `+5`, non-ASCII digits) — leave as-is, not
  a spec violation, tightening it adds validation the request didn't ask for — cost if
  wrong: a CSV with an unusual numeral format is silently accepted.
- Ruling: for a bad row inside a multi-line quoted field, "line N" reports the line where
  the CSV record ends (`reader.line_num`), not where it starts — matches the verifier's
  suggested fix, and skus/qty realistically never contain embedded newlines so the
  distinction is academic — cost if wrong: a rare multi-line-field error points a couple
  of lines late.
- fix round 1 dispatched (sonnet)
- fix 1 DONE (f62b414), 26 passed, no deviations
- orch.sh check: clean
- scoped re-verify dispatched (sonnet, agentId a82033c9c97255b5d)
- scoped re-verify: PASS. All 7 findings ADDRESSED, AC1-AC4 all PASS, 26 passed, no new
  breakage, no pre-existing test edited/deleted.
- DONE
