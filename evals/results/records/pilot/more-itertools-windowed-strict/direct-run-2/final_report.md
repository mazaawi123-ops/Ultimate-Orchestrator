## Done: `windowed()` now takes `strict`, and the full test suite passes

- **What changed:** `windowed(seq, n, fillvalue=None, step=1, *, strict=False)` in `more_itertools/more.py`. With `strict=True`, it yields every complete window and then raises `ValueError("not enough items to fill the final window")` at the point where it would otherwise pad a window with `fillvalue`. With `strict=False`, the code runs exactly as before. To spot padding, strict mode pads with a private marker object and checks the last item of each window. Padding only ever goes at the end of a window, so a real item that happens to equal `fillvalue` can't set off the error.
- **Docstring:** a new paragraph and doctest show two windows being yielded and then the `ValueError`.
- **Type stub:** `more.pyi` now accepts `strict: bool` as keyword-only in both `windowed` overloads.
- **Tests:** 8 new tests in `WindowedTests`. They cover:
  - inputs that line up exactly and ones that need padding, across `step` smaller than, equal to and larger than `n`;
  - input shorter than `n`, and empty input;
  - items equal to `fillvalue`;
  - windows arriving one at a time before the error, and `strict` being keyword-only;
  - an exhaustive comparison with `strict=False` for inputs up to 7 items, `n` 1–8 and `step` 1–9.
- **Results:** `python3 -m unittest -q` passes 938/938, up from 930 before the change. It also passes in a fresh checkout. No existing tests were changed. As a spot check I broke the new code on purpose three ways, and each time the new tests failed.

**Not verified:**
- **Type stub:** mypy isn't installed, so the stub change hasn't been type-checked.
- **Lint:** flake8 isn't installed either, so that run failed without checking anything. I checked the added lines for length by hand instead.
- I didn't install either tool, to avoid adding a dependency.

**Decisions I made (recorded in `.orchestrator/notes.md`):**
- `strict` is keyword-only.
- An empty input with `strict=True` yields nothing and doesn't raise, the same as `strict=False` and `zip(strict=True)` with empty inputs.
- If you pass `fillvalue` together with `strict=True`, it's accepted and simply never used, rather than raising an error.
- The stub doesn't narrow the element type when `strict=True`: it still says items may be `None` (or `fillvalue`'s type). A narrower version couldn't be checked without mypy.

The work is on branch `orch/windowed-strict` (commit `4708744`), made from `main` and not pushed; to take it, run `git merge orch/windowed-strict`. As you asked, I built and checked it myself with no helper agents and no independent review. The plan, decisions and test logs are kept in `.orchestrator/`.