# Repo notes (todo-cli)
- Python 3.11, stdlib only. Package `todo/`: `store.py` (class Store, JSON list of dicts), `cli.py` (argparse `main(argv=None)`), `__init__.py` empty.
- Tests: `python3 -m pytest -q` (pytest style, `tmp_path` fixture) in `tests/`. BASE: 3 passed. No pre-existing failures.
- Lint: `ruff check .` → 4 PRE-EXISTING errors in todo/cli.py lines 10-12 (E702 semicolons, E741 `l`). Don't add new ones; fixing those 4 is allowed but not required.
- DB path: `--db` flag (default env TODO_DB or todo.json). `*.json` is git-ignored.
- Item dict today: {"id": int, "title": str, "done": bool}. Store.save() rewrites whole file with json.dumps(indent=2).
- CLI prints with plain print(); list line format: `[x] #1 title` / `[ ] #1 title`.
- Style: short, no type hints in existing code, docstring only on the class. README.md has a one-line Usage section.
- .orchestrator/ is git-ignored; never commit it.
