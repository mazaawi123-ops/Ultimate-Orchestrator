# Goal
Stop Inventory.ship() driving stock negative (raise the existing InsufficientStock), and add
Inventory.import_csv(path) that bulk-receives from a sku,qty CSV, skips blank lines, and raises
an error naming the line number for bad rows. Tests for both. User unavailable: rulings below.

# Baseline
- branch: orch/inventory-fix-csv, from main (uncommitted work: none)
- BASE: 167b0db3cbb04d0c03e3cdb2101f11b0af732e1b
- tests at BASE: python -m pytest -q → 4 passed; pre-existing failures: none
- lint at BASE: ruff check . → All checks passed (covers whole repo)
- clean-room test command: n/a: no external services
- repo notes: .orchestrator/notes.md
- estimate given to the user: ~$0.8–2.5 (1 Haiku worker, 1 Opus verifier, Opus planner)

# Acceptance criteria
- AC1: ship(sku, qty) with qty > level raises InsufficientStock; level unchanged; no new key created for an unknown SKU (low_stock() unaffected); qty == level succeeds → 0; qty <= 0 still ValueError.
- AC2: import_csv on b"sku,qty\nA,5\n\nB,2\n" → level A=5, B=2, returns 2 (blank line skipped). Whitespace-only lines and all-empty rows like "," or " , " are blank too.
- AC3: bad row → CsvImportError (subclass of ValueError) whose str starts "line N: " with N = 1-based physical line where the record starts (header = line 1, blank lines counted); e.line == N; inventory completely unchanged after the error (no partial import).
- AC4: CRLF files and a UTF-8 BOM import correctly; duplicate SKUs sum via receive().
- AC5: python -m pytest -q passes (4 existing untouched + new tests for AC1–AC4); ruff check . clean.

# Stop-and-ask items
- none

# Review focus
CRLF; BOM; blank lines before a bad row (line number must count them); quoted field containing a
newline; header column order (qty,sku); header case/whitespace; rows of only commas; too many / too
few fields; qty "1.5", "abc", "", "0", "-3", " 7 "; empty file; header-only file; missing header;
unknown SKU ship; exact-level ship; file with bad row after good rows (atomicity).

# Constraints
- stdlib only (csv module); no new deps — README says stdlib-only.
- Existing 4 tests unchanged.
- Public API: Inventory.ship/receive/level/low_stock signatures unchanged.

# Rulings
- Ruling: header row required; its stripped, lower-cased fields must be exactly {"sku","qty"} (2 columns, either order) — request says "columns sku,qty", implying a header — cost if wrong: headerless files rejected with a clear line-1 error.
- Ruling: validate every row before calling receive() on any — half-imported file is worse than none — cost if wrong: user wanting partial import must split the file.
- Ruling: bad-row error is new `CsvImportError(ValueError)` in inventory/stock.py with `.line` and `.reason`, message "line N: <reason>" — callers catching ValueError still work; attribute lets code get the number — cost if wrong: trivial rename.
- Ruling: a row whose fields are all empty/whitespace (incl. "," ) counts as blank and is skipped — spreadsheet exports emit these — cost if wrong: such rows silently ignored instead of rejected.
- Ruling: N = line where the record starts (reader.line_num before reading + 1) — matters only for quoted multi-line fields — cost if wrong: off by some lines for multi-line records.
- Ruling: file opened with encoding="utf-8-sig", newline="" — tolerates Excel BOM and CRLF — cost if wrong: none known.
- Ruling: import_csv returns the number of rows received (int); empty or header-only file → 0, no error — useful and harmless — cost if wrong: none.
- Ruling: missing file → FileNotFoundError propagates unchanged — standard Python behaviour.
- Ruling: InsufficientStock message "cannot ship {qty} of {sku!r}: only {current} in stock"; raised before any write — cost if wrong: message wording.
- Ruling: qty parsed with int(raw.strip()) so "+3" is accepted as 3, "1.5" rejected — cost if wrong: minor.

# Tasks
## T1 ship guard + import_csv — tier: haiku — mode: sequential — AC: AC1–AC5
- Worktree: main tree
- Files: inventory/stock.py, tests/test_stock.py (append only), tests/test_import_csv.py (new)
- Depends on: none
- Interfaces:
  - Consumes: Inventory.receive(sku, qty), InsufficientStock
  - Produces: Inventory.import_csv(path) -> int; class CsvImportError(ValueError) with .line, .reason
- Tests allowed to change: none (append new tests only)
- Status: pending

# Shared-surface check
| Tasks | Shared file / interface | Resolution |
|---|---|---|
| (single task — both pieces batched into T1, same file) | inventory/stock.py | one worker |

# Log
- start: branch created, baseline 4 passed, ruff clean
- T1 dispatched (haiku)
- T1 DONE (45caa45), 33 passed
- verify 1 (opus): PASS on AC1–AC5. Findings: should-fix lenient csv.reader accepts unterminated quote / `"A"x`; ruling challenged int() accepts "1_000" and non-ASCII digits; nits: header index lookup shadows `f`, huge qty in message, UnicodeDecodeError has no line.
- Ruling (revised): qty must fullmatch r"[+-]?[0-9]+" before int() — "1_000"/"٣" are almost certainly typos/garbage in a stock file — cost if wrong: such values rejected with a clear line error.
- Ruling: use csv.reader(f, strict=True) — malformed quoting must be an error with a line number, not silently imported.
- Ruling: nits on huge-qty message and UnicodeDecodeError left as open items — low value, ValueError still raised, inventory unchanged.
- fix 1 (round 1, sonnet): strict=True + ASCII-digit qty + header lookup cleanup — dispatched
- fix 1 DONE (d124de2), 39 passed
- verify 2 (sonnet, scoped): PASS; findings 1–3 ADDRESSED; no pre-existing test changed. Noted: `"A" ,5` (space after closing quote) now rejected under strict mode.
- Ruling: accept rejecting `"A" ,5` — same malformed-quoting class as `"A"x`, reported with its line number — cost if wrong: a user with sloppy quoting must clean the file.
- DONE. Report: .orchestrator/report.md
