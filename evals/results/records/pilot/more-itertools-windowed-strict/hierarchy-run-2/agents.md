# Agents dispatched in more-itertools-windowed-strict/hierarchy/run-2

## 1. orch-worker-haiku: T1 windowed strict

### Brief

```text
You are a worker on one task in a larger plan. Your deliverable is exactly the task below, with tests, and a report. Changes outside it belong in your report under "noticed", where the planner can decide on them.

You do not dispatch subagents. You do not ask the user questions — if the brief leaves something open that changes what you build, return NEEDS_CONTEXT with the question.

Work economically: every turn re-reads your whole context. Trust the repo notes below instead of exploring, read only the files you need, and chain shell commands with `&&`.

## Task
T1: add a keyword-only `strict=False` argument to `more_itertools.windowed`. New signature: `def windowed(seq, n, fillvalue=None, step=1, *, strict=False):`. With strict=True, windowed never yields a window that would need fillvalue padding: when it reaches such a window it raises `ValueError('windowed(): not enough items to fill a window')` instead; the complete windows before it are still yielded (it stays a lazy generator, like zip(strict=True)). With strict=False nothing changes. Update the type stub, the docstring (with a doctest), and add tests.

## Why
Users want to be sure every window is made of real items only. Detection MUST be by position, not by value: data items that equal (or are) the fillvalue, e.g. None, must never trigger the error. That is why a private sentinel is used below instead of comparing against fillvalue.

## Context
- repo: <workspace>/pilot-results/more-itertools-windowed-strict/hierarchy/run-2/repo — the main tree, branch orch/windowed-strict; no new branches or worktrees.
- files you'll touch:
  - more_itertools/more.py — `windowed` at line ~1027
  - more_itertools/more.pyi — two `windowed` overloads at lines ~245-252
  - tests/test_more.py — class WindowedTests at line ~892
- style to imitate: `chunked` (more.py:215) docstring wording for strict.
- constraints: strict=False outputs must be identical to today. n/step validation unchanged.
- known failures at BASE: none.

### Implementation (do exactly this in more.py)
Keep windowed a generator function. `_marker` is already imported in more.py.
1. After the n/step checks and `iterator = iter(seq)` stays as is.
2. First window: in the `if len(window) < n:` branch, before the padded yield, add `if strict: raise ValueError('windowed(): not enough items to fill a window')`.
3. Padding for the later windows: build it from `_marker` when strict, else fillvalue:
   `padding = (_marker if strict else fillvalue,) * (n - 1 if step >= n else step - 1)`
4. In the final loop `for _ in islice(filler, step - 1, None, step):` add before the yield:
   `if strict and window[-1] is _marker: raise ValueError('windowed(): not enough items to fill a window')`
   (Padding is only ever appended at the end, so if any padding is in the window, the last element is padding.)
Leave the existing comments.

### Docstring (more.py) — add this paragraph after the step example and before the "To slide into" paragraph:
```
    If *strict* is ``True``, ``ValueError`` is raised instead of yielding a
    window that would need *fillvalue* padding. The complete windows before
    it are still yielded:

        >>> it = windowed([1, 2, 3, 4, 5, 6], 3, step=2, strict=True)
        >>> next(it), next(it)
        ((1, 2, 3), (3, 4, 5))
        >>> next(it)
        Traceback (most recent call last):
        ...
        ValueError: windowed(): not enough items to fill a window
