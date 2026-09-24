# Repo notes
- Layout: inventory/stock.py (InsufficientStock + Inventory), inventory/__init__.py (empty), tests/test_stock.py (4 pytest tests), README.md.
- Stdlib only (README says so). No pyproject/requirements.
- Tests: `python -m pytest -q` (4 passed at BASE). Lint: `ruff check .` (clean at BASE; covers all .py files).
- Tests import `from inventory.stock import Inventory`; pytest style with `pytest.raises`, plain functions, no classes.
- Inventory stores levels in `self._levels` dict; `level()` uses `.get(sku, 0)` so unknown SKUs read 0 without creating a key.
- `receive`/`ship` raise ValueError("qty must be positive") for qty <= 0.
- Bug: `ship()` subtracts without checking stock (marked `# BUG` comment).
- `InsufficientStock(Exception)` already exists in stock.py, unused.
- `.orchestrator/` is git-ignored; don't commit it.
