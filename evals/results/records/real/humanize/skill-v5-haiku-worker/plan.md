# Goal
Add `humanize.parse_size(text) -> int`, the inverse of `naturalsize`: it accepts every string `naturalsize` can produce (decimal kB..QB, binary KiB..QiB, gnu K..Q and "B", "Byte"/"Bytes"), returns bytes as int, raises ValueError on anything else, and is exported from the package. Also give `natural_list` an optional `conjunction="and"` argument so it can produce "a, b or c". New tests for both; existing suite stays green.

# Baseline
- branch: orch/parse-size-conjunction, from main (uncommitted work: none)
- BASE: 392aef707c0e74341ab4a51420984e9ea6b566c5
- tests at BASE: `python3 -m pytest -q --benchmark-disable` → 744 passed, 112 skipped; pre-existing failures: none
- lint at BASE: `ruff check --no-fix src tests && mypy src` → clean (ruff config has fix=true, so --no-fix is required)
- clean-room test command: n/a: no external services
- repo notes: .orchestrator/notes.md
- estimate given to the user: ~$2.5–3 (Opus planner, 1 Haiku worker, Opus verifier; fix rounds extra)

# Acceptance criteria
- AC1: `from humanize import parse_size` works and "parse_size" is in `humanize.__all__`.
- AC2: parse_size returns the exact ints in the T1 example table (decimal, binary, gnu, Byte/Bytes, negatives, whitespace, float-trap values like "4.35 kB" → 4350, "1.0 QiB" → 1024**10).
- AC3: every input in the T1 error table raises ValueError (non-str included); message contains repr of the input.
- AC4: round-trip: for the naturalsize outputs of 0, 1, 300, 1000, 1024, 10**6, 5*1024**2, 10**30, 1024**10, -4096 in each mode (default, binary=True, gnu=True), parse_size(naturalsize(n, ...)) == n exactly when the 1-decimal mantissa is exact; and in general |parse_size(naturalsize(n)) - n| <= 0.05 * base**exp (mantissa rounding).
- AC5: natural_list(["a","b","c"], conjunction="or") == "a, b or c"; ["a","b"] → "a or b"; ["a"] → "a"; [] → ""; default unchanged ("a, b and c"); positional `natural_list(["a","b"], "or")` also works.
- AC6: full suite `python3 -m pytest -q --benchmark-disable` passes (≥ 744 passed + new, 0 failed) and `ruff check --no-fix src tests && mypy src` is clean; no pre-existing test lines removed or loosened.

# Stop-and-ask items
- none

# Review focus
- float imprecision ("4.35 kB", "1.1 MB", "2.930K"), huge units exceeding 28-digit Decimal precision (1024**10), rounding ties
- case variants ("KB", "kb", "kib"), unit without number, number without unit, trailing garbage, thousands separators, "inf"/"nan", unicode digits, empty/whitespace-only, non-str input
- scientific notation from custom `format` (e.g. "%e"), integer mantissa ("%.0f" → "3 MB"), explicit "+" sign
- gnu "B" vs decimal/binary units; "Byte" vs "Bytes" singular/plural mismatch
- natural_list with generators + conjunction, one item, empty

# Constraints
- No new dependencies (stdlib `re` and `fractions` only). naturalsize behaviour unchanged. natural_list default output unchanged.

# Rulings
- Ruling: compute bytes as `fractions.Fraction(number) * multiplier` then Python `round()` (nearest, ties to even) — exact arithmetic avoids float errors (4.35*1000=4349.999…) and Decimal's 28-digit precision (1024**10 has 31 digits); round, not truncate, because naturalsize rounds the mantissa — cost if wrong: off-by-one on ties only.
- Ruling: units are case-sensitive, exactly as naturalsize emits them ("kB" not "KB"/"kb"; "KiB"; "K") — "KB"/"Kb" are ambiguous (kilobyte vs kibibyte vs kilobit) and fail-loud is safer; easy to relax later — cost if wrong: users pasting "KB" get ValueError.
- Ruling: a bare number with no unit ("1024") raises ValueError — naturalsize never produces it and guessing bytes is a coercion — cost if wrong: one-line relaxation.
- Ruling: "B", "Byte" and "Bytes" all mean ×1 and singular/plural mismatch ("5 Byte", "1 Bytes") is accepted — no ambiguity, no data loss — cost if wrong: negligible.
- Ruling: whitespace between number and unit is optional for every style, leading/trailing whitespace is stripped ("1.0kB", "1.0 K", " 300B ") — naturalsize differs by style and custom formats may pad — cost if wrong: slightly lenient parsing.
- Ruling: number syntax is ASCII only: optional +/- sign, digits with optional fraction (`1`, `1.`, `.5`, `1.25`), optional exponent `e±N` with 1–3 digits (custom `format="%e"` produces it). No thousands separators, no inf/nan, no unicode digits — fail loud; exponent cap prevents pathological 10**huge computations — cost if wrong: exotic formats rejected.
- Ruling: parse_size only understands the untranslated English suffixes; output of naturalsize under an activated non-English locale may raise ValueError. Documented in the docstring — a locale-aware parser is a larger feature — cost if wrong: localized users can't round-trip.
- Ruling: non-str input raises ValueError (not TypeError) — the request says "raise ValueError for anything it can't parse" — cost if wrong: callers expecting TypeError.
- Ruling: every parse failure raises `ValueError(f"could not parse size: {text!r}")` — one message naming the input.
- Ruling: `conjunction` is used verbatim (no stripping/validation), no Oxford comma, and is a normal positional-or-keyword parameter after `items` — matches existing style — cost if wrong: none.

# Tasks
## T1 parse_size + natural_list conjunction — tier: haiku — mode: sequential — AC: AC1–AC6
- Worktree: main tree
- Files: src/humanize/filesize.py, src/humanize/__init__.py, src/humanize/lists.py, tests/test_filesize.py, tests/test_lists.py, README.md (add a parse_size example next to the naturalsize examples)
- Depends on: none
- Interfaces:
  - Produces: `humanize.filesize.parse_size(text: str) -> int`, re-exported as `humanize.parse_size`; `natural_list(items: Iterable[Any], conjunction: str = "and") -> str`
- Tests allowed to change: none (append new tests only)
- Status: pending

# Shared-surface check
| Tasks | Shared file / interface | Resolution |
|---|---|---|
| (single task) | — | — |

# Log
- T1 DONE (ce0fcb4, haiku), 852 passed/112 skipped
- iter 1 verify (opus): FAIL on AC3 — >4300-digit mantissa raises CPython int-limit ValueError with wrong message (Fraction() not wrapped). should-fix: top-level `from fractions import Fraction` breaks repo's lazy-import convention; round-trip test tautological / 5%-of-n tolerance (a 5%-off parser passes). nits: tests don't exercise humanize.parse_size/__all__; docstring doesn't say localized output raises; no mantissa-length cap (quadratic only with int-digit limit disabled).
- Ruling: fix blocker + both should-fixes + first two nits in one sonnet round; mantissa-length cap left as open item — with the default int-digit limit the try/except already bounds it — cost if wrong: slow parse only for callers who disable the limit.
- fix 1 (sonnet, 0b45ba7): 849 passed/112 skipped
- recheck 1 (sonnet): PASS — findings 1–5 ADDRESSED (mutant ×1.001 caught by new round-trip tests); 849 passed/112 skipped; 852→849 is consolidation of the ce0fcb4 round-trip ids. DONE.
