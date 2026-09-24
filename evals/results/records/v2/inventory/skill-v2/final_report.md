I've fixed the `ship()` bug and added `Inventory.import_csv(path)`, with tests for both. The full suite passes (38 tests), and an independent verifier checked the change and passed it. The work is on a new branch, `orch/inventory-ship-csv`, made from `main` at `167b0db`. Nothing is pushed.

**What changed**
- **`ship()`:** shipping more than the current stock now raises `InsufficientStock` and leaves the stock unchanged. That includes a SKU that has never been received. Shipping exactly the current stock still works and leaves 0. Zero or negative quantities still raise `ValueError`, as before.
- **`import_csv(path)`:** reads a `sku,qty` file and calls `receive()` for each row. Blank lines are skipped, and it returns how many rows it received. It checks every row before receiving any, so a bad file imports nothing. A bad row raises `ValueError` with a message starting `line N: `, for example `line 4: qty must be a positive integer, got 'x'`. N is the line number you'd see in a text editor, with blank lines counted.
- **Tests:** 5 new ones for `ship()` added to `tests/test_stock.py`, and 29 in the new `tests/test_import_csv.py`. The 4 existing tests are unchanged apart from the import line.

**How it was done:** one Haiku worker per task, one after the other because both edit `inventory/stock.py`, then an Opus verifier. The verifier also broke the code on purpose in 23 ways, and the tests caught 21 of them. No fix rounds were needed. Sub-agents used about 133k tokens against my estimate of about 400k; the fix round I'd allowed for didn't happen.

**Decisions I made (you can reverse any of them):**
- The file must start with a `sku,qty` header, in any letter case. A file without one, or with `qty,sku`, is rejected with a `line 1:` error.
- Rows that are empty, spaces only, or only commas count as blank and are skipped.
- A quantity must be a whole number above 0 written in plain digits. `+5`, `5_0`, `2.5`, `-3` and full-width digits are rejected. Python's `int()` alone would accept some of these.
- An empty file or a header-only file returns 0 rather than raising an error.
- Errors are plain `ValueError` rather than a new exception class.

**Small issues left open:**
- No test covers a quoted field that contains a line break, so how those lines are numbered could change later without a test failing. One test would cover it.
- A single field longer than 131,072 characters raises the `csv` module's own error instead of the `line N:` `ValueError`. Nothing is imported in that case either.
- There are some comments that just repeat the code, and a missing blank line after the imports.
- Already true before this change: `receive()` and `ship()` accept decimal quantities.
- The subject line of the first commit has the co-author lines stuck onto it. I left it rather than rewrite history.

To take it: `git merge orch/inventory-ship-csv`.

As you asked, I kept the working files in the git-ignored `.orchestrator/` folder:
- `plan.md` — rulings and log
- `notes.md`
- `task-1-report.md`
- `task-2-report.md`
- `verify-1-report.md`
- `diff-1.patch`
- `report.md`