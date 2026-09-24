# Goal
Add keyword-only `strict=False` to more_itertools.windowed(). strict=True: never yield a window that would contain fillvalue padding; on reaching one, raise ValueError (like zip(strict=True)), after yielding all complete windows before it. strict=False: behaviour byte-identical to today. Update .pyi stub, docstring (with doctest), add tests.

# Baseline
- branch: orch/windowed-strict, from the user's branch (clean tree)
- BASE: b5e3886a37209bb880f17d82fbf4ba00ece0e41e
- tests at BASE: python3 -m unittest -q → 930 OK; pre-existing failures: none
- lint at BASE: ruff format --check . ; ruff check more_itertools tests ; python3 -m mypy.stubtest more_itertools.more more_itertools.recipes → all clean
- clean-room: n/a: no external services
- repo notes: .orchestrator/notes.md
- estimate given to the user: ~$2.5–3 (Opus planner, 1 Sonnet worker, Opus verifier; + ~$0.5 per fix round)

# Acceptance criteria
- AC1: signature is windowed(seq, n, fillvalue=None, step=1, *, strict=False); strict=False output is unchanged for all inputs (existing WindowedTests pass untouched).
- AC2: strict=True raises ValueError exactly when the non-strict call would yield a window containing padding, after yielding every earlier (complete) window; otherwise output equals non-strict output. Examples:
  - list(windowed([1,2,3,4,5], 3, strict=True)) → [(1,2,3),(2,3,4),(3,4,5)]
  - windowed([1,2,3], 4, strict=True) → ValueError on first next(), nothing yielded
  - windowed([], 3, strict=True) → [] (no error)
  - windowed([1..6], 3, step=2, strict=True) → yields (1,2,3),(3,4,5) then ValueError
  - windowed([1..7], 3, step=2, strict=True) → [(1,2,3),(3,4,5),(5,6,7)] no error
  - windowed([1..6], 3, step=3, strict=True) → [(1,2,3),(4,5,6)] no error
  - windowed([1..7], 3, step=3, strict=True) → (1,2,3),(4,5,6) then ValueError
  - windowed([1..8], 3, step=4, strict=True) → [(1,2,3),(5,6,7)] no error (item 8 falls in the step gap; non-strict yields no padded window either)
  - windowed([1..9], 3, step=4, strict=True) → (1,2,3),(5,6,7) then ValueError
  - windowed([None,None,None], 2, strict=True) → [(None,None),(None,None)] no error (data equal to fillvalue is not padding)
- AC3: more.pyi overloads accept strict: bool keyword; stubtest clean; ruff format/check clean.
- AC4: docstring documents strict with a doctest showing the ValueError; new tests in WindowedTests cover AC2 examples; python3 -m unittest -q passes.

# Stop-and-ask items
- none

# Review focus
- data values equal to fillvalue (None default, or custom) must not be mistaken for padding
- step > n with leftover items inside the gap (no window) vs. reaching a new window start
- step == n, step == 1, n == 1, len(seq) == n, len(seq) < n, empty seq
- laziness: complete windows are yielded before the error; works with one-shot iterators/generators; no extra items consumed beyond what non-strict consumes before the error point
- strict=False path unchanged (incl. performance-sensitive map/deque trick)

# Constraints
- no new dependencies; keep strict=False code path behaviour identical

# Rulings
- Ruling: strict is keyword-only — request says "keyword argument"; matches zip(strict=) and step/fillvalue positional order stays intact — cost if wrong: positional use rejected, trivially loosened later.
- Ruling: empty input with strict=True yields nothing, no error — no window would be padded (non-strict also yields nothing) — cost if wrong: one-line change.
- Ruling: items lying in a step gap (step > n) with no further window start are not an error — spec is about padded windows only, and non-strict yields no padded window there — cost if wrong: users expecting "all items covered" semantics get silent drop (same as today's non-strict).
- Ruling: error message 'not enough items in seq to fill the window'; ValueError (not a subclass) — mirrors zip's ValueError — cost if wrong: message tweak.
- Ruling: strict is not type-validated (truthiness used) — matches zip — cost if wrong: none significant.
- Ruling: no docs/versions.rst changelog entry — changelog entries are written at release time — cost if wrong: maintainer adds a line.

# Tasks
## T1 windowed strict — tier: sonnet — sequential — AC1–AC4
- Worktree: main tree
- Files: more_itertools/more.py, more_itertools/more.pyi, tests/test_more.py
- Depends on: none
- Interfaces: Produces windowed(seq, n, fillvalue=None, step=1, *, strict=False)
- Tests allowed to change: none (add new ones only)
- Status: dispatched

# Shared-surface check
| n/a (one task) | | |

# Log
- T1 DONE (039c7cd) sonnet, 946 passed, lint clean
- iter 1 verify (opus): PASS all AC. Findings: should-fix strict path buffers `step` items (list(islice)) → O(step) memory (368MB at step=5e6); nits: step=1 strict 2.4x slower, doctest doesn't show windows-before-error, stub could narrow with Literal[True]; ruling challenged (gap items dropped).
- Ruling kept: gap items not an error — request wording is about padded windows only; non-strict drops interior gap items by design. Logged.
- Ruling: stub Literal[True] narrowing not done — nit, extra overloads add stub complexity; left as open item.
- fix 1 (round 1, sonnet): memory fix (append items one at a time to the deque, count them) + doctest showing prefix windows.
- fix 1 DONE (ed58b95), 947 passed, lint clean
- recheck 1 (sonnet): PASS. Finding 1 ADDRESSED (peak 0.002MB vs 367.9MB), finding 2 ADDRESSED; 1575-case sweep incl. consumption counts: 0 mismatches; new memory test fails on 039c7cd, passes on ed58b95. step=1 strict ~2.2x slower remains (nit, open).
- DONE. .orchestrator/ kept at user's request (no cleanup).
