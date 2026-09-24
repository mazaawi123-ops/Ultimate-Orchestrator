## Result: done

Due dates are in, and all 23 tests pass. An independent reviewer (the verifier) confirmed each requirement by running the CLI directly.

- **Built:**
  - `todo add "title" --due 2026-10-01` saves `"due": "2026-10-01"` on the item. Anything that isn't a real `YYYY-MM-DD` date is rejected with exit code 2 and nothing is written.
  - `todo list` shows `[ ] #1 pay rent (due 2026-10-01)` for items with a due date. Items without one print exactly as before.
  - `todo overdue` lists open items due before today, in the same format as `list`. Items due today, future items, done items and items without a date are left out.
  - Files from before this change still load and work. The `due` field is only written when you give one, so old items never gain it.
- **Acceptance criteria:** 7/7 verified. The verifier passed them on its first check and again after the fix round.
- **Tests:** `python3 -m pytest -q` → 23 passed (there were 3 before). **Lint:** `ruff check .` → clean; the worker also fixed the 4 lint errors that were already in `todo/cli.py`. **Clean-room:** n/a, since nothing calls an outside service.
- **Iterations:**
  - The first build passed, but the verifier found the tests too weak. Nothing tested `done` or `overdue` on an old-format file, and the old-file test would still pass if `overdue` always returned nothing.
  - One fix round added those tests and showed they fail when `overdue` is broken on purpose to return nothing. It also limited the date check to plain 0–9 digits and checked that a rejected date writes nothing.
  - A second check passed with no new problems.
- **Rulings I made:**
  - Only strict `YYYY-MM-DD` is accepted. `20261001` and week dates like `2026-W40-4` are rejected.
  - Items without a due date get no `due` key at all, rather than `"due": null`.
  - "Overdue" means strictly before your computer's local date, so something due today is not overdue.
  - `overdue` prints nothing when nothing is overdue, the same as `list`.
  - A hand-edited file with a missing, `null` or garbage due date doesn't crash `overdue`; it skips those items.
  - The README usage line now mentions `--due` and `overdue`.
- **Open items:** two small ones I chose not to fix:
  - `overdue` also accepts a hand-edited compact date like `20000101`, which the CLI itself never writes.
  - The `add` confirmation builds the `(due …)` text separately from `list`.

  Also, the first commit's message has its co-author lines squashed onto the title line. It's cosmetic, and you can fix it if you rewrite history before merging.
- **Not verified:** none.
- **Branch:** `orch/due-dates` from `main` at `fd2956b`, with commits `f5d9cfd` and `0e04ff5`. Not pushed. To take it: `git merge orch/due-dates`.
- **Mode:** Lite. It used a Haiku worker to build, an Opus verifier, a Sonnet worker for the fix, and a Sonnet re-check. My estimate beforehand was about $1.5–2.5.

As you asked, I kept the plan, notes, worker and verifier reports, and patches. They're in `.orchestrator/`, which git ignores; start with `plan.md` for the rulings and log, and `report.md` for this summary.