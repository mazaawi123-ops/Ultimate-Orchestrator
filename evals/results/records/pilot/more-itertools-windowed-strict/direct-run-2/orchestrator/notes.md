# windowed(strict=...) — plan and notes (Direct mode)

## Acceptance criteria
1. `windowed(seq, n, fillvalue=None, step=1, *, strict=False)`; default behaviour byte-for-byte unchanged (existing tests pass untouched).
2. strict=True: every complete window before the first would-be-padded window is yielded, then ValueError is raised; no padded window is ever yielded.
3. strict=True with len(seq) < n (non-empty): ValueError on first next(), nothing yielded.
4. strict=True where windows line up exactly (incl. step > n where trailing items are skipped by the step): no error, same output as strict=False.
5. strict=True with empty input: yields nothing, no error (strict=False yields nothing too; no window is needed at all).
6. Detection does not depend on the value of fillvalue (a real item equal to fillvalue must not trigger the error).
7. Stub accepts `strict`; docstring documents it with a doctest.
8. Full suite `python3 -m unittest -q` passes (baseline 930/930).

## Decisions
- Decision: `strict` is keyword-only — it's described as a keyword argument, and positional use after `step` would be error-prone — cost if wrong: callers can't pass it positionally (easy to relax later).
- Decision: empty input with strict=True yields nothing and does not raise — strict=False yields no windows (no padding needed), matching zip(strict=True) on all-empty inputs — cost if wrong: a caller wanting "at least one window" gets no error.
- Decision: `fillvalue` passed together with strict=True is accepted and simply unused, not an error — zip-like, least surprising — cost if wrong: a silent no-op argument.
- Decision: padding detected via a private per-call sentinel object, not by comparing to fillvalue — padding is always at the tail of a window, so checking `window[-1] is sentinel` is exact — cost if wrong: none known.
- Decision: stub adds `strict: bool = ...` to both existing overloads; no Literal[True] overload narrowing the return type — mypy isn't installed here and installing it is a new dependency, so a more elaborate overload couldn't be verified — cost if wrong: strict=True callers still see `_T | None` element types.
- Error message: 'not enough items to fill the final window' (used for both the short first window and a later padded one).

## Evidence notes
- Mutants (scratch, reverted): disabling the in-loop padding check -> 46 failures; removing the first-window strict check -> 253 failures; not using a sentinel -> error. All caught.
- mypy is not installed (typechecks requirement); stub change not type-checked — not installed to avoid adding a dependency.
- flake8 not installed (run logged as fail: "No module named flake8"); added lines were checked manually for >79 chars instead: none.
