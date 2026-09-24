# Repo notes: todo-cli
- Python 3.11.15, stdlib only (README says "stdlib-only"). No dependency files exist; don't add any.
- Layout:
  - todo/store.py — class Store: JSON-backed list of dicts {"id": int, "title": str, "done": bool}.
    __init__(path) loads the file if it exists; save() rewrites the whole file (json.dumps indent=2);
    add(title) -> item; complete(item_id) -> item (KeyError if missing); list(include_done=False) -> list.
  - todo/cli.py — main(argv=None): argparse, prog="todo". Global `--db` (default env TODO_DB or
    "todo.json") must come BEFORE the subcommand: main(["--db", path, "add", "x"]).
    Subcommands add/done/list. Output lines: `added #1: title`, `done #1`, `[ ] #1 title` / `[x] #1 title`.
  - tests/test_store.py — 3 pytest tests using tmp_path. Plain functions, no classes, no fixtures file.
  - README.md — 3 lines: title, how to run tests, usage line.
- Tests: `python -m pytest -q` (from repo root). Baseline: 3 passed.
- Lint: no linter installed (no pyflakes/ruff). Use `python -m compileall -q todo tests` (exit 0 = ok).
- Style to imitate: tests/test_store.py (short plain test functions, tmp_path), todo/cli.py (compact
  one-line add_parser calls, f-string output).
- .gitignore ignores `*.json`, so test DB files never get committed; always use pytest tmp_path.
- Surprise: on Python 3.11, date.fromisoformat() ALSO accepts "20261001" and "2026-W40-4", so it
  can't be used alone to enforce YYYY-MM-DD. datetime.strptime("%Y-%m-%d") accepts "2026-1-1". Use
  the regex + fromisoformat combination the brief specifies.
- Known failing tests at BASE: none.
