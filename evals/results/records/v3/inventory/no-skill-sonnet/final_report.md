Done. Both changes are in `inventory/stock.py`, with tests in `tests/test_stock.py`, and an independent verifier agent confirmed correctness.

**Bug fix**: `ship()` now raises `InsufficientStock(f"cannot ship {qty} of {sku!r}: only {current} in stock")` when `qty > current`, leaving stock unchanged (shipping the exact full quantity to 0 still works).

**`import_csv(path)`**: reads `sku,qty` via the stdlib `csv` module, skips blank lines, calls `self.receive(sku, qty)` per row, and raises `ValueError` naming the 1-indexed file line number for malformed rows (wrong column count, missing sku, non-integer or non-positive qty). Rows applied before a bad one stay applied (no transactional rollback, matching "calls receive() for each row").

14/14 tests pass. The verifier independently re-derived the line-numbering logic, checked edge cases (empty/header-only file, duplicate SKUs, unknown-SKU ship, nonexistent path), and grepped for other `.ship(` callers that might depend on the old negative-stock behavior — found none.

Notes/plan kept at `scratchpad/plan.md` for the record.