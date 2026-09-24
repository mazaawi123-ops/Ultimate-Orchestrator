# Goal
Add `humanize.parse_size(text) -> int`, the inverse of `naturalsize`: accepts every string naturalsize can produce (decimal kB..QB, binary KiB..QiB, GNU K..Q and "B", "Byte"/"Bytes"), returns bytes as int, raises ValueError on anything unparseable; exported from the package. Add `conjunction="and"` to `natural_list` so it can produce "a, b or c". Tests for both; existing suite stays green.

# Baseline
- branch: orch/parse-size-conjunction, from main (clean tree)
- BASE: 392aef707c0e74341ab4a51420984e9ea6b566c5
- tests at BASE: `python3 -m pytest -q --benchmark-disable` → 744 passed, 112 skipped; pre-existing failures: none
- doctests at BASE: `python3 -m pytest -q --benchmark-disable --doctest-modules -p no:cacheprovider src/humanize/filesize.py src/humanize/lists.py` → 2 passed
- lint at BASE: `ruff check --no-fix src tests && ruff format --check src tests` → clean; `mypy src` → clean
- clean-room: n/a (no external services)
- repo notes: .orchestrator/notes.md
- estimate: 1 Sonnet worker + 1 Opus verifier + Opus planner ≈ $2.5–3.5 (more if fix rounds)

# Acceptance criteria
- AC1: `from humanize import parse_size` works and "parse_size" is in `humanize.__all__`.
- AC2: exact examples: "1 Byte"→1, "0 Bytes"→0, "-1 Byte"→-1, "300B"→300, "1B"→1, "3.0 MB"→3000000, "1.0 kB"→1000, "2.9 KiB"→2970, "-4.0 KiB"→-4096, "2.9K"→2970, "1.0 QB"→10**30 exactly, "30000.0 QB"→3*10**34 exactly, "1.0 QiB"→1024**10 exactly, "1024"→1024, "  1.5 kB  "→1500, "1.5kB"→1500, "1.0 K"→1024, "0.5 KiB"→512, "1.0005 kB"→1001, "-1.0005 kB"→-1001, "+2 kB"→2000, ".5 kB"→500, "5. kB"→5000. Return type is exactly `int` (not bool/float/Decimal).
- AC3: ValueError for: "", "   ", "kB", "abc", "1.0 XB", "1 kB extra", "1..0 kB", "1.0 kb", "1.0 KB", "1.0 mb", "1.0 Kib", "inf kB", "nan", "1e3 kB", "1_000 kB", "١٢ kB" (Arabic-Indic digits), "1.5 Bytes", "1.5 B", "1.5", "- 1 kB", "1 k B". Non-str input (None, 1024, b"1 kB") raises TypeError.
- AC4: round trip: for every v in a sweep (0, ±1, ±999, 1000, 1023, 1024, 999999, 10**6, 2**20, 10**12, 2**50, 10**30, 3*10**34, 1024**10 and a range of other ints) and every mode (default, binary=True, gnu=True): `naturalsize(parse_size(naturalsize(v, b, g)), b, g) == naturalsize(v, b, g)`, and for bytes-only outputs (|v| < base) `parse_size(naturalsize(v,...)) == v`.
- AC5: `natural_list(items, conjunction="and")`: default output unchanged; `natural_list(["a","b","c"], conjunction="or")`→"a, b or c"; `natural_list(["a","b"], conjunction="or")`→"a or b"; `natural_list(["a"], conjunction="or")`→"a"; `natural_list([], conjunction="or")`→""; positional `natural_list(["a","b"], "or")`→"a or b"; `natural_list(["a","b","c"], conjunction="and/or")`→"a, b and/or c".
- AC6: full suite passes (744+ new, 0 failed), doctest command passes, ruff (--no-fix) + format check + mypy src clean. New tests exist in tests/test_filesize.py and tests/test_lists.py covering AC2–AC5; docstrings for both functions updated with Examples/Args/Returns/Raises.

# Stop-and-ask items
- none

# Review focus
- Float precision for huge units (must be exact integer math, not float).
- Rounding of fractional results, including negative values and exact halves.
- Unicode digits / whitespace / underscores / exponent / inf / nan slipping through Decimal() or float().
- Case sensitivity & the ambiguous "KB"; "Byte"/"Bytes"/"B" with fractions.
- Localized naturalsize output (activate("fr_FR") etc.).
- natural_list: generators consumed once; conjunction default unchanged.

