## Done: `windowed()` now takes `strict=False`, and with `strict=True` it raises `ValueError` instead of yielding a padded window

- **What changed:**
  - `more_itertools/more.py`: `windowed(seq, n, fillvalue=None, step=1, *, strict=False)`. With `strict=True` it still yields every complete window. When it reaches a window that would need padding, it raises `ValueError("windowed(): iterable too short to fill the final window")`, the way `zip(strict=True)` does. The code with `strict=False` produces the same output as before.
  - Other files: the docstring has a new paragraph and a doctest, the type stub (`more.pyi`) accepts `strict`, there are 10 new tests in `tests/test_more.py`, and `docs/versions.rst` has a line under "Unreleased".
- **Checks: all 8 acceptance criteria met** on the final commit, c9247b2.
  - `python3 -m unittest -q`: all 940 tests pass (930 before, plus the 10 new ones).
  - `ruff` formatting and lint checks are clean.
  - `stubtest` finds no problems in the type stubs, and mypy infers the expected types for sample calls.
  - Logs are in `.orchestrator/logs/`.
- **Tests that failed before the change:** none.
- **Existing tests edited:** none. The new tests are additions only.
- **Review:** the independent reviewer passed it with no findings.
  - It compared `strict=True` against the normal output in 14,784 cases and found no mismatches.
  - It compared the new code without `strict` against the original over 3,960 inputs and found no differences.
  - It made 5 deliberately broken versions of the code, and the new tests caught all 5.
  - Test coverage of `more.py` is 100%.
- **Not verified:**
  - The Sphinx docs build, because Sphinx isn't installed here. The risk is low, because the new doctest is laid out like the 11 already in the file.
  - Python versions other than 3.11.

**Decisions I made without asking** (all recorded in `.orchestrator/record.md`):
- **Keyword-only:** `strict` can't be passed positionally, as with `zip`, so a stray `True` after `step` can't turn it on by accident.
- **Empty input:** it yields nothing and does not raise, because there is no window to pad.
- **Large steps:** when `step > n`, leftover items that the step jumps over entirely don't raise. For example, `windowed(range(7), 3, step=7, strict=True)` just yields `(0, 1, 2)`. No window starts on those items, and the normal mode yields nothing for them either.
- **Items equal to `fillvalue`:** real items that happen to equal `fillvalue` (or `None`) don't trigger the error. The code marks padding with a private placeholder rather than comparing values.
- **Types:** with `strict=True`, the stub gives windows the type `tuple[T, ...]`, without `fillvalue`'s type mixed in, because padding can never appear.

**Branch:** `orch/windowed-strict`, created from `main` at b5e3886. It is not pushed. To take it: `git merge orch/windowed-strict`.

**How it ran:** Reviewed mode. I built it myself and one reviewer checked it (Opus, extra-high effort). No repairs were needed, and the local estimate is about $1.50. The run record is in `.orchestrator/` (`record.md`, `request.md`, `summary.md`, `logs/`), and the mypy sample calls are in my scratchpad as `typecheck_windowed.py`.