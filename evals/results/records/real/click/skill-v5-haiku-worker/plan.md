# Goal
Add a `click.Duration` parameter type (exported like `click.DateTime`) that converts duration
strings (`90s`, `15m`, `2h`, `1d`, `1.5h`, `1h30m`, plain number = seconds) into
`datetime.timedelta`, passes `timedelta` values through unchanged, and fails every other input
with click's usual "Invalid value" error naming the bad input. With tests, docs listing and a
CHANGES entry. Done = suite + lint green and an independent verifier finds no blockers.

# Baseline
- branch: orch/duration-type, from main (uncommitted work: none)
- BASE: 06b2a678741131fd577ce170e23e5ca0aeba0309
- tests at BASE: `python3 -m pytest -q` → 2241 passed, 24 skipped, 1 xfailed; pre-existing failures: none
- lint at BASE: `ruff check src tests && ruff format --check src tests && mypy src` → clean; pyright types.py 0 errors / 1 warning
- clean-room test command: n/a: no external services
- repo notes: .orchestrator/notes.md
- estimate given to the user: ~$2–3 (Opus planner, 1 Haiku worker, 1 Opus verifier, fix round if needed)

# Acceptance criteria
- AC1: `click.Duration` is importable from `click` (`from click import Duration`), is a `ParamType` subclass with `name == "duration"` and `repr(click.Duration()) == "Duration"`.
- AC2: `click.Duration().convert(v, None, None)` returns the timedelta in the conversion table (Rulings / brief) for every valid example: 90s, 15m, 2h, 1d, 1.5h, 1h30m, 1d2h3m4s, plain "90"/"1.5"/"0", surrounding whitespace, int/float seconds.
- AC3: a `timedelta` input is returned unchanged (same object, `is`), including negative and zero timedeltas.
- AC4: every invalid example in the table raises `click.BadParameter` (never ValueError/OverflowError/TypeError); through a command (`CliRunner`) the output contains `Invalid value for '--timeout'` and the repr of the bad input, exit code 2.
- AC5: `click.Duration().to_info_dict() == {"param_type": "Duration", "name": "duration"}` (case added to tests/test_info_dict.py).
- AC6: CHANGES.md has an entry under Version 8.6.0; Duration is listed in docs/api.md and docs/parameter-types.md next to DateTime.
- AC7: `python3 -m pytest -q` passes with new tests in tests/test_types/test_Duration.py; `ruff check src tests && ruff format --check src tests && mypy src` clean; pyright on types.py no new errors.

# Stop-and-ask items
- none

# Review focus
- Unicode digits (`"١h"`, `"²s"`) must fail — `\d` / `str.isdigit` / `float()` accept some of them.
- `float()`-isms that must not sneak in: `"1e3"`, `"inf"`, `"nan"`, `"1_000"`, `"+5"`, `"-5"`, `" 1 "` inside combos.
- Overflow: `"999999999999d"`, `"9"*400`, huge int → BadParameter, not OverflowError.
- bool is an int subclass: `True` must fail, not become 1 second.
- nan/inf floats as python values; negative numbers.
- Unit order / repetition: `"30m1h"`, `"1h1h"`; empty string; unit with no number (`"h"`); `"1.h"`, `".5h"`, `"1.5.2h"`.
- Float precision of fractional units (`"1.1h"`, `"0.000001s"`), microsecond rounding.
- Error path through a real command (default values converted too: `default=90`, `default="2h"`).

# Constraints
- No new dependencies; don't import `math` (tests/test_imports.py allow-list).
- Existing tests untouched except adding one case to the parametrize list in tests/test_info_dict.py.

# Rulings
- Ruling: units are `d`, `h`, `m`, `s` only, lowercase, case-sensitive; no `w`, `ms`, `us` — the request lists exactly these; `M` vs `m` is ambiguous — cost if wrong: `2H`/`1w` users get a clear error and we add units later.
- Ruling: combinations must use each unit at most once, in descending order d→h→m→s, with no internal whitespace (`1h30m` ok; `30m1h`, `1h1h`, `1h 30m` fail) — keeps one unambiguous grammar; fail loudly — cost if wrong: slightly stricter than some users expect.
- Ruling: number syntax is ASCII `[0-9]+(\.[0-9]+)?` for every component and for plain seconds; decimals allowed on any component (`1.5h30m` = 2h). `.5h`, `1.h`, `1e3`, `inf`, `nan`, `1_000`, signs, unicode digits fail — avoid float() leniency — cost if wrong: users must write `0.5h`.
- Ruling: negative durations are rejected for string and number input (`-5`, `-1h`, `-1`) — "duration" is non-negative and the request lists no sign — cost if wrong: negative offsets need a custom type. A negative *timedelta* still passes through unchanged (request says timedelta passes through unchanged).
- Ruling: surrounding whitespace is stripped (`" 2h "` ok) — matches click's INT/FLOAT which accept it via int()/float() — cost if wrong: negligible.
- Ruling: Python int/float values (not bool) are seconds, so `default=90` works; bool, None, bytes, lists etc. fail with BadParameter — "a plain number means seconds" covers non-string numbers; anything else fails loudly — cost if wrong: a caller passing a raw int gets seconds instead of an error.
- Ruling: conversion is `timedelta(days=, hours=, minutes=, seconds=)` with float components (timedelta rounds to microseconds); OverflowError and ValueError from it become BadParameter — cost if wrong: none.
- Ruling: error message `"{value!r} is not a valid duration. Use a number of seconds or a combination of days, hours, minutes and seconds, such as '90s', '1.5h' or '1h30m'."` via gettext — names the bad input as required.
- Ruling: no `get_metavar` override (metavar is `DURATION`); `to_info_dict` inherited unchanged.

# Tasks
## T1 Duration type + tests + docs + CHANGES — tier: haiku — mode: sequential — AC: AC1–AC7
- Worktree: main tree
- Files: src/click/types.py, src/click/__init__.py, tests/test_types/test_Duration.py (new), tests/test_info_dict.py (add one case), docs/api.md, docs/parameter-types.md, CHANGES.md
- Depends on: none
- Interfaces:
  - Consumes: `ParamType`, `self.fail`, `_` (gettext) in src/click/types.py
  - Produces: `class Duration(ParamType[timedelta])` in src/click/types.py; `from .types import Duration as Duration` in src/click/__init__.py
- Tests allowed to change: tests/test_info_dict.py — add one parametrize case only (no existing case edited)
- Status: pending

# Shared-surface check
| Tasks | Shared file / interface | Resolution |
|---|---|---|
| (single task) | — | — |

# Log
- T1 DONE (3bf5deb, haiku), 2304 passed, lint clean
- verify 1 (opus): PASS all AC7/7. Nits: message duplicated x5 (brief asked for one place — worker deviation unreported), docstring wrong about negative timedelta, versionadded 8.6 vs 8.x.0 style, test_Duration uses click.testing without import. Ruling challenged: "0.0000005s" silently → timedelta(0).
- Ruling (revised): a nonzero string/number input that rounds to timedelta(0) fails with the usual message — a positive duration silently becoming 0 ("no timeout" in many apps) is silent coercion — cost if wrong: sub-microsecond inputs error instead of becoming 0.
- fix 1 (round 1, sonnet): all nits + revised ruling, in one brief.
- fix 1 DONE (b169e4a, sonnet), 2314 passed, lint clean; accepted deviation: CliRunner call sites use imported name
- recheck 1 (sonnet): PASS, findings 1-4 ADDRESSED, no new breakage. Done.
