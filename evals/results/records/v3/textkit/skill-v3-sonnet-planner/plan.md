# Goal
Add `truncate(text, max, ellipsis='…')` to textkit (exported from `src/index.js`), which cuts
a string to at most `max` characters *including the ellipsis*, and never splits a UTF-16
surrogate pair. Separately, fix `wrap()` in `src/wrap.js` so a word longer than `width` is
hard-broken across lines instead of being dropped onto its own (overflowing) line — no output
line may ever exceed `width` characters. Both need `node --test` tests.

# Baseline
- branch: orch/textkit-truncate-wrap, from main (no uncommitted work)
- BASE: 6ea27ab865b897684776452e2290b953378ec443
- tests at BASE: `npm test` → 3 passed, 0 failed; pre-existing failures: none
- lint at BASE: no lint script configured — n/a
- clean-room test command: n/a — no external services, no .env, no secrets anywhere in this repo
- repo notes: .orchestrator/notes.md (pasted into every brief)
- estimate given to the user: 2 haiku workers in parallel (~$0.10–0.35 each) + 1 opus verifier
  (~$0.20–0.40) ≈ $0.50–1.10 total, mostly off the planner's (Opus) budget

# Acceptance criteria
- AC1: `truncate(text, max, ellipsis)` is exported from `src/index.js` and from `src/truncate.js`.
- AC2: `Array.from(truncate(text, max, ellipsis)).length <= max` for every case (result never
  exceeds `max` *code points*, ellipsis included).
- AC3: if `Array.from(text).length <= max`, `truncate` returns `text` unchanged (no-op, no
  ellipsis appended).
- AC4: `truncate` never splits a surrogate pair — the result string, re-encoded, contains only
  whole code points (no lone surrogates). Concretely: `truncate("😀😀😀😀", 3)` (4 astral
  emoji, each 1 code point / 2 UTF-16 units) → `"😀😀…"` (2 emoji + ellipsis = 3 code points),
  and `[..."😀😀…"]` has no lone-surrogate entries.
- AC5: default ellipsis is `'…'` (single char) when the 3rd arg is omitted.
- AC6: `wrap(text, width)`: no line in the output ever has more UTF-16 `.length` > `width`,
  even when a single word is longer than `width`. `wrap("aaaaaaaaaa", 5)` →
  `"aaaaa\naaaaa"`. `wrap("hi aaaaaaaaaa bye", 5)` → `"hi\naaaaa\naaaaa\nbye"`.
- AC7: `wrap`'s existing behaviour for words that fit is unchanged: `wrap("aaa bbb ccc ddd", 7)`
  still → `"aaa bbb\nccc ddd"` (this is the existing test, must still pass).
- AC8: `npm test` (full suite: `node --test test/*.test.js`) passes, 0 failures.

# Stop-and-ask items
none — both changes are additive/local, no irreversible or external-facing actions.

# Review focus
- truncate: `max <= 0`; `max` smaller than the ellipsis's own code-point length (ellipsis
  itself must then be truncated so the result still never exceeds `max`); empty string input;
  `text` exactly `max` chars (no-op boundary); custom multi-char `ellipsis`; non-string input
  (numbers) via `String(text)` coercion, matching existing style (slug.js does this).
- wrap: a long word at the very start of the text; a long word in the middle; a long word
  exactly a multiple of `width`; a long word whose length leaves a remainder that then gets
  joined with the next short word; `width` itself very small (e.g. 1); empty string input;
  existing all-short-words test must still pass unchanged.

# Constraints
- No new dependencies (zero-dep lib stays zero-dep).
- Match existing style: plain function, `String(input)` coercion, no classes (see src/slug.js,
  src/wrap.js).
- `truncate`'s `max` and the surrogate-safety guarantee are both defined in terms of Unicode
  *code points* (via `Array.from(str)` / the string's iterator, which is surrogate-pair
  aware), not raw `.length` (UTF-16 code units) — see Ruling below.

# Rulings
- Ruling: `truncate`'s `max` counts Unicode code points (`Array.from(str).length`), not
  UTF-16 `.length` — this is what makes "at most max characters" and "never split a surrogate
  pair" simultaneously satisfiable; a `.length`/`.slice()`-based cut can't guarantee both at
  once. Cost if wrong: a caller expecting UTF-16-unit counting sees a shorter-than-expected
  result for astral text — acceptable, since the spec explicitly calls out surrogate-pair
  safety, which only makes sense under code-point counting.
- Ruling: if `ellipsis`'s own code-point length is `>= max`, `truncate` returns just the first
  `max` code points of `ellipsis` itself (no separate truncated-text part) — this is the only
  way to keep the "at most max, ever" guarantee when max is too small to fit any real text
  plus the full ellipsis. Cost if wrong: an unusual small-max case returns something other
  than what a caller guessed; still never exceeds `max`.
- Ruling: `max <= 0` (or non-positive) returns `""`. Cost if wrong: same as above, edge case
  only.
- Ruling: `wrap`'s hard-break also cuts on code-point boundaries (`Array.from(word)`), not raw
  `.slice()`, for the same surrogate-safety reason, even though the task only named this
  requirement explicitly for `truncate` — keeping both functions consistent costs nothing
  extra here. Cost if wrong: a wide/astral-character word in wrap could split a surrogate
  pair across lines; low likelihood but free to avoid.

