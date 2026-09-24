# Agents dispatched in more-itertools-windowed-strict/reviewed/run-1

## 1. orch-verifier: Independent review of windowed strict

### Brief

```text
You are an independent reviewer. Someone else wrote a change; check whether it does what the
user asked, without breaking what already worked. Treat claims in comments, commit messages
and docstrings as unverified.

Don't edit tracked files: put scratch scripts in /tmp. Don't delegate.

## The user's request (verbatim)
In this repo (more-itertools), add a `strict` keyword argument to `windowed()`, defaulting to False. With `strict=True`, `windowed` must never yield a window that would need `fillvalue` padding: when it reaches such a window it raises ValueError instead, the way `zip(strict=True)` does, and the complete windows before it are still yielded. With `strict=False` nothing changes. Update the type stub and the docstring, and add tests. The test suite runs with `python3 -m unittest -q`.

(Context for this run: no one is available to answer questions until you finish, so make sensible calls, record them, and carry on. Keep any plan, notes or report files you create; don't delete them at the end.)

## Candidate
Repo <workspace>/pilot-results/more-itertools-windowed-strict/reviewed/run-1/repo, candidate c9247b249c8f on branch orch/windowed-strict. Patch: .orchestrator/review/candidate-c9247b249c8f.patch
(BASE b5e3886a3720..candidate).

## Contracts to preserve
- Positional signature `windowed(seq, n, fillvalue=None, step=1)` and its existing output for every input (more_itertools/more.py `windowed`); ValueError for n<=0 / step<1; empty input yields nothing.
- Internal callers of windowed in more_itertools/more.py (around lines 2209, 2594, 3483) use the default non-strict mode and must behave identically.
- Stub conventions in more_itertools/more.pyi (overloads; `stubtest` must pass). Changelog convention: docs/versions.rst "Unreleased" section.

## Acceptance criteria (the main session's reading of the request)
- C1: `windowed(..., strict=True)` yields exactly the non-strict output minus any window containing padding, and raises ValueError where the non-strict version would yield a padded window (first-window-short and later-window cases, all step/n relations).
- C2: Complete windows before the bad one are yielded before the raise (lazy, zip-like).
- C3: No raise when no window needs padding: exact fit, empty input, trailing items skipped entirely by a large step (e.g. n=3, step=7, 7 items).
- C4: Padding detection doesn't depend on fillvalue's value (real items equal to fillvalue/None don't trigger a raise).
- C5: strict=False behaviour unchanged; existing tests pass unmodified.
- C6: `more.pyi` accepts `strict`; stubtest and mypy on usage pass; ruff format/check clean.
- C7: Docstring documents *strict* with a doctest that passes (doctests run through the unittest suite's load_tests).
- C8: Full suite `python3 -m unittest -q` passes.
Where a criterion misses or contradicts the request, say so: the request is the reference.

## Decisions the main session made (decisions, not facts)
- Decision: `strict` is keyword-only (`*, strict=False`) — mirrors zip(strict=), avoids a stray positional bool after `step`.
- Decision: empty input with strict=True yields nothing and doesn't raise — no window exists, so none needs padding.
- Decision: trailing items that fall entirely in a skipped gap (step > n) don't raise — no window starts there, and non-strict yields no window there either.
- Decision: padding detected by using the private sentinel `_marker` as the padding value when strict.
- Decision: stub adds a `strict: Literal[True]` overload (first) returning `Iterator[tuple[_T, ...]]`, and `strict: bool` on the existing overloads.
- Decision: plain ValueError with message "windowed(): iterable too short to fill the final window".
- Decision: changelog line added under "Unreleased" in docs/versions.rst.
Check the code follows each one. If a decision looks wrong against the request or a contract,
report it as a finding.

## Commands
- tests: python3 -m unittest -q   lint: ruff format --check . && ruff check more_itertools tests
- stubtest: PYTHONPATH=. stubtest more_itertools.more more_itertools.recipes
- mypy usage: MYPYPATH=. python3 -m mypy --no-incremental <your snippet in /tmp>
- offline run: n/a (pure library code, no network)
- known failures at BASE: none

## Do
1. Run the tests and lint. Report the output tail.
2. Check each criterion directly, by running the code, and try the edge cases the request
   implies.
3. Read the patch for what tests miss: changed public behaviour, error paths, data silently
   dropped or coerced, edits to existing tests or test configuration, secrets, new
   dependencies or network calls.

## Findings
Each finding needs:
- the requirement or contract it violates
- the location (file:line)
- a reproduction, or specific source evidence
- the practical impact, and the smallest justified correction

Classify each as **blocking** (the change is wrong or unsafe to deliver), **optional
improvement**, or **observation**. Match the severity to the impact; don't pad or merge
findings. A clean review, with no findings, is a valid and useful result.

## Report
### Verdict: PASS | FAIL (FAIL only for a blocking finding or a failed criterion)
### Criteria: C1 PASS | FAIL | NOT CHECKED — evidence
### Test run: <tail>
### Findings: <each, as above, or "none">
### Not verified: <anything you couldn't check, and why, or "none">

```

