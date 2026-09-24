## Result: done

`windowed()` now has a keyword-only `strict=False` argument. With `strict=True` it yields each complete window, then raises `ValueError('not enough items in seq to fill the window')` when it reaches a window that would need padding. With `strict=False` nothing changed. The full suite passes: 947 tests, up from 930.

- **Built:** the change is in `more_itertools/more.py`, the two type-stub overloads in `more_itertools/more.pyi`, and new tests in `WindowedTests`. The docstring has a new paragraph and a doctest that shows two complete windows coming out before the error.
- **Acceptance criteria:** 4/4 verified.
  - The independent verifier compared `strict=True` against `strict=False` over 14,175 input combinations and found no mismatches.
  - It also confirmed `strict=False` behaves exactly as before over 5,280 cases, including how many items are read from the input.
  - It checked the stub with mypy: passing `strict` positionally, or as a non-bool, is rejected.
  - A second, narrower check after the fix confirmed the fix broke nothing.
- **Tests:** `python3 -m unittest -q` → 947 passed, doctests included. **Lint:** `ruff format --check`, `ruff check` and `stubtest` all clean. **Clean-room:** not applicable, since nothing calls an external service.
- **Iterations:** the first version passed every criterion, but the verifier found that `strict=True` held `step` items in memory at once. With `step=5_000_000` that peaked at 368 MB, where `strict=False` stays near zero. A fix round brought it down to the same small, fixed memory use as `strict=False`. I added a test that fails on the old code and passes on the new.
- **Decisions I made:**
  - `strict` can only be passed by keyword, like `zip(strict=)`.
  - An empty input yields nothing and doesn't raise, because no window is padded.
  - When `step > n`, leftover items that fall in the gap before the next window would start are dropped without an error, e.g. `windowed([1..8], 3, step=4, strict=True)` gives `(1,2,3)`, `(5,6,7)`. `strict=False` never yields a padded window there either, and `windowed` already skips gap items in the middle of the input. The verifier questioned this, since `zip(strict=True)` exists to catch dropped data, but agreed it's defensible, so I kept it.
  - The error is a plain `ValueError` with the message above.
  - The value of `strict` isn't type-checked at runtime, as with `zip`.
  - I didn't add a changelog entry to `docs/versions.rst`; those are written at release time.
- **Open items (minor, not fixed):**
  - With `step=1`, `strict=True` runs about 2.2× slower than `strict=False`.
  - The stub still says windows may contain the fill value when `strict=True`. Extra `Literal[True]` overloads could narrow that.
- **Not verified:** none.
- **Branch:** `orch/windowed-strict`, from `b5e3886`, with commits `039c7cd` and `ed58b95`. Not pushed. To take it: `git merge orch/windowed-strict`.
- **Mode:** Lite. Two Sonnet workers (build and fix), one Opus verifier and one Sonnet re-check, with me planning on Opus. I estimated about $2.5–3; the run came to about $2.5.

As you asked, I kept `.orchestrator/`: `plan.md` has the plan, decisions and log, alongside `notes.md`, `report.md`, the worker reports and the diff files.