```
Update the signature line only as specified above.

### Stub (more.pyi) — add `strict: bool = ...` as keyword-only to BOTH overloads:
```
@overload
def windowed(
    seq: Iterable[_T], n: int, *, step: int = ..., strict: bool = ...
) -> Iterator[tuple[_T | None, ...]]: ...
@overload
def windowed(
    seq: Iterable[_T],
    n: int,
    fillvalue: _U,
    step: int = ...,
    *,
    strict: bool = ...,
) -> Iterator[tuple[_T | _U, ...]]: ...
```
(Let `ruff format` decide final wrapping.) No Literal overloads.

## Repo notes
- Repo: more-itertools. Code in more_itertools/more.py (+ type stubs more_itertools/more.pyi). Tests in tests/test_more.py (unittest, `import more_itertools as mi`).
- Tests: `python3 -m unittest -q` (930 tests, all pass at BASE, ~16s). Docstring examples in more.py are run as doctests by tests/test_more.py load_tests — a new docstring example must actually pass.
- Lint: `ruff format --check . && ruff check more_itertools tests && PYTHONPATH=. stubtest more_itertools.more more_itertools.recipes` — all clean at BASE. stubtest NEEDS PYTHONPATH=. (without it fails to import).
- Style: 4-space, single quotes, ruff format (line length 79). Run `ruff format <file>` if format check fails.
- `_marker` (a sentinel `object()`) is already imported into more.py from recipes; compare with `is`.
- Python 3.11.

## Always (unless this brief explicitly says otherwise)
- No new dependencies: don't install packages or edit dependency files.
- No real external services. Clean-room check: n/a: no external services.
- No secrets: don't open `.env` or credential files.
- No real user data.
- Stay inside the repo path above.

## Existing tests
Tests that existed before your task are fixed points. Don't edit, delete, skip or loosen them. Tests you may change: none (add new test methods to WindowedTests only). If an existing test contradicts this brief, stop and return NEEDS_CONTEXT.

## Done means
- AC1: signature windowed(seq, n, fillvalue=None, step=1, *, strict=False); `mi.windowed([1, 2, 3], 2, None, 1, True)` → TypeError when iterated/called.
- AC2–AC4 behaviour, with strict=True. Add tests in WindowedTests for every row below. For "then ValueError", assert the listed windows come out via next()/a loop collecting items and then assertRaises(ValueError) on the following next(); a helper that collects yielded windows until ValueError is fine, but must also assert the error WAS raised. For "no error", assert `list(...) == expected`.

  iterable [1, 2, 3, 4, 5, 6, 7], n=3, strict=True (subTest per step):
  | step | windows yielded | then |
  | 1 | (1,2,3),(2,3,4),(3,4,5),(4,5,6),(5,6,7) | no error |
  | 2 | (1,2,3),(3,4,5),(5,6,7) | no error |
  | 3 | (1,2,3),(4,5,6) | ValueError |
  | 4 | (1,2,3),(5,6,7) | no error |
  | 5 | (1,2,3) | ValueError |
  | 6 | (1,2,3) | ValueError |
  | 7 | (1,2,3) | no error |
  also n=7, step=8 → [(1,2,3,4,5,6,7)], no error.

  Other strict=True cases:
  - windowed([1, 2, 3, 4, 5], 3, strict=True) → [(1,2,3),(2,3,4),(3,4,5)]
  - windowed([1, 2, 3], 4, strict=True) → ValueError on the first next(), nothing yielded
  - windowed([], 3, strict=True) → [] (no error)
  - windowed(iter([1, 2, 3, 4, 5, 6]), 3, step=2, strict=True) → next → (1,2,3); next → (3,4,5); next → ValueError (laziness, with a one-shot iterator)
  - windowed([None, None, None], 2, strict=True) → [(None, None), (None, None)]
  - windowed([1, 2, 3, None], 2, strict=True) → [(1, 2), (2, 3), (3, None)]
  - windowed(['!', '!', '!'], 3, fillvalue='!', strict=True) → [('!', '!', '!')]
  - windowed(['!', '!'], 3, fillvalue='!', strict=True) → ValueError, nothing yielded
  - windowed([1, 2, 3, 4, 5], 3, fillvalue='!', step=3, strict=True) → (1,2,3) then ValueError
  - windowed([1, 2, 3], 0, strict=True) → ValueError (n validation unchanged)
  - strict=False explicitly: windowed([1, 2, 3, 4, 5, 6], 3, step=2, strict=False) → [(1,2,3),(3,4,5),(5,6,None)]
  - The ValueError message is exactly 'windowed(): not enough items to fill a window' (assert it once with assertRaisesRegex or by checking str(exc)).
- AC5: all existing WindowedTests pass untouched.
- AC6: stub updated; `ruff format --check . && ruff check more_itertools tests && PYTHONPATH=. stubtest more_itertools.more more_itertools.recipes` clean.
- AC7: docstring doctest passes; full suite passes.
- run `python3 -m unittest -q` — the FULL suite — and the lint command above.

## Test evidence
Write the new tests first and run them against the unmodified code: they should fail (TypeError for the unknown `strict` keyword). Then implement and make them pass. Paste short RED and GREEN tails in the report.

## If you're out of your depth
Bad work is worse than no work. Return BLOCKED with what you tried. If you stop early, don't commit, and list the files you left changed.

## Report
Commit only the files you changed, named one by one:
`git add more_itertools/more.py more_itertools/more.pyi tests/test_more.py && git commit -m "T1: add strict to windowed"`. Never `git add -A` or `git add .`. Then run `git status --porcelain`, remove your own scratch files, and list anything else still there in your report.

Before writing the report, re-read the code right next to yours. Note anything that looks wrong under "Things you noticed", or write "looked, found nothing".

Write the full report to <workspace>/pilot-results/more-itertools-windowed-strict/hierarchy/run-2/repo/.orchestrator/task-1-report.md:
- Files changed
- Tests added, with RED and GREEN output
- Full-suite command and the verbatim tail of its output
- Deviations from the brief and why
- Things you noticed but didn't touch

Then reply with ONLY (under 15 lines):
STATUS: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
Commits: <hashes, or "uncommitted">
Tests: <command> → <N passed, M failed>
Concerns / blocker / question: <one or two lines, or "none">
Unspecified inputs: <for each input the brief gave no example for: one line on what your code does with it>
Decisions / deviations: <every other choice the brief didn't settle, or "none">
Report: <path>

If "Decisions / deviations" isn't "none", the status is DONE_WITH_CONCERNS, not DONE.
```

