# Repo notes

- Layout: `todo/store.py` (Store class, JSON-backed), `todo/cli.py` (argparse CLI), `tests/test_store.py` (pytest, uses tmp_path).
- Run tests: `python -m pytest -q` from repo root. No lint config in repo.
- Store.__init__(path) loads JSON list of items if file exists, else empty list.
- Item shape today: {"id": int, "title": str, "done": bool}.
- Store.add(title) -> item; Store.complete(id) -> item; Store.list(include_done=False) -> list of items (open by default).
- Store.save() writes json.dumps(self.items, indent=2).
- cli.py: subparsers "add" (positional title), "done" (positional id:int), "list" (--all flag). main(argv=None) builds Store(args.db) where db defaults to $TODO_DB or "todo.json".
- No existing datetime/date handling anywhere in repo.
- Style: compact, minimal, no docstrings beyond the one class docstring, f-strings for CLI output.
- No CI config found; only test runner is pytest.
