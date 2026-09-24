# Goal
Add keyword-only `strict=False` to `more_itertools.windowed`. With strict=True it never yields a window that would need fillvalue padding: on reaching such a window it raises ValueError (like zip(strict=True)); the complete windows before it are still yielded. strict=False behaviour unchanged. Update stub, docstring, tests.

# Baseline
- branch: orch/windowed-strict from main (clean tree)
- BASE: b5e3886a37209bb880f17d82fbf4ba00ece0e41e
- tests at BASE: python3 -m unittest -q → 930 OK; pre-existing failures: none
- lint at BASE: ruff format --check . ; ruff check more_itertools tests ; PYTHONPATH=. stubtest more_itertools.more more_itertools.recipes → all clean
- clean-room: n/a (no external services)
- estimate given: 1 Haiku worker + 1 Opus verifier, ~$2–3 total

# Acceptance criteria
- AC1: windowed(seq, n, fillvalue=None, step=1, *, strict=False); strict passed positionally → TypeError.
- AC2: strict=True, input yields only full windows → identical output to strict=False, no error. E.g. windowed([1,2,3,4,5],3,strict=True) → [(1,2,3),(2,3,4),(3,4,5)]; [] → [].
- AC3: strict=True, a window would need padding → the full windows before it are yielded, then ValueError is raised when the padded window would be produced (lazily, as a generator). Exact cases in review focus / brief table.
- AC4: detection is by position, not value: items equal to / identical to fillvalue (e.g. None) in the data never trigger the error.
- AC5: strict=False output unchanged (all existing WindowedTests pass untouched).
- AC6: more.pyi overloads accept `strict: bool = ...` keyword-only; stubtest clean; ruff format/check clean.
- AC7: docstring documents strict with a passing doctest; new unittest tests in WindowedTests cover AC1–AC4; full suite passes.

# Stop-and-ask items
- none

# Review focus
- first window short (len(seq) < n), with and without data; empty input
- step > n, step == n, step < n with trailing partial window; step past end (no window needed → no error)
- data containing None / the fillvalue itself, incl. last item equal to fillvalue
- laziness: complete windows reachable via next() before the raise; ValueError not raised early
- n/step validation unchanged; strict=False path byte-for-byte same outputs

# Constraints
- no new deps; existing tests unchanged.

# Rulings
- Ruling: strict is keyword-only — mirrors zip(strict=...) and avoids a 5th positional bool — cost if wrong: users can't pass it positionally (easy to relax later, hard to tighten).
- Ruling: empty input with strict=True yields nothing and does not raise — no window exists that would need padding (non-strict also yields nothing) — cost if wrong: callers expecting an error on empty input get none.
- Ruling: leftover items that no window would cover (step > n, e.g. [1..6], n=3, step=4... ) do not raise — strict only forbids yielding padded windows, which non-strict wouldn't yield there either — cost if wrong: silent skip of trailing items that step>n already skips by design.
- Ruling: error message `windowed(): not enough items to fill a window` — cost if wrong: cosmetic.
- Ruling: stub just adds `strict: bool = ...` keyword-only to both existing overloads (no Literal[True] overload narrowing away `| None`) — matches repo convention (chunked/sliced strict not narrowed) and keeps stubtest simple — cost if wrong: strict=True users still see `_T | None` element types.
- Ruling: detect padding with the `_marker` sentinel as internal padding in strict mode, checking `window[-1] is _marker` (padding is only ever appended at the end) — position-based, O(1) per window.

# Tasks
## T1 windowed strict — tier: haiku — sequential — AC: AC1–AC7
- Worktree: main tree
- Files: more_itertools/more.py, more_itertools/more.pyi, tests/test_more.py
- Depends on: none
- Interfaces: Produces windowed(seq, n, fillvalue=None, step=1, *, strict=False)
- Tests allowed to change: none (add new tests only)
- Status: pending

# Log
- T1 DONE (612b60f), 945 passed, lint clean
- verify 1 (orch-verifier, opus): PASS 7/7; differential vs BASE 69,300 cases, 0 fails; nit: test_strict_false_default duplicates test_strict_false_explicit (left for user); _marker-in-data false positive declined (private sentinel)
