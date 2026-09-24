# windowed-strict

## Request
See .orchestrator/request.md (verbatim). Add `strict=False` kwarg to `more_itertools.windowed`; strict raises ValueError instead of yielding any padded window, after yielding all complete windows before it.

## Done means
- C1: `windowed(..., strict=False)` and calls without `strict` behave exactly as at BASE (existing WindowedTests pass unchanged; default is False).
- C2: With strict=True, every window that would contain fillvalue padding raises ValueError at the point it would be yielded; all complete windows before it are yielded first (lazy, like zip(strict=True)). Covers: non-empty seq shorter than n (raises before any yield); trailing partial window for step < n, step == n, step > n.
- C3: With strict=True, inputs whose windows are all complete yield the same as strict=False (incl. empty seq -> no windows, no error; step past the end -> no error).
- C4: Padding detection doesn't depend on values: a seq containing items equal to fillvalue (e.g. None) doesn't falsely raise.
- C5: Type stub `more.pyi` accepts `strict`; stubtest passes for more_itertools.more.
- C6: Docstring documents `strict` with a doctest; doctests pass (test suite loads doctests).
- C7: `python3 -m unittest -q` passes fully; `ruff format --check` and `ruff check` clean.

## Baseline
- BASE b5e3886, branch orch/windowed-strict; test command: python3 -m unittest -q
- Known failures at BASE: none (930 passed)

## Contracts to preserve
- windowed(seq, n, fillvalue=None, step=1) positional signature and output; ValueError for n <= 0 and step < 1.
- Stub overloads for fillvalue typing.

## Route
- Builders: me · Review: independent orch-verifier (user asked for Reviewed mode)
- Requirements set: orch.sh require review

## Decisions
- Decision: `strict` is keyword-only (`*, strict=False`) — matches zip(strict=True) and avoids positional misuse after `step`; request says "keyword argument" — cost if wrong: someone passing it positionally gets TypeError.
- Decision: empty seq with strict=True yields nothing and does not raise — no window exists, so none needs padding — cost if wrong: small behaviour difference for empty input.
- Decision: fillvalue may still be passed with strict=True; it's simply never emitted — no reason to reject — low cost.
- Decision: validation of n/step keeps its existing lazy (generator) timing — unchanged contract.
- Decision: detect padding via a private sentinel used as internal fill in strict mode (padding is only ever trailing), so user values equal to fillvalue can't trigger false errors.
- Decision: stub gets a `strict: Literal[True]` overload returning Iterator[tuple[_T, ...]] (no fill type) plus `strict: bool = ...` on existing overloads.

## Work
- implementation + stub + docs + tests: me — done — 56286b8
- repair 1 (separate non-strict loop): me — done — 60bf412

## Findings and repairs
- Review (orch-verifier) on 56286b8: PASS, C1-C7 met, no blocking findings.
- observation — ~4% slowdown on non-strict loop from per-iteration `strict and ...` check (more.py:1101); timeit BASE 21.0/20.6ms vs 21.8/21.4ms — fixed in 60bf412 (non-strict loop restored verbatim, strict loop separate); my timeit 20.5 vs 20.5 ms; rechecker ADDRESSED.
- Re-check (orch-rechecker) on 60bf412: PASS, no new findings.
- Incident: the rechecker ran `pip install mypy` into system Python (/usr/local/lib/python3.11/dist-packages; mypy 2.3.1 + deps). Outside the repo and not authorized; not reverted (unclear which deps pre-existed); disclosed to user. Doesn't affect evidence (suite doesn't use mypy).
- Repair cycles used: 1 of 2

## Status
Done — candidate 60bf412; gate passed
