# Plan: fix ship() oversell + add Inventory.import_csv

Baseline: `python -m pytest -q` → 4 passed (Python 3.11, stdlib only, pytest).
Notes live in `.orchestrator/` (already git-ignored by the repo, so they don't pollute commits).

## Task A — ship() must not go negative (worker A)
- Files owned: `Inventory.ship` body in `inventory/stock.py`; `tests/test_stock.py`.
- Behaviour: if `qty > level(sku)` raise `InsufficientStock`; stock is left unchanged.
  Shipping exactly the level is allowed (→ 0). Unknown SKU counts as level 0.
  `qty <= 0` still raises `ValueError` first (existing behaviour kept).
- Message names the SKU, requested qty and available qty.
- Tests: oversell raises + level unchanged; unknown SKU raises; exact-level ship → 0.

## Task B — Inventory.import_csv(path) (worker B)
- Files owned: new code at top/bottom of `inventory/stock.py` (imports, new exception
  class, new method appended after `low_stock`); new `tests/test_import_csv.py`.
- Must not touch `ship()` (worker A's region).

## Decisions (no one available to ask — recorded here)
1. **Instance method.** `inv.import_csv(path)` — the spec says it "calls receive() for each
   row", which needs an instance. Returns the number of rows imported (int).
2. **Header is optional.** If the first non-blank row is `sku,qty` (case-insensitive,
   whitespace-stripped) it is skipped; otherwise it is treated as data. Tolerates both
   exported files with a header and hand-written ones without.
3. **Blank lines skipped**: empty lines and lines with only whitespace/empty fields
   (e.g. `  ` or `,`).
4. **Bad row → `CSVImportError`**, a new subclass of `ValueError` (so existing
   `except ValueError` callers still catch it), with `.line` (1-based physical line number
   in the file) and a message like `"line 4: qty must be a positive integer, got 'abc'"`.
   Bad = wrong column count, empty SKU, qty not an integer, qty <= 0.
5. **Atomic.** All rows are parsed/validated first; `receive()` is called only if the whole
   file is valid. A bad row on line 900 must not leave lines 1–899 half-applied.
6. Fields are whitespace-stripped; qty accepts integers only (`"3.5"` is bad);
   duplicate SKUs accumulate (natural `receive()` semantics).
7. Open with `encoding="utf-8-sig", newline=""` (tolerates a BOM from Excel, correct
   csv-module usage). Missing file → normal `FileNotFoundError`, not wrapped.

## Verification (verifier agent, independent of workers)
- Full test suite green.
- Review diff against this plan; adversarial edge-case probing (BOM, CRLF, quoted fields,
  whitespace lines, header-only file, bad line numbers after blank lines, atomicity).
- Writes findings to `.orchestrator/verification.md`. Orchestrator fixes anything real,
  re-runs tests, writes `.orchestrator/report.md`, commits.