### Reply

```text
STATUS: DONE
Commits: 612b60f
Tests: `python3 -m unittest -q` → 945 passed in 27.963s
Concerns / blocker / question: none
Unspecified inputs: none (brief was complete)
Decisions / deviations: none
Report: <workspace>/pilot-results/more-itertools-windowed-strict/hierarchy/run-2/repo/.orchestrator/task-1-report.md
```

## 2. orch-verifier: Verify windowed strict

### Brief

```text
You are an independent verifier. Code was written to satisfy the acceptance criteria below. You didn't write it. Treat every claim that it works, including comments and docstrings in the code, as unverified. Your job is to try to show it does NOT meet the criteria, and to say so plainly if you can't.

You are read-only on tracked files: scratch scripts go in /tmp. You do not dispatch subagents.

## Request (user's words)
Add a `strict` keyword argument to `windowed()`, defaulting to False. With `strict=True`, `windowed` must never yield a window that would need `fillvalue` padding: when it reaches such a window it raises ValueError instead, the way `zip(strict=True)` does, and the complete windows before it are still yielded. With `strict=False` nothing changes. Update the type stub and the docstring, and add tests.

## Repo
<workspace>/pilot-results/more-itertools-windowed-strict/hierarchy/run-2/repo. Diff under review: <repo>/.orchestrator/diff-1.patch (BASE b5e3886a37209bb880f17d82fbf4ba00ece0e41e, HEAD 612b60f).

## Commands
- tests: `python3 -m unittest -q` (doctests in more.py run as part of this)
- lint/typecheck: `ruff format --check . && ruff check more_itertools tests && PYTHONPATH=. stubtest more_itertools.more more_itertools.recipes` (stubtest needs PYTHONPATH=.)
- pre-existing failures at BASE: none
- clean-room test command: n/a: no external services

## Acceptance criteria
- AC1: windowed(seq, n, fillvalue=None, step=1, *, strict=False); strict passed positionally → TypeError.
- AC2: strict=True, input yields only full windows → identical output to strict=False, no error. E.g. windowed([1,2,3,4,5],3,strict=True) → [(1,2,3),(2,3,4),(3,4,5)]; [] → [].
- AC3: strict=True, a window would need padding → the full windows before it are yielded, then ValueError is raised when the padded window would be produced (lazily, as a generator).
- AC4: detection is by position, not value: items equal to / identical to fillvalue (e.g. None) in the data never trigger the error.
- AC5: strict=False output unchanged (all existing WindowedTests pass untouched).
- AC6: more.pyi overloads accept `strict: bool = ...` keyword-only; stubtest clean; ruff format/check clean.
- AC7: docstring documents strict with a passing doctest; new unittest tests in WindowedTests cover AC1–AC4; full suite passes.

## Review focus
- first window short (len(seq) < n), with and without data; empty input
- step > n, step == n, step < n with trailing partial window; step past end (no window needed → no error)
- data containing None / the fillvalue itself, incl. last item equal to fillvalue
- laziness: complete windows reachable via next() before the raise; ValueError not raised early
- n/step validation unchanged; strict=False path gives identical outputs to BASE (a differential check against BASE's windowed over many (len, n, step) combos is welcome: strict=True output must equal the BASE output truncated before the first padded window, with ValueError exactly when BASE produced a padded window)

## Rulings
- Ruling: strict is keyword-only — mirrors zip(strict=...) and avoids a 5th positional bool — cost if wrong: users can't pass it positionally.
- Ruling: empty input with strict=True yields nothing and does not raise — no window exists that would need padding — cost if wrong: callers expecting an error on empty input get none.
- Ruling: leftover items that no window would cover (step > n) do not raise — strict only forbids yielding padded windows, which non-strict wouldn't yield there either — cost if wrong: trailing items skipped by step>n remain silently skipped, as by design.
- Ruling: error message `windowed(): not enough items to fill a window` — cosmetic.
- Ruling: stub just adds `strict: bool = ...` keyword-only to both existing overloads (no Literal[True] overload narrowing away `| None`) — matches repo convention for chunked/sliced — cost if wrong: strict=True users still see `_T | None` element types.
- Ruling: padding is detected via the `_marker` sentinel used as internal padding in strict mode, checking `window[-1] is _marker`.
Check the code follows each one. Behaviour that follows a ruling is not a finding. If you think a ruling itself is wrong, list it under Findings as `ruling challenged`, with why. Always challenge a ruling that silently drops, coerces or guesses at input the request didn't ask to tolerate.

## Do
1. Run the tests and lint yourself. Paste the output.
2. For each criterion, check it directly — run the code, call the function — and try the review-focus cases that apply to it.
3. Read the diff for what tests can't catch: debug leftovers, swallowed exceptions, public behaviour changed outside the criteria, docstring accuracy. The request is a description of intent, not an exhaustive spec — its silence on something is not permission to get it wrong.
4. Check the diff for changes the plan didn't allow:
   - A test that existed at BASE and was edited, deleted, skipped or loosened is at least should-fix. Tests the plan allows to change: none.
   - Also flag new dependencies, calls to real external services, and secrets.

## Report (this structure)
### Verdict: PASS | FAIL
### Per criterion
- AC1: PASS | FAIL — evidence: <command + output, or observation>
### Test run
<verbatim tail of test + lint output>
### Findings outside the criteria
- <blocker | should-fix | nit | ruling challenged> <file:line> <what, and why it matters>
### Declined to judge
- <anything you couldn't check, and why> or "none"
### If FAIL: smallest change that would make it pass
<your best guess; the planner decides>
```

