## Result: done
Shipping more than the stock level now raises `InsufficientStock`, and `Inventory.import_csv(path)` is added. Tests cover both.

- **Built:**
  - `ship()` raises `InsufficientStock("cannot ship 6 of 'A': only 5 in stock")` when you try to ship more than you have. The stock level doesn't change. Shipping exactly what's in stock still works and leaves 0. A failed ship of an unknown SKU no longer adds that SKU to `low_stock()`.
  - `import_csv(path)` returns the number of rows it received. It skips blank lines and rows that are only commas, and handles Windows line endings and a byte-order mark at the start of the file.
  - Bad rows raise a new `CsvImportError`, a subclass of `ValueError`. It has a `.line` attribute and a message like `line 4: qty 'abc' is not an integer`. The line number is where the record starts in the file.
- **Acceptance criteria:** 4 of 4 met.
- **Tests:** `python -m pytest -q` gives 52 passed (4 existed before). Lint (ruff and flake8) is clean. The 4 original tests are unchanged.
- **Iterations:** the independent check passed the first build but found three problems, all now fixed:
  1. An unclosed quote made the importer silently drop the rows after it. It now uses strict CSV parsing and raises `line N: malformed CSV: …`.
  2. A header with a duplicate column, like `sku,qty,qty`, silently used the first one. It is now rejected.
  3. Three of my rules had no tests. The new tests fail when the code is deliberately broken, so they do check the rules.

  A second check confirmed the fixes and found nothing new broken.
- **Decisions I made without you** (all are in `plan.md`):
  - The first non-blank line must be a header containing `sku` and `qty`. Column order, letter case and extra columns don't matter.
  - The import is all-or-nothing: every row is checked before any stock is received. If one row is bad, nothing is imported.
  - A row with nothing but commas counts as a blank line and is skipped.
  - `qty` must be a whole number written with ASCII digits, and greater than 0. `1.5`, `1_000` and non-Latin digits are rejected.
  - A missing file raises the normal `FileNotFoundError`. A file that isn't UTF-8 raises the normal `UnicodeDecodeError`.
- **Open items** (minor, left as they are):
  - `CsvImportError` can't be pickled.
  - A `qty` longer than 4,300 digits raises a plain `ValueError` without a line number.
  - Every row must have the same number of fields as the header, so a trailing comma rejects the file.
  - Strict parsing rejects badly formed quoting like `"A" ,5`.
- **Not verified:** none.
- **Branch:** `orch/inventory-fix-csv` from `main` at `167b0db`, commits `f40bd14` and `d20a1c2`. Not pushed. To take it: `git merge orch/inventory-fix-csv`.
- **How it ran:** one worker plan (Opus planner). The build was done by one Haiku worker and checked by one Opus verifier. The fix round was one Sonnet worker, re-checked by one Sonnet checker. I estimated about $2–2.5, plus about $0.45 for the fix round.

Everything I wrote along the way is kept in `.orchestrator/`, which git ignores:
- `plan.md`: plan, rulings and a log of each step
- `notes.md`
- `report.md`
- `task-1-report.md` and `fix-1-report.md`: the workers' reports
- `diff-1.patch`, `diff-2.patch` and `fix-1.patch`