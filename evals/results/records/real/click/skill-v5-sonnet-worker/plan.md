# Goal
Add a `click.Duration` parameter type (a class, used as `click.Duration()`, exported like
`click.DateTime`) that converts duration strings (`90s`, `15m`, `2h`, `1d`, `1.5h`, `1h30m`,
plain number = seconds) into `datetime.timedelta`, passes a `timedelta` through unchanged,
and fails with click's usual "Invalid value ..." error naming the bad input otherwise.
Plus tests and a CHANGES.md entry. Done = suite + lint green and the verifier agrees.

# Baseline
- branch: orch/duration-type, from main-line branch (uncommitted work: none)
- BASE: 06b2a678741131fd577ce170e23e5ca0aeba0309
- tests at BASE: `python3 -m pytest -q` → 2241 passed, 24 skipped, 1 xfailed; pre-existing failures: none
- lint at BASE: `ruff check src tests` clean; `ruff format --check src tests` clean; `mypy src` clean; `pyright src/click/types.py` 0 errors (1 pre-existing typing_extensions warning)
- clean-room test command: n/a: no external services
- repo notes: .orchestrator/notes.md
- estimate given to the user: Lite — 1 Sonnet worker + 1 Opus verifier, ~$2.5–3 total (planner ~60% of it)

# Acceptance criteria
- AC1: `import click; click.Duration` exists, is a `click.ParamType` subclass in src/click/types.py, exported from src/click/__init__.py as `from .types import Duration as Duration`; `repr(click.Duration())` == "Duration"; `click.Duration.name` == "duration".
- AC2: `click.Duration().convert(v, None, None)` returns:
  "90s"→timedelta(seconds=90); "15m"→timedelta(minutes=15); "2h"→timedelta(hours=2); "1d"→timedelta(days=1);
  "1.5h"→timedelta(hours=1, minutes=30); "1h30m"→timedelta(hours=1, minutes=30);
  "1d2h3m4s"→timedelta(days=1, hours=2, minutes=3, seconds=4); "0.5d"→timedelta(hours=12);
  "90"→timedelta(seconds=90); "1.5"→timedelta(seconds=1.5); "0"→timedelta(0); "0s"→timedelta(0);
  "  2h  "→timedelta(hours=2); 90 (int)→timedelta(seconds=90); 1.5 (float)→timedelta(seconds=1.5).
- AC3: a `timedelta` input is returned unchanged (`convert(td, None, None) is td`), including a negative one.
- AC4: each of these raises `click.BadParameter` whose message contains `repr(value)` and "is not a valid duration":
  "", "   ", "abc", "5x", "h", "1h30", "30m1h", "1h1h", "1 h", "1h 30m", "-5", "-1h", "+5", "1H", ".5h", "1.h", "1e3", "inf", "nan", "١٢" (Arabic-Indic digits), "99999999999d" (overflow), True, -5 (int), float("nan"), float("inf"), [] (list).
  No other exception type (OverflowError, ValueError, TypeError) escapes convert().
- AC5: on the CLI, `@click.option("--timeout", type=click.Duration())` invoked with `--timeout 5x` exits 2 and output contains `Invalid value for '--timeout': '5x' is not a valid duration.`; with `--timeout 1h30m` the callback receives timedelta(seconds=5400); a `default="15m"` converts to timedelta(minutes=15).
- AC6: CHANGES.md has a bullet under "## Version 8.6.0 / Unreleased" describing `Duration`; docs/api.md and docs/parameter-types.md list `Duration` next to `DateTime`.
- AC7: `python3 -m pytest -q` passes with new tests in tests/test_types/test_Duration.py covering AC1–AC5; `ruff check src tests`, `ruff format --check src tests`, `mypy src` clean; `pyright src/click/types.py` 0 errors.

# Stop-and-ask items
- none

# Review focus
- Overflow: huge values ("99999999999d", "1"*400 + "s", int 10**30) must fail via self.fail, not raise OverflowError.
- Unicode digits (`\d` in Python re matches them and float() accepts them) — must be rejected; ASCII only.
- Regex anchoring: `re.match` without `\Z`/fullmatch lets trailing junk or "\n" through ("2h\n" after strip is fine, but "2h\nx" must fail).
- bool is an int subclass — True must fail, not become 1 second.
- Float precision: "1.5h" must equal exactly timedelta(hours=1, minutes=30); float sums of components are fine at microsecond resolution but check.
- Components order/repetition; bare trailing number after units.
- Error path goes through `self.fail` so CLI shows "Invalid value for ...".
- Info dict / to_info_dict still works (default ParamType one).

