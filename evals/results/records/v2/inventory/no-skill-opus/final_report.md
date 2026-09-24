Both changes are in and all 40 tests pass (there were 4 before). I haven't committed anything because you didn't ask me to, so it's all uncommitted in the working tree.

**The bug fix:** `ship()` now raises `InsufficientStock` when you ask for more than is in stock, and the stock level is left as it was. The error names the SKU, how many were asked for and how many are available. Shipping exactly what's in stock still works and leaves 0, and shipping an SKU that has never been received raises the error. There are 3 new tests in `tests/test_stock.py`.

**The CSV import:** `inv.import_csv(path)` calls `receive()` for each row and returns how many rows it imported.
- Blank lines are skipped, including lines that are only spaces or only a comma.
- A bad row raises a new `CSVImportError` that names the line, e.g. `line 4: qty must be a positive integer, got 'abc'`. Line numbers are the actual lines in the file, so blank lines count.
- A bad row is a wrong number of columns, an empty SKU, or a qty that isn't a positive whole number.
- Its tests are in the new `tests/test_import_csv.py`.

**How it was run:**
1. I wrote a plan first, including the decisions below.
2. Two workers ran in parallel, one per feature, each limited to its own part of the code.
3. An independent verifier reviewed the code and tried a lot of awkward inputs (odd line endings, quoted fields, very long values, bad rows after blank lines). Its first verdict was pass with minor issues.
4. I fixed those: some unusual inputs slipped through without a line number, a few checks had no tests, and some code was hard to read.
5. The verifier re-checked and passed it. It also deliberately broke the code in 9 ways, and the tests caught every one. I then fixed one last small issue it raised: a very long bad value was repeated in full in the error message, so it's now cut to 20 characters.

**Decisions I made because no one was available to ask:**
- **Header row:** `sku,qty` is optional and is only recognised as the first non-blank line.
- **All or nothing:** the whole file is checked before anything is received, so a bad row on line 900 doesn't leave lines 1–899 already added to stock.
- **Error type:** `CSVImportError` is a kind of `ValueError`, so existing `except ValueError` code still catches it.
- **Strict quantities:** plain digits only, so `3.5`, `+3`, `0` and non-English digits like `３` are rejected, while `007` is read as 7.
- **Byte-order mark:** a CSV saved from Excel with a byte-order mark at the start imports normally.

**Two things I left alone on purpose:**
- A file that isn't valid UTF-8 raises Python's normal decoding error without a line number, because the line can't be worked out reliably.
- SKUs aren't checked for control characters, since that wasn't asked for.

The plan, the verifier's findings and the final report are kept in `.orchestrator/` (the repo already ignores that folder in git):
- `plan.md`
- `verification.md`
- `report.md`