# Tasks

## T1 add truncate — tier: haiku — mode: worktree — AC: AC1, AC2, AC3, AC4, AC5, AC8
- Worktree: `.orchestrator/worktrees/T1` (from `orch.sh wt-add T1`)
- Files: `src/truncate.js` (new), `src/index.js` (add one export line), `test/truncate.test.js` (new)
- Depends on: none
- Interfaces:
  - Produces: `export function truncate(text, max, ellipsis = "…")` in `src/truncate.js`,
    re-exported as `export { truncate } from "./truncate.js";` appended to `src/index.js`
    (after the existing `wrap` export line — do not touch the existing two lines in that file)
- Tests allowed to change: none (only adding a new test file)
- Status: pending

## T2 fix wrap hard-break — tier: haiku — mode: worktree — AC: AC6, AC7, AC8
- Worktree: `.orchestrator/worktrees/T2` (from `orch.sh wt-add T2`)
- Files: `src/wrap.js` (modify), `test/wrap.test.js` (extend — keep the existing test)
- Depends on: none
- Interfaces: none consumed/produced beyond the existing `export function wrap(text, width = 80)`
- Tests allowed to change: none may be deleted or weakened; may add new `test(...)` blocks to
  `test/wrap.test.js` alongside the existing one
- Status: pending

# Shared-surface check
| Tasks | Shared file / interface | Resolution |
|---|---|---|
| T1, T2 | none (disjoint files) | fully parallel |

# Log
- start: branch created, baseline captured, notes written.
- dispatched T1 (haiku, worktree) and T2 (haiku, worktree) in parallel.
- T1 DONE (0d7aae7), 10/10 passed, no deviations. T2 DONE (c778952), 6/6 passed, no deviations.
- stray check clean. Merged T1 then T2 into orch/textkit-truncate-wrap: 683d9e2. Full suite 13/13
  passed after merge, no old-test lines deleted. Worktrees finished, reports copied to
  .orchestrator/reports/{T1,T2}/.
- dispatched full verifier (opus) against diff-1.patch.
- Verifier (opus) result: truncate() clean on all 8 AC (ran 20k random probes, no violations).
  wrap() has 2 real findings:
  - BLOCKER: src/wrap.js hard-break decides "is this word too long" via `.length` (UTF-16
    units) but chunks by code-point COUNT, not by cumulative `.length` per chunk — so a chunk
    of `width` code points can have `.length` up to 2x width for astral chars (emoji). E.g.
    `wrap("😀😀😀😀😀",5)` → one line of `.length` 10, violates AC6. Root cause: my own
    algorithm spec in the T2 brief conflated "chunk size in code points" with "chunk size in
    width", which only coincide for BMP/ASCII text. Planning mistake, not the worker's.
  - SHOULD-FIX: `width <= 0` infinite-loops (`rest.slice(0, width)` never shrinks `rest` when
    width <= 0). Old pre-fix code didn't hang on width 0. Regression introduced by the hard-break branch.
  - Nits (not fixing, see Rulings below): `truncate(text, max, null)` bypasses the default
    ellipsis (standard JS default-param semantics — only `undefined` triggers a default, and
    the brief never specified non-string ellipsis handling); `max` of NaN/undefined returns
    `"…"` (also unspecified input); test suite lacked an emoji case for wrap and a width<=0
    case for either function.
- New Ruling: wrap() clamps effective width to `Math.max(1, width)` to avoid the infinite
  loop for width <= 0 — treats non-positive width as 1 rather than throwing, to keep wrap()
  total for all numeric input (matches the "no new dependencies / no thrown surprises" style
  already in the file). Cost if wrong: a caller passing width 0 gets 1-char lines instead of
  an error; low-likelihood misuse.
- New Ruling: wrap()'s hard-break chunker now accumulates code points into a chunk while
  `chunk.length + nextCodePoint.length <= width`, flushing on overflow — this guarantees no
  chunk's `.length` exceeds width UNLESS a single code point's own `.length` already exceeds
  width (e.g. width=1 with one emoji, `.length` 2) — that one case is mathematically
  unavoidable without splitting a surrogate pair, so it's allowed to overflow by construction
  (never more than one lone-surrogate-free code point per line). Cost if wrong: same
  unavoidable edge case either way.
- Dispatching sonnet fix round (round 1) for both findings, in the main tree (parallel phase
  is over, only wrap.js is being touched).
- fix 1 (findings 1+2, round 1, sonnet, commit 6d5b4a1): rewrote wrap()'s hard-break to
  accumulate code points into a chunk while `chunk.length + cp.length <= w`, and clamped
  `w = Math.max(1, width)`. `npm test` → 15/15 passed after fix, no old-test lines deleted.
- scoped re-verify (sonnet): Finding 1 ADDRESSED (astral hard-break now respects .length,
  probed widths 1/2/3/5/10, no lone surrogates, no code points lost). Finding 2 ADDRESSED
  (width 0/-1 return instantly, no hang). All 3 pre-existing wrap regression cases unchanged.
  truncate() edge cases re-skimmed, sane. No new findings.
- DONE. Kept .orchestrator/ and all worktree reports per user instruction (not cleaning up).
