## Result: done

`click.Duration` is added and exported like `click.DateTime`, and the independent checks passed. The first check found one bug, which was fixed and re-checked.

- **Built:** `click.Duration()` turns `90s`, `15m`, `2h`, `1d`, `1.5h`, `1h30m` and `1d2h3m4s` into a `timedelta`. A plain number means seconds, whether it arrives as a string like `"90"` or as a number like `default=90`. A `timedelta` passes through unchanged. Anything else fails with click's usual error, for example `Invalid value for '--timeout': '5x' is not a valid duration.` The change also adds tests in `tests/test_types/test_Duration.py` plus one row in `tests/test_info_dict.py`, a CHANGES.md entry under 8.6.0, and entries in `docs/api.md` and `docs/parameter-types.md`.
- **Acceptance criteria:** 7 of 7 verified. An Opus verifier checked the build, and a Sonnet checker re-checked it after the fix.
- **Tests:** `python3 -m pytest -q` → 2293 passed, 24 skipped, 1 xfailed. **Lint:** `ruff check`, `ruff format --check` and `mypy src` are clean; `pyright` shows 0 errors and the one warning that was already there. **Clean-room:** not needed, since nothing calls an outside service.
- **Iterations:** The verifier found that a huge integer such as `10**400` crashed with `OverflowError` instead of click's error, because the conversion to float wasn't inside the error handling. My plan's overflow example (`10**30`) was too small to hit that path. One fix round moved the conversion inside the handling, added a `10**400` test (shown failing before the fix), and corrected the "versionadded" note to `8.6.0`. The re-check passed with nothing new broken.
- **Rulings I made:** The request didn't settle these, so I chose strict rules that fail loudly:
  - Units are lowercase `d`, `h`, `m` and `s` only, so `1H` fails.
  - Each unit can appear once, largest first: `30m1h` and `1h1h` fail.
  - Numbers use plain digits 0–9 with an optional decimal part, and decimals are allowed on any unit. Signs, exponents, `inf`/`nan`, `.5` and `1.` are rejected.
  - Spaces around the value are ignored, but spaces inside it fail (`1h 30m`).
  - Negative values fail, but a negative `timedelta` still passes through unchanged.
  - `True`/`False` are rejected rather than treated as 1 or 0 seconds.
  - The type takes no constructor arguments.
  - The CHANGES entry has no PR or issue number, since none exists.
  - The worker added one more: no `math` import, because a test (`tests/test_imports.py`) limits which modules click loads at import.
- **Open items:** Very long durations lose precision below a millisecond. For example, `365000d0.000001s` drops the final microsecond. Durations up to about 100 years were exact in the verifier's tests, so I left it.
- **Not verified:** I didn't build the Sphinx docs. The new entries follow the same format as the existing `DateTime` ones.
- **Branch:** `orch/duration-type` from BASE `06b2a67`, with commits `98cf501` and `7351a72`. Not pushed. To take it: `git merge orch/duration-type`
- **Mode:** Lite. I planned on Opus, one Sonnet worker built it plus one fix round, an Opus verifier checked it, and a Sonnet checker re-checked it. I estimated about $2.5–3.

As you asked, I kept the plan, notes and reports in `.orchestrator/`. The tooling git-ignores that folder, so the files aren't part of the commits.

Files are in `.orchestrator/`:
- plan.md
- notes.md
- report.md
- task-1-report.md
- fix-1-report.md