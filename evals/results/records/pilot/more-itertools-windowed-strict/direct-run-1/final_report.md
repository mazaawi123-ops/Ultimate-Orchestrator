## Done: `windowed()` has a keyword-only `strict` argument, and the full suite passes (937 tests)

- **What changed:** with `strict=True`, `windowed` raises `ValueError("windowed() ran out of items before filling a window")` at exactly the point where the default mode would yield a padded window. The complete windows before that point are still yielded. The default mode behaves exactly as before.
- **How it spots padding:** in strict mode the function pads with a private marker object instead of `fillvalue`. So an item that happens to equal `fillvalue` never triggers an error. Padding can only land in the last window, at its end, so one check per window is enough (`more_itertools/more.py:1027`).
- **Other files:** the type stub (`more.pyi`) has `strict: bool = ...` on both overloads. The docstring has a strict example, which runs as a doctest. There's a changelog entry under Unreleased in `docs/versions.rst`, and 7 new tests in `WindowedTests`. One of those tests compares strict and non-strict output across every combination of input length 0–8, `n` 1–5 and `step` 1–6.
- **Criteria:** all 5 met. `python3 -m unittest -q` on commit 9dbe2a3 ran 937 tests and all passed (`.orchestrator/logs/002-check.log`). The final evidence check passed on that commit.
- **Checking the tests:** I broke the implementation three ways in a scratch copy (removed the loop check, dropped the private marker, removed the first-window check). The new tests failed each time.
- **Failures before the change:** none.
- **Test changes:** none to existing tests; tests were only added.
- **Review:** none, since you asked for Direct mode.
- **Not verified:** mypy and ruff aren't installed here, and installing them was outside the task. The stub change isn't type-checked. I checked line lengths by hand; the changed code adds no lines over 79 characters.
- **Decisions** (also recorded in `.orchestrator/notes.md`):
  - `strict` is keyword-only, as in `zip(strict=...)`.
  - The error is raised only when the default mode would actually yield a padded window. Trailing items that a large `step` skips over don't count, because no window is built from them. The same goes for empty input, which yields no windows and doesn't raise.
  - The stub keeps element types as `_T | None`, even though strict mode never yields padding. A more precise `Literal[True]` overload is possible, but I couldn't verify it without mypy.
- **Branch:** `orch/windowed-strict`, made from `main` at b5e3886. It hasn't been pushed. To take it: `git merge orch/windowed-strict`.
- **Route and models:** Direct, done entirely in the main Opus session with no subagents. The local cost estimate is about $0.63.