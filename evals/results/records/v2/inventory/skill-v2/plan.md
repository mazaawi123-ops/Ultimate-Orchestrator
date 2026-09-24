# Goal
Stop `Inventory.ship()` driving stock negative: shipping more than the current level must raise
the existing `InsufficientStock` and leave the level unchanged. Add `Inventory.import_csv(path)`
that reads a `sku,qty` CSV and calls `receive()` per row, skips blank lines, and raises a clear
error naming the line number for bad rows. Tests for both. Done = both behaviours tested, full
suite green, an independent verifier agrees.

# Baseline
- branch: orch/inventory-ship-csv, from main (uncommitted work: none)
- BASE: 167b0db3cbb04d0c03e3cdb2101f11b0af732e1b
- tests at BASE: `python3 -m pytest -q` → 4 passed; pre-existing failures: none
- lint at BASE: no linter installed; `python3 -m compileall -q inventory tests` → ok (covers both dirs)
- clean-room test command: n/a: no external services
- repo notes: .orchestrator/notes.md (pasted into every brief)
- estimate given to the user: 2 Haiku workers, 1 Opus verifier, likely 1 Sonnet fix + 1 Sonnet
  re-check: ~400k tokens, ~90k on Opus (plus the planner)
- mode: full hierarchy at the user's explicit request (the size alone would justify direct mode)

# Acceptance criteria
- AC1: `ship(sku, qty)` with qty > level raises `InsufficientStock` and the level is unchanged
  (also for an unknown SKU, level 0). qty == level succeeds and leaves level 0. qty <= 0 still
  raises ValueError (checked before the stock check).
- AC2: `import_csv(path)` on `"sku,qty\nA,5\n\nB,2\n"` → level A=5, B=2, returns 2. Blank lines
  (empty, whitespace-only, or only commas/whitespace like `,` or ` , `) are skipped anywhere,
  including before the header. Accepts `str` or `pathlib.Path`. CRLF and a UTF-8 BOM work.
- AC3: a bad row raises `ValueError` whose message starts with `line N: ` where N is the
  physical 1-based line number (header line = 1, blank lines counted). Bad = wrong column count,
  empty sku, qty not matching `[0-9]+` after stripping, qty == 0. Missing/incorrect header also
  raises `line N: ...`. After any such error the inventory is completely unchanged.
- AC4: `python3 -m pytest -q` passes (4 old tests untouched + new tests for AC1–AC3) and
  `python3 -m compileall -q inventory tests` is clean.

# Stop-and-ask items
- none (stdlib only, no external services, no data, no deps)

# Review focus
- ship: boundary qty == level, qty == level + 1, unknown sku, level unchanged after the raise
- CSV: CRLF line endings; UTF-8 BOM before header; blank lines before the header and before a
  bad row (line number must count them); whitespace around fields; trailing comma (3 columns);
  rows of only commas; quoted fields; negative / decimal / `5_0` / unicode-digit (`５`) qty
  (Python `int()` accepts `5_0` and `５` — must be rejected); qty `0`; duplicate SKUs across
  rows (accumulate); header-only file; empty file; missing header; header in wrong case / order
  (`SKU,QTY`, `qty,sku`); partial import after an error (must not happen); nonexistent path

# Constraints
- stdlib only (README: "Tiny stdlib-only"); use the `csv` module.
- Existing 4 tests in tests/test_stock.py are fixed points; none may change.
- Public behaviour of receive/level/low_stock unchanged.

# Rulings
- Ruling: `InsufficientStock` message is `f"cannot ship {qty} of {sku!r}: only {current} in stock"`,
  no new attributes — callers only need the type; message aids debugging — cost if wrong: trivial
  to add attributes later.
- Ruling: qty <= 0 check stays first in ship() (ValueError wins over InsufficientStock) — keeps
  existing contract — cost if wrong: none realistic.
- Ruling: header row required: first non-blank row, fields stripped and lowercased, must equal
  `["sku", "qty"]`; otherwise `ValueError("line N: expected header 'sku,qty'")` — request says
  "columns sku,qty"; accepting case differences is harmless; reordered columns are rejected rather
  than silently guessed — cost if wrong: headerless or `qty,sku` files are rejected with a clear message.
- Ruling: blank row = every field is empty after `.strip()` (covers `""`, `"   "`, `","`, `" , "`)
  → skipped — spreadsheet exports produce comma-only rows; they carry no data — cost if wrong: a
  genuinely broken all-empty row is silently skipped rather than reported.