### Reply

```text
### Verdict: PASS

I found no blocking problems and have no findings to report. The tree is unchanged at c9247b249c8f.

### Criteria
- **C1 PASS.** I wrote my own check in `/tmp/rev/check.py` covering 14,784 cases: sizes 0 to 13, n 1 to 8, step 1 to 11, and fillvalues None, '!' and 0. For the data I used plain ranges, lists made entirely of the fillvalue, and lists made entirely of None. The reference was the non-strict output run with a private sentinel as the fill. In every case, strict mode yielded exactly the unpadded windows and raised ValueError only when non-strict would have yielded a padded window. That includes a short first window, a short later window, n == step, n > step and n < step. There were 0 mismatches. The same check confirmed that only the last non-strict window can ever hold padding.
- **C2 PASS.** The same check collects every yielded window before catching the error, so the complete windows came out before the raise in all cases. `windowed(count(), 3, strict=True)` stays lazy. The strict branch (`more_itertools/more.py:1104-1109`) checks `window[-1] is _marker` before each yield, and the source is consumed exactly as in non-strict mode.
- **C3 PASS.** An exact fit, empty input (`[]`), and n=3, step=7 with 7 items (result `[(1, 2, 3)]`, no raise) all behave correctly. The exhaustive check covered every trailing-gap case with step > n.
- **C4 PASS.** Data made entirely of the fillvalue or of None never raised wrongly (included in the 14,784 cases). The padding value is `_marker` (`more.py:1092`) and the test is an identity check.
- **C5 PASS.** `/tmp/rev/cmp.py` compared BASE (from `git archive b5e3886`) against the candidate over 3,960 inputs, both without `strict` and with `strict=False`: 0 mismatches. The error messages for n=0, n=-1, step=0 and step=-1 are identical. The internal callers at `more.py:2239`, `2624` and `3513` don't pass `strict`, so they go through the unchanged non-strict loop. No existing test was changed; the test diff only adds lines. Speed without `strict` is the same (12.2 ms at BASE, 12.0 ms now).
- **C6 PASS.** stubtest reported "Success: no issues found in 2 modules". I also ran mypy on `more.pyi` itself, since stubtest doesn't check overload overlap: clean. For a mypy usage snippet (`/tmp/rev/usage.py`), the inferred types are:
  - `strict=True`, with or without a fillvalue, gives `Iterator[tuple[int, ...]]`.
  - `strict=False` or `strict=<bool variable>` without a fillvalue gives `tuple[int | None, ...]`.
  - The same with fillvalue `'x'` gives `tuple[int | str, ...]`.
  - Existing call forms are unchanged. `Literal` was already imported.

  ruff format and ruff check are clean.
- **C7 PASS.** The docstring documents *strict* and includes a doctest. That doctest runs as "Doctest: more_itertools.more.windowed ... ok" through `load_tests` in `tests/test_more.py:44`. `docs/api.rst:65` uses a plain `autofunction:: windowed`, so the rendered signature will show `strict` automatically.
- **C8 PASS.** The full suite passes (940 tests). Coverage with CI's `--include` gives `more.py` 1809 statements, 0 missed, 100% (CI requires at least 99%).

The main session's decisions all match the code:
- `strict` is keyword-only; a test checks that passing it positionally raises TypeError.
- Empty input yields nothing.
- Items left in a skipped gap don't raise.
- Padding is detected with the `_marker` sentinel.
- The `Literal[True]` overload comes first, and the other two overloads take `strict: bool`.
- The error message is the exact text decided on.
- The changelog line is under "Unreleased".

None of these conflicts with the request.

To test the new tests themselves, I made deliberately broken copies of the code in `/tmp/rev/mut`. The tests caught all five that change behaviour:
- comparing against the fillvalue instead of the sentinel
- dropping the first-window check
- checking `window[0]` instead of `window[-1]`
- padding with the fillvalue in strict mode
- stopping silently instead of raising

### Test run
```
Ran 940 tests in 27.196s

OK
---
10 files already formatted
All checks passed!
---
Success: no issues found in 2 modules
```

### Findings
none

### Not verified
- The Sphinx docs build (`make docs`, which runs with `-W`) wasn't run because Sphinx isn't installed here. Risk is low: the new docstring block uses the same doctest and Traceback layout as 11 others already in `more.py`.
- I only ran the suite on this machine's Python 3.11. CI also covers 3.10, 3.12 to 3.14 and pypy-3.10.

Scratch scripts are in `/tmp/rev/` (`check.py`, `cmp.py`, `usage.py`, `mutate.py`).
```
