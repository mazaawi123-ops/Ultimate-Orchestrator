`click.Duration` works and is exported next to `click.DateTime`. It turns `90s`, `15m`, `2h`, `1d`, `1.5h` and `1h30m` into a `datetime.timedelta`. The full test suite passes (2309 passed, up from 2241), as do ruff and mypy. Nothing is committed.

- **Behaviour:** a plain number such as `90` or `1.5` means seconds. So does an `int` or `float` given as `default=`. A `timedelta` comes back as the same object.
- **Errors:** bad input gets click's usual error, exit code 2:
  `Error: Invalid value for '--timeout': 'soon' is not a valid duration. Use a number of seconds or units d, h, m, s, such as '1h30m'.`
  Values too large for a `timedelta` (like `999999999999d`) get their own message, `'…' is too large to be a duration.`, rather than a traceback.
- **Files:** the class is in `src/click/types.py` and the export in `src/click/__init__.py`. The tests are in a new file, `tests/test_types/test_Duration.py`, which follows the repo's one-file-per-type layout, plus one case in `tests/test_info_dict.py`. There's a CHANGES entry under 8.6.0 (no PR number, since there isn't one yet), and I also added `Duration` to `docs/parameter-types.md` and `docs/api.md`.

**Calls I made without you** (all recorded in the plan):
- **Units:** lowercase `d`, `h`, `m`, `s` only. No weeks, milliseconds or `M`, which could be misread as months.
- **Combinations:** each unit can appear once, largest first. So `30m1h` and `1h1h` are rejected as likely typos.
- **Spaces:** spaces around the value are ignored, but a space inside it (`1h 30m`) is rejected.
- **Numbers:** no signs, exponents, `inf`/`nan` or `_`, and `True`/`False` aren't accepted as numbers.

**How it was checked:** one subagent built it. A second, fresh subagent checked it against the plan and your requirements, including about 80 edge-case inputs run through a real command, and found nothing blocking. I then fixed the version marker (`8.6` → `8.6.0`, the repo's style) and added the few tests it said were missing.

One process note: the checker briefly used `git stash`/`git stash pop` to measure the starting test count, though I'd told it not to touch the repo. I confirmed the working tree is exactly as the builder left it.

Files are in the scratchpad:
- PLAN.md
- REPORT.md
- verify/adv.py