# Repo notes (todo-cli)
- Python 3.11, stdlib only (no deps). Package `todo/`: `store.py` (Store class, JSON list of dicts), `cli.py` (argparse `main(argv=None)`).
- Tests: pytest-style functions in `tests/`, using `tmp_path` fixture. Run: `python -m pytest -q` (baseline: 3 passed). `python -m unittest` finds 0 tests — don't use it.
- No linter installed; use `python -m py_compile todo/*.py tests/*.py` as a syntax check.
- CLI entry: `python -m todo.cli --db <path> <cmd>`; `--db` defaults to $TODO_DB or `todo.json`.
- Store item shape today: {"id": int, "title": str, "done": bool}; `Store.save()` writes json.dumps(items, indent=2).
- Style: compact, no type hints, no docstrings beyond the class one, f-strings for output. CLI subparsers built one per line (`a = sub.add_parser("add"); a.add_argument(...)`).
- CLI output formats: add → `added #<id>: <title>`; list → `[ ] #<id> <title>` / `[x] ...`.
- `.gitignore` ignores `*.json`, so test DB files never get committed.
- Today's date for the run is 2026-09-23; tests must NOT depend on the real date (inject `today`).
