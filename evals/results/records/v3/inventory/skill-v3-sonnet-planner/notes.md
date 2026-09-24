# Notes

Layout: single-package stdlib-only Python project.
- `inventory/stock.py` — Inventory class, InsufficientStock exception (already defined, unused).
- `tests/test_stock.py` — pytest tests.
- `inventory/__init__.py` — empty.

Test command: `python -m pytest -q` (run from repo root). Baseline: 4 passed, 0 failed.
No lint config found (no flake8/ruff/pylint config) — skip lint step.

Conventions: plain classes, ValueError for bad qty args, docstring on class only,
no type hints used currently, no external deps (pytest is the only dev dep).

Bug: `Inventory.ship` (stock.py:16-21) lets qty exceed current stock, going negative.
Must raise `InsufficientStock` (already defined at top of stock.py) instead, and leave
stock unchanged when it raises.

New method: `Inventory.import_csv(path)` — reads CSV with header `sku,qty`, calls
`self.receive(sku, int(qty))` per row, skips blank lines, raises a clear error naming
the 1-based line number (counting the header as line 1) for malformed rows (wrong column
count, non-integer qty, non-positive qty, etc).