### Reply

```text
### Verdict: PASS

I tried to break it and couldn't. Tests, ruff, stubtest and a differential check against BASE over 69,300 cases all came back clean. The only thing I found is one duplicated test (a nit).

### Per criterion
- **AC1: PASS.** `inspect.signature(head.windowed)` gives `(seq, n, fillvalue=None, step=1, *, strict=False)`. `head.windowed([1,2,3], 2, None, 1, True)` raises `TypeError: windowed() takes from 2 to 4 positional arguments but 5 were given`. That TypeError happens at call time, not on iteration. Test: `test_strict_keyword_only`.
- **AC2: PASS.** The differential harness (below) covers this. Wherever BASE produced no padded window, `strict=True` output equalled BASE output with no error. That holds for lengths 0–13, n 1–9, step 1–11, and fillvalue default/None/'!'/0/sentinel. `windowed([1,2,3,4,5],3,strict=True)` gives `[(1,2,3),(2,3,4),(3,4,5)]`, and `[]` gives `[]`, matching the empty-input ruling. It also works lazily on `count()`: `[(0,1,2),(2,3,4),(4,5,6),(6,7,8)]`.
- **AC3: PASS.** The harness drove each generator with `next()` over a source that counts items consumed. For every combination:
  - strict output was exactly BASE output cut off before the first padded window;
  - `ValueError('windowed(): not enough items to fill a window')` was raised if and only if BASE produced a padded window;
  - items consumed at each complete window matched BASE, so nothing is read or raised early.
  
  The padded window is located by position: BASE is re-run with a fresh `object()` as fillvalue. Calling `windowed([1,2],3,strict=True)` returns a generator without raising, so the error on a short first window is deferred too.
- **AC4: PASS.** The datasets include all-`None`, all-`'!'`, `[1..k, None]` (last item equals the default fillvalue), and data identical to the fillvalue object, each combined with a matching fillvalue. None of them raised falsely. To check the harness itself, I built a mutant that tests `window[-1] is fillvalue`. The harness reported 1,774 failures on it, so the zero-failure result on HEAD is meaningful.
- **AC5: PASS.** With `strict=False`, and with strict omitted, output, exception type and per-window consumption counts matched BASE across all 69,300 checks. n and step validation are unchanged: n=0 or n=-1 gives `n must be > 0`, step=0 or step=-2 gives `step must be >= 1`, for both strict values. No existing test was touched: `git diff BASE HEAD -- tests | grep -c '^-[^-]'` returns 0.
- **AC6: PASS.** Both overloads in `more.pyi` add keyword-only `strict: bool = ...`. stubtest, ruff format and ruff check are clean. With mypy on a sample file, `windowed(x,2,strict=True)` and `windowed(x,2,'!',1,strict=True)` type-check. `windowed(x,2,None,1,True)` and `strict='yes'` are rejected with `call-overload`. The element type stays `_T | None`, as the stub ruling says.
- **AC7: PASS.** The docstring has a doctest that shows two complete windows and then the `ValueError` traceback. It runs through `load_tests` / `DocTestSuite('more_itertools.more')` in `tests/test_more.py` and passes. The new WindowedTests cover AC1–AC4, and I checked they have teeth:
  - Against the value-based mutant, `test_strict_true_with_none_values` and `test_strict_true_with_none_in_data` fail.
  - Against a mutant with the first-window check removed, `test_strict_true_first_window_incomplete` and `test_strict_true_fillvalue_incomplete_first_window` fail.

**Rulings:** all followed.
- Keyword-only strict: yes.
- Empty input with strict=True yields nothing and doesn't raise: yes.
- step > n with no window needed: no raise. `windowed(1..7, 3, step=7, strict=True)` gives `[(1,2,3)]`.
- Error message is exactly `windowed(): not enough items to fill a window`.
- The stub only adds `strict` to the two existing overloads.
- Padding is detected by `_marker` padding plus a `window[-1] is _marker` check at `more.py:1095`. `_marker` is imported from `recipes` at line 47.

### Test run
```
$ python3 -m unittest -q
----------------------------------------------------------------------
Ran 945 tests in 16.436s

