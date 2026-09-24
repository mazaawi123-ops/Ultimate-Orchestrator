# Repo notes
- Tiny stdlib-only Python package. Layout: inventory/stock.py (InsufficientStock, Inventory), inventory/__init__.py (empty), tests/test_stock.py (pytest).
- Tests: `python -m pytest -q` (4 passed at BASE). Lint: `ruff check .` (clean at BASE). No unittest-style tests; `unittest discover` finds 0 — use pytest.
- Tests import `from inventory.stock import Inventory` and `import pytest`; plain functions named test_*, no classes, no fixtures file.
- Inventory keeps `self._levels: dict[str, int]`; receive/ship raise ValueError("qty must be positive") for qty <= 0.
- low_stock() lists every key in _levels, so any write of a key (even 0) shows up there.
- Style: 4 spaces, double quotes, no type hints, no docstrings except the class one.
- Surprise: ship() currently subtracts with no check (the bug; comment "# BUG:" marks it).
- No external services, no secrets, no deps file.
