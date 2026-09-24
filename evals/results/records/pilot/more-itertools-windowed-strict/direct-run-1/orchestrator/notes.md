# windowed(strict=...) — Direct run notes

## Acceptance criteria
1. strict=False (default): behaviour unchanged (existing tests untouched and passing).
2. strict=True: ValueError raised exactly where strict=False would yield a padded window; all complete windows before it are yielded.
3. Padding detected structurally (private marker), not by comparing to fillvalue, so data equal to fillvalue never raises.
4. Empty input, and trailing items skipped by step, don't raise (no padded window would be produced).
5. Stub + docstring updated; tests added; full suite `python3 -m unittest -q` passes.

## Decisions
- Decision: `strict` is keyword-only — mirrors zip(strict=...) and avoids positional confusion after fillvalue/step — cost if wrong: small API relaxation later is backward compatible.
- Decision: strict semantics = "raise exactly where non-strict would yield a padded window" (so items skipped entirely by step > n don't raise) — the request says "never yield a window that would need padding"; a window that is never produced needs no padding — cost if wrong: users expecting "every item covered" semantics would need a different check.
- Decision: in strict mode the user's fillvalue is ignored internally (replaced by a private object() marker) — it can never be yielded in strict mode anyway — cost if wrong: none observable.
- Decision: stub uses `strict: bool = ...` on both overloads, not a Literal[True] overload narrowing the element type — mypy isn't installed and installing it is out of scope; a simpler stub that can't be wrong beats an unverified precise one — cost if wrong: strict=True users still see `_T | None` element type.
- Decision: added a changelog entry under Unreleased in docs/versions.rst, following repo convention.
- Error message: 'windowed() ran out of items before filling a window'.

## Evidence
- Mutation check (scratchpad copy): removing the loop check, the marker, or the first-window check each made the new tests fail (48 / 3 errors / 61).
- mypy / ruff not available locally; overlong lines checked by hand (none added in changed code).
