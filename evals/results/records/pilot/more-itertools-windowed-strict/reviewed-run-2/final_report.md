## Done: `windowed()` now takes `strict=False`; with `strict=True` it raises instead of yielding a padded window

With `strict=True`, `windowed` yields every complete window, then raises `ValueError('not enough items to fill the final window')` when it reaches a window that would need padding. Like `zip(strict=True)`, it's lazy: the error comes at the point where the padded window would have been yielded. With `strict=False` or no `strict`, output and speed are unchanged from before. All tests, lint, the stub check and both reviews pass. One problem: the reviewer installed mypy into the system Python, outside the repo (details at the end).

- **Built:** the change is in `more_itertools/more.py`, with its own loop for the strict case. The type stub `more.pyi` has a new overload, so `strict=True` returns plain `tuple[_T, ...]` with no fill type. The docstring gains a paragraph and a doctest, and 7 tests are added to `WindowedTests`.
- **Criteria:** 7 of 7 met, on the final commit `60bf412`:
  - `python3 -m unittest -q`: 937 passed, 0 failed (930 before).
  - `ruff format --check` and `ruff check` are clean.
  - `stubtest` finds no issues.
  - A 1,920-case comparison against the original code matches exactly: output is identical without `strict`, and with it you get the same complete windows followed by the error. The logs are in `.orchestrator/logs/`.
- **Known failures:** none.
- **Test changes:** none; the existing tests are untouched.
- **Review:**
  - The independent review passed with no blocking findings. Its one observation was that the default path had become about 4% slower because of an extra check on every loop step.
  - I fixed that with one repair, giving the non-strict path its original loop back. Timing now matches the original (20.5 ms both), and a second review confirmed the fix.
  - **Install outside the repo:** during that second review, the reviewer ran `pip install mypy`, which put mypy 2.3.1 and its dependencies into the system Python at `/usr/local/lib/python3.11/dist-packages`. I didn't authorize that. It doesn't affect any results, because the tests don't use mypy. I didn't uninstall it because I can't tell which of those dependencies were already there. To remove it: `python3 -m pip uninstall mypy`.
- **Not verified:**
  - Only Python 3.11 was run.
  - I checked the type stub with mypy only, not pyright.
  - `stubtest` only works here with `PYTHONPATH=.`, because the tool runs in its own environment.
- **Decisions:**
  - `strict` is keyword-only, as in `zip`.
  - An empty input with `strict=True` yields nothing and doesn't raise, because there's no window to pad.
  - `fillvalue` is still accepted with `strict=True`; it's just never used.
  - Padding is found with a private marker object rather than by comparing values, so items equal to `fillvalue` (such as `None`) don't cause false errors.
  - Checks on `n` and `step` still happen on the first `next()`, as before.
- **Branch:** `orch/windowed-strict` from `main` at `b5e3886`, not pushed. To take it: `git merge orch/windowed-strict`.
- **Route and models:**
  - Reviewed: I built it myself (Opus), with one review by `orch-verifier` (Opus) and one re-check by `orch-rechecker` (Sonnet).
  - Estimated cost was about $2 of the $12 budget (a local estimate, not a bill).

The run record is kept in `.orchestrator/` as you asked, with the verbatim request, criteria, decisions and findings in `record.md`.