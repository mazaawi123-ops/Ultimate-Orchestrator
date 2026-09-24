Due dates are added on a new branch, `orch/due-dates`. I checked 42 passing tests and the lint step myself, and a separate Opus verifier checked all 7 acceptance criteria and passed them. Nothing is pushed or merged into `main`.

**What it does now**
- `todo add "title" --due 2026-10-01` saves `"due": "2026-10-01"` on the item. Without `--due`, the item is saved exactly as before, with no `due` field.
- A bad date (`2026-13-01`, `2026-02-30`, `20261001`, `2026-1-01`, an empty string) exits with code 2 and prints `invalid due date '<value>': expected YYYY-MM-DD`. The JSON file isn't created or changed.
- `todo list` shows `[ ] #1 pay rent (due 2026-10-01)`. Items without a due date print exactly as before.
- `todo overdue` lists open items due before today, in the same format as `list`. An item due today doesn't count.
- Old files with no `due` field load and work with every command. Items saved before don't gain a `due` field. If someone hand-edits a bad date into the file, `overdue` skips that item instead of crashing.
- New tests are in `tests/test_due.py` and `tests/test_cli.py`, and the three old tests are unchanged. The verifier deliberately broke the code 13 ways; the tests caught 11. The other two changes made no difference to behaviour.

**What happened along the way:** before verification I found a problem the first worker hadn't reported. Its `overdue` accepted a compact date like `"20000101"` from a hand-edited file and counted it as overdue. I sent it back, and it's fixed, with a test that failed before the fix. No further fix rounds were needed.

**Decisions I made for you** (all listed in the report):
- Only the exact `YYYY-MM-DD` form is accepted, so `20261001` is rejected rather than converted.
- "Before today" uses your computer's local date.
- `add` still prints just `added #N: title`, without the due date.
- Items without a date have no `due` field at all rather than `"due": null`.

**Left open:** the verifier found four minor issues, and I didn't fix them. The only one worth knowing: if code calls the store directly with a non-text date (such as a Python `date` object), it gets a less helpful error. Nothing bad is saved. The CLI isn't affected.

**Cost:** 2 Haiku workers (one sent back once) and 1 Opus verifier, about 200k tokens in total. My estimate was about 400k, because I expected a fix round that turned out not to be needed.

To take it: `git merge orch/due-dates`.

Files are in `.orchestrator/` (kept, and git-ignored):
- `report.md`
- `plan.md`
- `notes.md`
- `verify-1-report.md`
- `task-1-report.md`
- `task-2-report.md`
- `diff-1.patch`