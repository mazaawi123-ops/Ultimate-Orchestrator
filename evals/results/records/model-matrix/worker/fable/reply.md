STATUS: DONE
Commits: 8ffe81f (branch orch-wt/windowed-strict) — more_itertools/more.py, more_itertools/more.pyi, tests/test_more.py
Tests: `python3 -m unittest -q` → Ran 935 tests, OK (includes the doctests; the two new docstring examples pass). `tests.test_more.WindowedTests` → 12 tests OK (5 new).
Material assumptions:
- `strict` is keyword-only (`def windowed(seq, n, fillvalue=None, step=1, *, strict=False)`), matching the brief's "keyword argument"; positional `windowed(seq, n, fill, step)` calls are untouched.
- Error message is `'iterable ended before the window was complete'` (the brief didn't specify wording; the doctest pins it).
- Strict detection uses the existing `_marker` sentinel as padding instead of `fillvalue`, with an O(1) `window[-1] is _marker` check (padding always follows all real items, so once any padding is in the window its newest item is padding). Non-strict path is byte-for-byte the old logic apart from the `pad` variable.
- Stub: `strict: bool = ...` added to both overloads; in the with-fillvalue overload it's after `*` so `step` stays positional as before.
Remaining problems: none. Not done (out of brief scope): no docs/versions.rst changelog entry. `black` isn't installed here, so formatting was checked by hand against the 79-column limit (no added line exceeds it).
Evidence: full run log at <workspace>/unittest.log; new tests cover: complete-only cases across steps, raise-after-partial-yield for n>len, n==step, off-by-one/two, and one-short cases, explicit strict=False padding, empty input, and laziness on `count()`.