- Ruling: validate every row first, then call `receive()` for each valid row in file order —
  a half-imported file is worse than none — cost if wrong: users wanting partial import must split files.
- Ruling: qty must match `re.fullmatch(r"[0-9]+", qty)` after strip and be > 0 — `int()` alone
  accepts `+5`, `5_0`, `５` — cost if wrong: `+5` is rejected (clear message).
- Ruling: sku is stripped; case preserved; duplicates accumulate via receive() — request says
  "calls receive() for each row" — cost if wrong: none.
- Ruling: line number = `csv.reader.line_num` after reading the row (physical line where the record
  ends; equals the physical line for any record without an embedded newline) — cost if wrong: a
  quoted multi-line field reports its last line.
- Ruling: file opened with `open(path, newline="", encoding="utf-8-sig")` — csv docs require
  newline=""; utf-8-sig strips an Excel BOM — cost if wrong: non-UTF-8 files raise UnicodeDecodeError.
- Ruling: empty file or only blank lines → returns 0, no error; header-only → returns 0 — no bad row
  exists — cost if wrong: an accidentally empty file goes unnoticed.
- Ruling: errors are plain `ValueError` (no new exception class), messages exactly:
  `line N: expected header 'sku,qty'`, `line N: expected 2 columns (sku,qty), got K`,
  `line N: missing sku`, `line N: qty must be a positive integer, got '<raw stripped qty>'` —
  matches existing ValueError style; tests match on `^line N: ` — cost if wrong: callers wanting a
  line attribute must parse the message.
- Ruling: `import_csv` returns the number of rows received (int) — useful and cheap — cost if wrong: none.
- Ruling: nonexistent path → FileNotFoundError propagates unchanged — standard — cost: none.

# Tasks
## T1 fix ship overdraw — tier: haiku — mode: sequential — AC: AC1, AC4
- Worktree: main tree (on orch/inventory-ship-csv)
- Files: inventory/stock.py, tests/test_stock.py (append only)
- Depends on: none
- Interfaces: Consumes `InsufficientStock`, `Inventory._levels`. Produces unchanged `ship(sku, qty)` signature.
- Tests allowed to change: none (appending new tests is fine)
- Status: pending

## T2 import_csv — tier: haiku — mode: sequential, after T1 — AC: AC2, AC3, AC4
- Worktree: main tree
- Files: inventory/stock.py, tests/test_import_csv.py (new)
- Depends on: T1
- Interfaces: Consumes `Inventory.receive(sku, qty)`. Produces `Inventory.import_csv(path) -> int`.
- Tests allowed to change: none
- Status: pending

# Shared-surface check
| Tasks | Shared file / interface | Resolution |
|---|---|---|
| T1, T2 | inventory/stock.py | sequential |

# Log
- T1 (haiku, 32k tokens): DONE, commit c9f45d3. Checked: 9 passed; old-tests shows only the import line changed (allowed); RED/GREEN in report. T1 status → DONE.
- T2 (haiku, 46k tokens): DONE, commit f00d929. Checked: 38 passed, compileall ok, old-tests only import line. Mutant evidence in report came from ad-hoc scripts, not the suite run against the mutant — weaker than asked; left to the verifier to probe test strength rather than a re-dispatch. Noted: T1's commit subject has the co-author trailers glued onto the subject line (cosmetic; not rewriting history).
- verify 1: full Opus verifier on diff-1.patch (BASE 167b0db..HEAD f00d929)
- verify 1 (opus, 55k tokens): PASS on AC1–AC4. Mutation run: 21/23 mutants caught. 4 nits, no blockers/should-fix/challenged rulings.
  - Ruling: nit "no test for a quoted field with embedded newline (enumerate-vs-line_num and missing newline='' mutants survive)" → report, no fix round — nit severity, the code follows the ruling today; a fix round + scoped re-verify costs ~180k for one test — cost if wrong: a future refactor could silently change multi-line-record line numbers.
  - Ruling: nit "csv.Error for >131072-char field isn't wrapped as 'line N:' ValueError" → report — pathological input, inventory still unchanged — cost if wrong: one class of bad file gets a less clear error.
  - Ruling: nit "step comments restate code" and pre-existing "float qty accepted by receive/ship" → report only; the latter is out of scope.
- No fix rounds. Final: 38 passed, compileall clean, git status clean. .orchestrator/ kept at the user's request.
