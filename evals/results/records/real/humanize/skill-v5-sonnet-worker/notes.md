# Repo notes (humanize)
- Layout: src/humanize/<module>.py, public API re-exported in src/humanize/__init__.py (import + alphabetical `__all__`). Tests in tests/test_<module>.py (pytest, heavy use of @pytest.mark.parametrize, call via `humanize.<fn>`).
- Tests: `python3 -m pytest -q --benchmark-disable` (PYTHONPATH=src already set). BASE: 744 passed, 112 skipped, 0 failing.
- Doctests are NOT run by the default command (pyproject pytest config wins over tox.ini). Check them with: `python3 -m pytest -q --benchmark-disable --doctest-modules -p no:cacheprovider src/humanize/filesize.py src/humanize/lists.py` (BASE: 2 passed).
- Lint: `ruff check --no-fix src tests && ruff format --check src tests` (clean at BASE). NB: pyproject sets ruff `fix = true`, so plain `ruff check` rewrites files — always pass --no-fix. Types: `mypy src` (clean at BASE; ignore the "num_workers" config warning).
- Style: `from __future__ import annotations`; Google-style docstrings with Examples (```pycon blocks in filesize.py), Args, Returns; full type hints. Docs pages use mkdocstrings (`::: humanize.filesize`), so docstrings are the docs.
- filesize.py: `suffixes` dict (decimal kB..QB base 1000, binary KiB..QiB base 1024, gnu "KMGTPEZYRQ" base 1024) and `naturalsize`. Output forms: "1 Byte", "0 Bytes", "-1 Byte", "3.0 MB", "2.9 KiB", "2.9K", "300B", "1B" (gnu), "1.0 QB", "30000.0 QB", "-4.0 KiB". Suffix/Byte strings go through gettext `_()` (translations may change them).
- `__init__.py` uses `__lazy_modules__`; keep the existing import pattern (just add the name to the existing `from humanize.filesize import ...` line).
- lists.py: `natural_list(items)` joins with ", " and " and " (no Oxford comma); has `__all__`.