# Constraints
- No new dependencies; stdlib only (re, datetime.timedelta, math).
- Existing tests unchanged.

# Rulings
- Ruling: units are exactly `d`, `h`, `m`, `s`, lowercase only; no `w`/`ms`/long names, `1H` fails — request lists only these; `M` could mean months — cost if wrong: users typing uppercase get a clear error.
- Ruling: combined units must appear at most once and in descending order d→h→m→s (`30m1h`, `1h1h` fail) — ambiguous input fails loudly — cost if wrong: minor inconvenience, easy to relax later.
- Ruling: each component and a plain number is `[0-9]+(\.[0-9]+)?` — ASCII digits, optional fraction with digits on both sides; no sign, no exponent, no `inf`/`nan`, no `.5`/`1.` — fail loudly rather than guess — cost if wrong: `.5h` users must type `0.5h`.
- Ruling: decimals allowed on any component (`1.5h30m` = 2h) — simplest consistent grammar — cost if wrong: none significant.
- Ruling: leading/trailing whitespace is stripped; internal whitespace (`1h 30m`, `1 h`) fails — keeps grammar strict — cost if wrong: users must remove spaces.
- Ruling: negative durations are rejected (strings with `-`, negative int/float); a negative `timedelta` passes through unchanged since the request says timedeltas pass unchanged — cost if wrong: can't express negative offsets via strings.
- Ruling: non-bool int/float values (e.g. from `default=90`) mean seconds; must be finite and ≥ 0; bool and any other type fail — "a plain number means seconds" — cost if wrong: none.
- Ruling: error message is `_("{value!r} is not a valid duration.")` so CLI reads `Invalid value for '--timeout': '5x' is not a valid duration.` — matches DateTime's `{value!r} ...` style — cost if wrong: wording tweak.
- Ruling: `Duration()` takes no constructor arguments, default metavar (DURATION), default info dict — minimal surface — cost if wrong: can add options later.
- Ruling: CHANGES entry has no {pr}/{issue} reference — none exists — cost if wrong: maintainer adds one.

# Tasks
## T1 Duration type, tests, docs, changelog — tier: sonnet — mode: sequential — AC: AC1–AC7
- Worktree: main tree
- Files: src/click/types.py, src/click/__init__.py, tests/test_types/test_Duration.py (new), CHANGES.md, docs/api.md, docs/parameter-types.md
- Depends on: none
- Interfaces:
  - Consumes: `ParamType[T]`, `self.fail(message, param, ctx)`, `_` (gettext) in src/click/types.py
  - Produces: `class Duration(ParamType[timedelta])` with `name = "duration"`, `convert(self, value: t.Any, param: Parameter | None, ctx: Context | None) -> timedelta`, `__repr__` → "Duration"; export `click.Duration`
- Tests allowed to change: none (adding a Duration row to tests/test_info_dict.py is allowed as an addition only)
- Status: pending

# Shared-surface check
| Tasks | Shared file / interface | Resolution |
|---|---|---|
| (single task) | — | — |

# Log
- Understand/plan done; Lite mode, 1 sonnet worker.
- T1 DONE_WITH_CONCERNS (98cf501): no math import (test_light_imports allow-list) — accepted as Ruling: finiteness via value>=0 + catching OverflowError/ValueError. 2292 passed.
- Ruling: don't import math in types.py — tests/test_imports.py allow-lists modules click imports — cost if wrong: none
- iter 1 verify (opus): FAIL. AC4 — int >= 2**1024 (10**400) leaks OverflowError from float(value) outside try (types.py:659-661), also via default=10**400 on CLI; root cause: brief listed 10**30 (overflows only in timedelta), not an int that overflows float(). should-fix: test gap. nits: versionadded 8.6 -> 8.6.0; float-sum precision loss beyond ~100 years (left as open item).
- fix 1 (round 1, sonnet): overflow fix + 10**400 test + versionadded 8.6.0
- fix 1 DONE (7351a72), 2293 passed
- recheck 1 (sonnet): PASS — all 3 findings ADDRESSED, no new breakage. Done.
