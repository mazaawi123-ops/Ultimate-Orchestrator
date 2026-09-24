## Result: done
Shipping more than the stock level now raises `InsufficientStock`, and `Inventory.import_csv(path)` is in. The full test suite passes: 39 tests, including the 4 original ones, unchanged.

- **Built:**
  - `ship()` checks stock before changing anything and raises `InsufficientStock("cannot ship 5 of 'A': only 3 in stock")`. Shipping a SKU the inventory has never seen raises too, and doesn't add that SKU at zero stock.
  - `import_csv(path)` reads a file with a `sku,qty` header, skips blank lines, and handles Windows line endings and the byte-order mark Excel adds. It returns the number of rows imported.
  - A bad row raises the new `CsvImportError`, a subclass of `ValueError`, with messages like `line 4: qty must be a whole number, got 'x'`. The error also carries the line number as `.line`.
  - The whole file is checked before anything is added, so a bad row leaves the inventory exactly as it was.
- **Acceptance criteria:** 5/5 verified by an independent Opus verifier, then re-checked by a Sonnet verifier after the fix round.
- **Tests:** `python -m pytest -q` → 39 passed. Lint: `ruff check .` → clean. Clean-room: not applicable (nothing calls an external service).
- **Iterations:** the first build passed its tests, but the verifier found two gaps:
  - Badly quoted CSV was imported without complaint: `C,"3` with no closing quote imported C=3.
  - Quantities like `"1_000"` and non-ASCII digits were accepted.

  One Sonnet fix round made quoting strict, limited quantities to an optional sign plus plain digits, and added 6 tests that failed before the fix. The re-check passed.
- **Rulings I made:**
  - A header row is required. Its columns can be in either order, and case and surrounding spaces don't matter.
  - If any row is bad, nothing is imported.
  - A row that is only commas or whitespace counts as blank and is skipped.
  - Error line numbers are the actual line in the file where the row starts, counting the header and blank lines.
  - `import_csv` returns the row count; an empty or header-only file returns 0.
  - A missing file raises the normal `FileNotFoundError`.
  - Quantities must be a whole number with an optional sign, so `+3` is accepted.
  - Quoting is strict, so `"A" ,5` (a space after the closing quote) is now rejected, with its line number.
- **Open items:** two minor issues, left unfixed:
  - A file that isn't UTF-8 raises `UnicodeDecodeError` with no line number. It is still a `ValueError`, and the inventory is unchanged.
  - A very long qty value is repeated in full in the error message.
- **Not verified:** none.
- **Branch:** `orch/inventory-fix-csv` from `main` at 167b0db, 2 commits. Not pushed. To take it: `git merge orch/inventory-fix-csv`.
- **Mode:** Lite. Agents: one Haiku worker, one Sonnet fix worker, one Opus verifier and one Sonnet re-check, with me planning on Opus. I estimated about $0.8–2.5.

As you asked, I kept the plan, notes, worker reports, verifier reports and final report in `.orchestrator/`. That folder is not tracked by git, so the files stay on disk but aren't in the commits.

Files are in `.orchestrator/`:
- plan.md
- notes.md
- report.md
- task-1-report.md
- fix-1-report.md
- verify-1.md
- verify-2.md