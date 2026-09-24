# windowed-strict

## Request
See .orchestrator/request.md (verbatim). Add `strict=False` to `windowed()`; strict=True raises ValueError instead of yielding any padded window, after yielding the complete windows before it.

## Done means
- C1: `windowed(..., strict=True)` yields exactly the non-strict output minus any window containing padding, and raises ValueError where the non-strict version would yield a padded window (first-window-short case and later-window cases, all step/n relations). Checked by new tests in `tests/test_more.py::WindowedTests` including an exhaustive comparison against non-strict output.
- C2: Complete windows before the bad one are yielded before the raise (lazy, zip-like). Named test.
- C3: No raise when no window needs padding: exact fit, empty input, trailing items skipped by a large step (e.g. n=3, step=7, 7 items).
- C4: Padding detection doesn't depend on fillvalue's value (real items equal to fillvalue/None don't trigger a raise). Named test.
- C5: strict=False behaviour unchanged: all existing tests pass unmodified; default path code unchanged in output.
- C6: `more.pyi` accepts `strict`; `stubtest more_itertools.more` and mypy on a small usage snippet pass; ruff format/check clean.
- C7: Docstring documents *strict* with a doctest; doctests pass (they run via the unittest suite's load_tests).
- C8: Full suite `python3 -m unittest -q` passes.

## Baseline
- BASE b5e3886, branch orch/windowed-strict; test command: python3 -m unittest -q
- Known failures at BASE: none (930 passed)

## Contracts to preserve
- Positional signature `windowed(seq, n, fillvalue=None, step=1)`; ValueError for n<=0 / step<1; empty input yields nothing.
- Internal callers (more.py: 2209, 2594, 3483) use default non-strict.

## Route
- Builders: me · Review: independent (orch-verifier), user requested Reviewed mode
- Requirements set: orch.sh require review

## Decisions
- Decision: `strict` is keyword-only (`*, strict=False`) — mirrors `zip(strict=)`, prevents a stray positional bool being taken as strict after `step` — cost if wrong: callers can't pass it positionally; easy to relax later, can't tighten later.
- Decision: empty input with strict=True yields nothing and does not raise — no window exists, so none needs padding (same as zip() of empties) — cost if wrong: one-line change.
- Decision: trailing items that fall entirely in a skipped gap (step > n) do not raise — no window starts there, so none would be padded; matches the non-strict output which yields no window there — cost if wrong: users expecting "all items consumed into windows" semantics would be surprised.
- Decision: detect padding with a private sentinel (`_marker`) used as the padding value when strict, so real items equal to fillvalue never trigger a raise — cost if wrong: none known.
- Decision: stub gets a `strict: Literal[True]` overload returning `Iterator[tuple[_T, ...]]` (no fillvalue in the element type), plus `strict: bool` on the existing overloads.
- Decision: ValueError message: "windowed(): iterable too short to fill the final window" (plain ValueError, like chunked(strict=True)).
- Decision: add a changelog line under "Unreleased" in docs/versions.rst, following the repo's convention.

## Work
- implementation + stub + docstring + tests + changelog: me — done — c9247b2

## Findings and repairs
- Review (orch-verifier, candidate c9247b2): PASS, no findings. Not verified by reviewer: Sphinx build (not installed), Pythons other than 3.11.
- Repair cycles used: 0 of 2

## Status
Done — candidate c9247b2; suite 940/940, ruff, stubtest, mypy usage, independent review all pass.
