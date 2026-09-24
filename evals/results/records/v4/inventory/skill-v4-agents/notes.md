# Repo notes
- Stdlib-only Python package. Files: inventory/__init__.py (empty), inventory/stock.py (InsufficientStock, Inventory), tests/test_stock.py (4 pytest tests).
- Tests: `python -m pytest -q` (from repo root; 4 passed at BASE). `python -m unittest` finds nothing — use pytest.
- Lint: `ruff check . && flake8 inventory tests` (both clean at BASE).
- Style: plain functions-style pytest tests (`import pytest`, `from inventory.stock import ...`, `pytest.raises`), no classes, no docstrings on tests. 4-space indent, double quotes.
- Inventory stores levels in `self._levels` dict; `receive(sku, qty)` raises ValueError("qty must be positive") for qty <= 0.
- `ship()` has a `# BUG:` comment marking the overdraw bug; remove that comment when fixing.
- low_stock() lists every key in _levels below threshold, so creating a key for an unknown SKU is visible behaviour.
- No known failing tests. `.orchestrator/` is git-ignored.
