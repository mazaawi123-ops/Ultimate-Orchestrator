# Repo notes (humanize)
- Layout: src/humanize/*.py (package), tests/test_*.py (pytest, heavy use of @pytest.mark.parametrize with `test_args, expected`), docs/*.md use mkdocstrings (`::: humanize.filesize`) so new public functions are documented from docstrings automatically.
- Tests: `python3 -m pytest -q --benchmark-disable` (PYTHONPATH=src already set). BASE: 744 passed, 112 skipped, 0 failing.
- Lint: `ruff check --no-fix src tests && mypy src` (clean at BASE). NOTE: pyproject sets ruff `fix = true`, so plain `ruff check` rewrites files — always pass `--no-fix`.
- Public API: src/humanize/__init__.py imports each function and lists it in an alphabetical `__all__`.
- src/humanize/filesize.py: `suffixes` dict (decimal kB..QB, binary KiB..QiB, gnu "KMGTPEZYRQ") and `naturalsize(value, binary=False, gnu=False, format="%.1f")`. Output forms: "1 Byte", "300 Bytes", "1.0 kB", "2.9 KiB", "300B", "2.9K", negatives like "-4.0 KiB". Suffixes pass through gettext `_()`.
- src/humanize/lists.py: `natural_list(items)` joins with ", " and " and " (no Oxford comma); has `__all__ = ["natural_list"]`.
- Docstrings: Google style with `Examples:` in ```pycon fenced blocks (see naturalsize), `Args:`, `Returns:`. Doctests are not collected by pytest, but keep examples correct.
- `from __future__ import annotations` at top of every module; type hints everywhere (mypy strict-ish).
