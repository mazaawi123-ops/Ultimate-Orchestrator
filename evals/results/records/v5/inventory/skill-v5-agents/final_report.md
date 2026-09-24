## Result: done

Shipping more than the stock level now raises `InsufficientStock`, and `Inventory.import_csv(path)` is added with tests for both. The full suite passes (47 tests), lint is clean, and an independent verifier checked the finished code.

- **Built:**
  - **`ship()`:** raises `InsufficientStock` when asked for more than is in stock, with a message like `cannot ship 6 of 'A': only 5 in stock`. The stock level stays unchanged. Shipping exactly the stock level works and leaves 0. Shipping a SKU that was never received also raises the error.
  - **`import_csv(path)`:**
    - Requires a `sku,qty` header, skips blank lines, and calls `receive()` for each row.
    - Returns the number of rows it received.
    - A bad row raises `CsvImportError`, a subclass of `ValueError`, with a message like `path: line 3: qty must be a positive integer, got 'abc'`. The line number is also on `.line`.
    - It checks every row before receiving any, so a bad file changes nothing.
- **Acceptance criteria:** 4/4 verified.
- **Tests:** `python -m pytest -q` → 47 passed (4 existed before). **Lint:** `ruff check .` → clean. **Clean-room:** not needed, since nothing calls an external service.
- **Iterations:** the first build passed its tests, but the verifier failed it on two gaps:
  - A malformed quote in a large file crashed with a raw `csv.Error` that had no line number.
  - A quoted newline inside a SKU silently merged two rows into one.

  It also listed some missing tests. One fix round closed all of these, and a scoped re-check passed with no new breakage.
- **Rulings I made:**
  - **Header:** required. Upper or lower case is accepted, but the columns must be exactly `sku,qty` in that order.
  - **Rows with only commas:** `,` is treated as a bad row, not a blank line, so no data is dropped silently.
  - **Whitespace:** trimmed from the SKU and the quantity.
  - **Quantity:** must be plain digits and greater than 0. `2.5`, `-1`, `+5` and `1_000` are rejected.
  - **Control characters in a SKU:** rejected, including newlines and tabs.
  - **Encoding:** files must be UTF-8. A leading byte-order mark (which Excel adds) is accepted; any other encoding raises `UnicodeDecodeError`.
  - **Empty or missing files:** an empty file is an error ("missing header"). A file with only the header returns 0. A missing file raises the normal `FileNotFoundError`.

  The verifier also questioned whether trimming whitespace from SKUs was right. I kept it, because spaces around CSV fields are usually just formatting, and documented it in the docstring.
- **Open items:** none. `receive()` and `ship()` called directly still accept any SKU string; only the import checks for control characters.
- **Not verified:** none.
- **Branch:** `orch/inventory-fix-csv`, from `main` at `167b0db`, with 2 commits. Not pushed. To take it: `git merge orch/inventory-fix-csv`.
- **Mode:** one Haiku worker built it and one Sonnet worker did the fix round. Opus verified the build and Sonnet re-checked the fix, with Opus planning. I estimated about $2.5–3 before the fix round, which will have added to that.

As you asked, I kept the plan, notes and report files. They're in `.orchestrator/`, which git ignores, so they aren't part of the branch. The main ones are `.orchestrator/plan.md` (plan, rulings and log), `.orchestrator/notes.md` and `.orchestrator/report.md`.