# Goal
Stop `Inventory.ship()` driving stock negative (raise the existing `InsufficientStock`, level
unchanged), and add `Inventory.import_csv(path)` that bulk-receives from a `sku,qty` CSV,
skipping blank lines and raising a clear error naming the line number for bad rows. Tests for both.
Done = both behaviours implemented, tested, full suite + lint green, independently verified.

# Baseline
- branch: orch/inventory-fix-csv, from main (uncommitted work: none)
- BASE: 167b0db3cbb04d0c03e3cdb2101f11b0af732e1b
- tests at BASE: `python -m pytest -q` → 4 passed; pre-existing failures: none
- lint at BASE: `ruff check .` → All checks passed (covers every .py file)
- clean-room test command: n/a: no external services
- repo notes: .orchestrator/notes.md
- estimate given to the user: 1 Haiku worker + 1 Opus verifier, Opus planner, ~$2.5–3

# Acceptance criteria
- AC1: `ship(sku, qty)` with qty > level raises `InsufficientStock`; level unchanged; qty == level succeeds (level 0); shipping an unknown SKU raises `InsufficientStock` and creates no key (`low_stock()` stays `[]`).
- AC2: `import_csv` on `"sku,qty\nA,5\n\nB,2\nA,3\n"` returns 3 and leaves A=8, B=2 (blank line skipped, duplicate SKUs accumulate). Accepts `str` and `pathlib.Path`.
- AC3: a bad row raises `CsvImportError` (subclass of `ValueError`) whose message contains `line N` (N = 1-based physical line where the record starts, header = line 1) and whose `.line == N`; inventory is unchanged after any error (all-or-nothing).
- AC4: `python -m pytest -q` passes and `ruff check .` is clean; the 4 existing tests are untouched; new tests cover AC1–AC3 incl. the review-focus cases.

# Stop-and-ask items
- none

# Review focus
CRLF line endings; UTF-8 BOM; whitespace-only lines; blank lines before a bad row (line
numbering); comma-only rows (must NOT be treated as blank); quoted fields containing newlines
(line of record start); header case / column order / extra columns; header-only file; empty file;
qty `0`, `-1`, `2.5`, `1_000`, `''`, `abc`; missing sku; wrong field count; missing file.

# Constraints
- Stdlib only (README). No change to `InsufficientStock`'s base class or existing tests.
- `inventory/__init__.py` stays as is (tests import from `inventory.stock`).

# Rulings
- Ruling: header row required, first non-blank line, fields compared after `.strip().lower()` must equal `["sku","qty"]` exactly — request says "columns sku,qty" — cost if wrong: headerless files rejected with a clear line-1 error.
- Ruling: validate every row before calling `receive()` on any — a half-imported file is worse than none — cost if wrong: user wanting partial import must split the file.
- Ruling: blank line = csv row `[]` or a single field that is whitespace-only; comma-only rows (`,`) are bad rows, not blank — avoids silent data loss — cost if wrong: files with trailing comma rows fail loudly.
- Ruling: sku and qty are `.strip()`ped; qty must match `[0-9]+` (ASCII, no sign/underscore/decimal) and be > 0 — fail loudly on anything else — cost if wrong: `+5`/`1_000` rejected.
- Ruling: error class `CsvImportError(ValueError)` in stock.py with `.path`, `.line`, `.reason`; message `"{path}: line {line}: {reason}"` — ValueError subclass keeps generic handlers working — cost if wrong: rename.
- Ruling: file opened with `encoding="utf-8-sig", newline=""` (tolerates Excel BOM) — cost if wrong: non-UTF-8 files raise UnicodeDecodeError.
- Ruling: empty / all-blank file → `CsvImportError` line 1 "missing header"; header-only file → returns 0 — fail loudly on no header.
- Ruling: missing file → `FileNotFoundError` propagates unchanged.
- Ruling: `import_csv` returns number of rows received (int).
- Ruling: `InsufficientStock` message `"cannot ship {qty} of {sku!r}: only {current} in stock"`.

# Tasks
## T1 ship overdraw fix + import_csv — tier: haiku — mode: sequential (main tree) — AC: AC1–AC4
- Worktree: main tree
- Files: inventory/stock.py, tests/test_stock.py (append only), tests/test_import_csv.py (new)
- Depends on: none
- Interfaces:
  - Consumes: `Inventory.receive(sku, qty)`, `InsufficientStock`
  - Produces: `class CsvImportError(ValueError)` with `__init__(self, path, line, reason)`; `Inventory.import_csv(self, path) -> int`
- Tests allowed to change: none (append new tests only)
- Status: pending

# Shared-surface check
| Tasks | Shared file / interface | Resolution |
|---|---|---|
| (single task) | — | — |

# Log
- T1 DONE (e032492, haiku), 36 passed, ruff clean
- iter 1 verify (opus): FAIL. AC3: csv.Error (e.g. field > 131072 from stray quote) escapes unwrapped, no line no. AC4: missing tests (ship qty<=0, non-ASCII digits, non-UTF-8). should-fix: quoted newline in SKU accepted -> rows silently merged ('"A,1\nB",2' stored as one SKU). nit: int() of >4300 digits raises bare ValueError; test style (inner imports, "Case N" docstrings). ruling challenged (low): SKU strip.
  Root cause: plan's review focus didn't cover csv.Error or control chars in SKU; brief's case 30 locked the multi-line SKU acceptance in.
- Ruling: wrap csv.Error as CsvImportError at record start line, reason "malformed CSV: <err>" — fail loudly with line — low cost.
- Ruling: reject SKU containing any control char (ord<32 or ==127), reason "sku contains control characters" — prevents silent row merge — cost: SKUs with tabs rejected.
- Ruling: int() ValueError (huge qty) -> same "qty must be a positive integer" CsvImportError.
- Ruling (challenge rejected): keep SKU strip — whitespace around CSV fields is formatting noise; documented in import_csv docstring.
- Ruling: non-UTF-8 stays UnicodeDecodeError (verifier accepted); add a test.
- Tests 30/31 (new in this change, not BASE) may change to expect the control-char error at line 2.
- fix 1 (findings 1-5, round 1, sonnet): 6f0dee2, 47 passed, ruff clean. Ruling: control-char check is import_csv-only; receive/ship unchanged (out of scope).
- recheck 1 (sonnet): PASS — findings 1-5 ADDRESSED, AC1-AC4 PASS, no new breakage. Run complete.