# Constraints
- No new dependencies; stdlib only (decimal, re). Existing tests unchanged. Keep `__lazy_modules__` import pattern.

# Rulings
- Ruling: units are matched case-sensitively against exactly naturalsize's spellings (kB..QB, KiB..QiB, K..Q, B, Byte, Bytes); "KB"/"kb"/"mb" raise ValueError — "KB" is ambiguous (1000 vs 1024) and fail-loudly beats guessing — cost if wrong: users with lowercase input get an error; easy to relax later.
- Ruling: GNU single letters K..Q are base 1024 (as naturalsize gnu=True); decimal suffixes base 1000; binary base 1024.
- Ruling: result = Decimal(number) * base**exp, rounded to nearest int with ROUND_HALF_UP (halves away from zero, symmetric for negatives) — naturalsize output is lossy so rounding to nearest is the best inverse; exact Decimal/int math so "1.0 QB" == 10**30 — cost if wrong: off-by-one bytes on exact halves.
- Ruling: byte-level forms (Byte, Bytes, B, bare number) must be integral ("1.0 B" OK → 1; "1.5 Bytes" → ValueError) — fractional bytes are meaningless; fail loudly — cost if wrong: minor.
- Ruling: a bare number with no unit is accepted as bytes — unambiguous and handy — cost if wrong: minor leniency.
- Ruling: whitespace: strip leading/trailing; between number and unit zero or more spaces/tabs allowed; nothing between sign and digits; unit must be one token — naturalsize emits both "2.9K" and "2.9 KiB".
- Ruling: number grammar is ASCII only: optional +/-, digits with optional single '.' (".5" and "5." allowed); no exponent, underscores, thousands separators, inf/nan, non-ASCII digits — naturalsize's default format never emits them.
- Ruling: "Byte" and "Bytes" are interchangeable regardless of the count ("2 Byte" accepted).
- Ruling: parse_size parses the untranslated English forms only; translated output under an active locale raises ValueError — i18n parsing is out of scope; documented in the docstring — cost if wrong: a follow-up feature.
- Ruling: non-str input raises TypeError (like int(None)); ValueError is reserved for unparseable strings.
- Ruling: `conjunction` is a positional-or-keyword parameter used verbatim (" {conjunction} "), no validation, no Oxford comma, not translated (natural_list isn't translated today).
- Ruling: parse_size lives in filesize.py, reuses the `suffixes` dict rather than duplicating unit lists.

# Tasks
## T1 parse_size + natural_list conjunction — tier: sonnet — sequential — AC: AC1–AC6
- Worktree: main tree
- Files: src/humanize/filesize.py, src/humanize/__init__.py, src/humanize/lists.py, tests/test_filesize.py, tests/test_lists.py
- Depends on: none
- Interfaces:
  - Produces: `humanize.parse_size(text: str) -> int` (filesize.py, exported); `humanize.natural_list(items: Iterable[Any], conjunction: str = "and") -> str`
- Tests allowed to change: none (add new tests only)
- Status: pending

# Shared-surface check
Single task — n/a.

# Log
- understand/plan done; baseline green.
- T1 dispatched to orch-worker-sonnet
- T1 DONE (c0b23ad), 849 passed/112 skipped; lint-only deviations accepted (EM102 msg vars, PT011 match=). Note: _version.py is untracked/generated; format check scoped to tracked files
- iter 1 verify (orch-verifier): FAIL. B1 ctx.prec=200 → decimal.InvalidOperation (not ValueError) for >200-digit numbers incl. naturalsize(10**250) output; double rounding past 200 digits. B2 regex `(?P<unit>\S*)$` O(n²) backtracking (100k chars → 48–147 s). Nits: docstring overclaims (custom format / localized → ValueError), strip() removes unicode ws at ends, README silent, no huge/hostile tests.
  Root cause: brief didn't name "huge values naturalsize can emit (up to ~1.8e308)" or "adversarial-length input" as cases.
  Rulings: B1, B2 → fix round 1 (sonnet). Docstring nit → fix. strip() nit → accept (nothing mis-parsed). README nit → open item (not requested).
- fix 1 (B1,B2,docstring; round 1, sonnet): 4de7e61, 866 passed/112 skipped; prec=len(number_str)+40, unit [A-Za-z]*
- recheck 1 (orch-rechecker): PASS — B1, B2, docstring ADDRESSED; AC2/3/4/6 hold; 866 passed/112 skipped. Non-blocking: ReDoS test uses wall-clock <1s (observed ~5ms).
