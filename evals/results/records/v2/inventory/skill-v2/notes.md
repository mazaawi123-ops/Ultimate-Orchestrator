# Repo notes
- Layout: `inventory/stock.py` (the whole module: `InsufficientStock(Exception)`, `Inventory`),
  `inventory/__init__.py` (empty), `tests/test_stock.py` (4 pytest tests). Nothing else.
- Stdlib only (README says so). Python 3.11, pytest 9.1 available. No pyproject/requirements.
- Tests: `python3 -m pytest -q` from the repo root (4 passed at BASE).
- Lint: no linter installed. Use `python3 -m compileall -q inventory tests` (syntax check of both dirs).
- Conventions: plain functions/methods, no type hints, no docstrings except the class one-liner,
  `ValueError("qty must be positive")` style short lowercase messages. Tests are plain pytest
  functions, `inv = Inventory()` then asserts, `pytest.raises(...)` for errors.
- `Inventory._levels` is a dict sku -> int. `receive(sku, qty)` raises ValueError if qty <= 0,
  else adds. `ship(sku, qty)` raises ValueError if qty <= 0, then (BUG) subtracts without a check.
  `level(sku)` returns 0 for unknown SKUs. `low_stock(threshold=5)` returns sorted SKUs with level < threshold.
- Surprise: ship() to exactly 0 leaves the sku in `_levels` with 0, so it appears in low_stock(). Keep that.
- `.orchestrator/` is git-ignored (.gitignore). `.claude/` is excluded via .git/info/exclude — never touch it.