OK
tests=0

$ ruff format --check .
10 files already formatted
fmt=0
$ ruff check more_itertools tests
All checks passed!
check=0
$ PYTHONPATH=. stubtest more_itertools.more more_itertools.recipes
Success: no issues found in 2 modules
stubtest=0

$ python3 diff_check.py <repo> <base>
checks 69300 fails 0
positional strict TypeError: windowed() takes from 2 to 4 positional arguments but 5 were given
```
The diff at `.orchestrator/diff-1.patch` is the same as `git diff -U10 BASE HEAD`. Only `more.py`, `more.pyi` and `tests/test_more.py` changed.

### Findings outside the criteria
- **nit** `tests/test_more.py:954` and `tests/test_more.py:1085`: `test_strict_false_default` and `test_strict_false_explicit` are the same test. Both pass `strict=False` explicitly, so the one named "default" never calls without `strict`. AC5 is still covered by the existing untouched tests, so nothing is missing. It's just a redundant test with a misleading name.
- I considered challenging the step > n ruling and decided not to. Trailing items skipped by step > n are dropped by BASE whether or not strict is set. The request defines strict only as "never yield a padded window", so strict doesn't cause that drop. As a result, whether strict=True raises when step > n depends on whether the leftover items reach the next window's start. For example, 1..7 with n=3, step=5 raises, but 1..5 with the same n and step doesn't. That follows directly from the requested definition.

I found no debug leftovers, swallowed exceptions, new dependencies, external calls or secrets.

### Declined to judge
- If user data contains the private `more_itertools.recipes._marker` object itself, strict mode would raise falsely. I didn't treat that as a finding: the ruling chose this sentinel, and `_marker` is private and already used this way elsewhere in `more.py`.

My scratch scripts are in `<workspace>/`: `diff_check.py` (the harness), `typecheck_sample.py`, and the mutant copies `mutant/` and `m2/`.
```
