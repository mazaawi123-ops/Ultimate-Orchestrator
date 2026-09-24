# Goal
Stop Inventory.ship() driving stock negative (raise the existing InsufficientStock instead), and add
instance method Inventory.import_csv(path) that bulk-receives from a sku,qty CSV, skipping blank lines
and raising a clear, line-numbered error for bad rows. Tests for both. Done = both behaviours tested, full suite + lint green, independently verified.

# Baseline
- branch: orch/inventory-fix-csv, from main (uncommitted work: none)
- BASE: 167b0db3cbb04d0c03e3cdb2101f11b0af732e1b
- tests at BASE: python -m pytest -q → 4 passed; pre-existing failures: none
- lint at BASE: ruff check . && flake8 inventory tests → clean (ruff covers whole repo)
- clean-room test command: n/a: no external services
- repo notes: .orchestrator/notes.md
- estimate given to the user: ~$2–2.5 (Opus planner, 1 Haiku worker, 1 Opus verifier; +~$0.45 per fix round)

# Acceptance criteria
- AC1: ship(sku, qty) with qty > level(sku) raises InsufficientStock with message "cannot ship {qty} of {sku!r}: only {current} in stock"; level unchanged; no _levels key created for an unknown SKU. qty == level succeeds (level 0). qty <= 0 still raises ValueError (checked first).
- AC2: import_csv on "sku,qty\nA,5\n\nB,2\n" → returns 2, level A=5, B=2. CRLF, UTF-8 BOM, header column order/case/whitespace, whitespace-only lines and all-empty-field rows (",") are handled per rulings.
- AC3: bad rows raise CsvImportError (subclass of ValueError) with `.line` == N and str starting "line N: ", N = 1-based physical line where the record starts (header = line 1 when first); inventory unchanged after any error.
- AC4: python -m pytest -q passes with new tests for AC1–AC3; existing 4 tests unmodified; ruff + flake8 clean.

# Stop-and-ask items
- none

# Review focus
CRLF; BOM; blank/whitespace lines before the header and before a bad row (line numbering); quoted fields containing newlines (line = record start); rows of only commas; qty forms "1.5", "1_000", "+5", " 5 ", "", non-ASCII digits; duplicate SKUs; header-only and empty files; unknown-SKU ship not polluting low_stock(); atomicity on error.

# Constraints
- stdlib only; existing tests unchanged (fixed points); InsufficientStock stays a plain Exception subclass (existing public class).

# Rulings
- Ruling: import_csv is an instance method calling self.receive per row, returns number of rows received — request says "calls receive() for each row" — cost if wrong: trivial wrapper for a classmethod.
- Ruling: header row required; matched case-insensitively after strip, located by name (any column order, extra columns allowed and ignored) — "columns sku,qty" implies a header — cost if wrong: headerless files rejected with "line 1: missing header row 'sku,qty'" / header error.
- Ruling: validate every row before receiving any (all-or-nothing) — a half-imported file is worse than none and hard to retry — cost if wrong: user wanting partial import must split the file.
- Ruling: a "blank line" is any record whose fields are all empty after strip (includes "", "   ", ",") — spreadsheet exports emit comma-only rows — cost if wrong: a stray "," row is silently skipped rather than flagged.
- Ruling: qty must fullmatch r"[+-]?[0-9]+" after strip, then must be > 0 — int() alone accepts "1_000" and non-ASCII digits — cost if wrong: those odd forms are rejected.
- Ruling: sku and qty are stripped of surrounding whitespace; empty sku is an error; SKU case preserved.
- Ruling: file opened with encoding="utf-8-sig", newline="" — handles BOM and CRLF — cost if wrong: non-UTF-8 files raise UnicodeDecodeError (propagates).
- Ruling: FileNotFoundError / UnicodeDecodeError propagate unwrapped; csv.Error is wrapped as CsvImportError "line N: malformed CSV: <err>".
- Ruling: new exception CsvImportError(ValueError) in inventory/stock.py with attribute .line — "clear error naming the line number"; ValueError base keeps generic handlers working.

# Tasks
## T1 ship overdraw fix + import_csv — tier: haiku — mode: sequential (main tree) — AC: AC1–AC4
- Worktree: main tree
- Files: inventory/stock.py, tests/test_stock.py (append only), tests/test_import_csv.py (new)
- Depends on: none
- Interfaces:
  - Consumes: Inventory.receive(sku, qty), InsufficientStock
  - Produces: class CsvImportError(ValueError) with __init__(self, line, message), attr .line; Inventory.import_csv(self, path) -> int
- Tests allowed to change: none (append new tests only)
- Status: pending

# Shared-surface check
| Tasks | Shared file / interface | Resolution |
|---|---|---|
| (single task) | — | — |

# Log
- T1 dispatched (orch-worker-haiku, main tree)
- T1 DONE (f40bd14), 40 passed, lint clean; only old-test change is the allowed import line
- iter 1 verify (orch-verifier): PASS on AC1–AC4; should-fix: (F1) lenient csv.reader silently swallows rows after an unterminated quote in last/ignored column — root cause: brief didn't specify strict mode; (F2) duplicate sku/qty header columns silently use first; (F3) untested: non-ASCII digits, csv.Error wrapping, header error line after blank lines. Nits: CsvImportError not picklable, >4300-digit qty gives unnumbered ValueError, exact field count rejects trailing comma, dead code in test_stock.py, misnamed test_import_csv_empty_file.
- Ruling: F1 is a bad row under AC3 (silent data loss defeats the all-or-nothing ruling) — fix with csv.reader(strict=True).
- Ruling: duplicate 'sku' or 'qty' header column → CsvImportError "duplicate column {name!r} in header" — ambiguous input must not guess.
- Ruling: nits pickling / 4300-digit / trailing-comma left as open items for the user; test-file dead code + misnamed test fixed in the same round (cheap).
- fix 1 (F1–F3 + test nits, round 1, orch-worker-sonnet): dispatched
- fix 1 DONE (d20a1c2), 52 passed, lint clean
- fix 1 re-check (orch-rechecker): PASS; findings 1–4 ADDRESSED (3 mutants now killed); no new breakage. Noted: strict mode now rejects `"A" ,5` (RFC-4180-invalid) — accepted as a deliberate tightening.
- DONE. Report: .orchestrator/report.md. .orchestrator/ kept at user's request.
