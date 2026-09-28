STATUS: DONE
Commits: 98321c5
Tests: `python3 -m unittest -q` → OK (936 tests). Module doctests pass (583 attempted, 0 failed). `mypy more_itertools/more.pyi` found no issues.
Material assumptions:
- `strict` is keyword-only (`windowed(seq, n, fillvalue=None, step=1, *, strict=False)`), and both stub overloads accept it.
- The error is `ValueError('windowed(): window would need padding')`.
- Empty input with `strict=True` yields nothing and does not raise, because no window needs padding.
- If the input runs out before the next step would start a window, that is not an error (for example n=3, step=7 over 7 items), because non-strict `windowed` yields no padded window there either.
Remaining problems: none. `strict=True` uses a plain Python loop, so it is a bit slower than the non-strict `islice`/`map` path. The non-strict code is unchanged.
Evidence: the full test log is in scratchpad/tests.log. The new `WindowedTests` include an exhaustive check (size 0–7, n 1–5, step 1–6): with `strict=True`, the windows yielded are exactly the non-strict windows that have no padding, and it raises only when a padded window would come next. There are also tests for an infinite iterator, `fillvalue`, empty input and invalid n.