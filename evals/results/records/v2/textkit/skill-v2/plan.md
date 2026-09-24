# Goal
Add `truncate(text, max, ellipsis = "…")` to textkit: result is at most `max` characters
including the ellipsis, never splits a surrogate pair, exported from src/index.js. Fix
`wrap()` so words longer than `width` are hard-broken and no output line ever exceeds
`width`. Tests use Node's built-in runner. Done = both behaviours shipped with tests, full
suite green, independently verified.

# Baseline
- branch: orch/truncate-wrap, from main (uncommitted work: none)
- BASE: 6ea27ab865b897684776452e2290b953378ec443
- tests at BASE: `npm test` → 3 pass, 0 fail; pre-existing failures: none
- lint at BASE: `for f in src/*.js test/*.js; do node --check "$f" || exit 1; done` → clean (per-file loop, so it covers every file)
- clean-room test command: n/a: no external services
- repo notes: .orchestrator/notes.md (pasted into every brief)
- estimate given to the user: 2 Haiku workers, 1 Opus verifier, likely 1 Sonnet fix + 1 Sonnet re-check; ~300–400k tokens, ~90k on Opus

# Acceptance criteria
- AC1: `import { truncate } from "./src/index.js"` works, and `truncate` is a function.
- AC2: For any string s and integer max >= 0, `[...truncate(s, max, e)].length <= max` (code points), and if `[...s].length <= max` the result is exactly s.
- AC3: truncate never produces a lone surrogate from a well-formed input: for well-formed s and e, `truncate(s, max, e).isWellFormed()` is true.
- AC4: truncate exact examples (T1 table) all hold, including ellipsis default "…", custom ellipsis, empty ellipsis, max smaller than ellipsis, and RangeError for invalid max.
- AC5: For any text and integer width >= 1, every line of `wrap(text, width)` has `[...line].length <= width`, and no non-whitespace character is lost or reordered (`wrap(t,w).replace(/\s+/g,"") === t.replace(/\s+/g,"")`).
- AC6: wrap exact examples (T2 table) all hold, including the pre-existing test `wraps at width`, and RangeError for invalid width.
- AC7: `npm test` passes with new tests in test/truncate.test.js and test/wrap.test.js; lint loop clean; package.json unchanged (no deps).

# Stop-and-ask items
- none

# Review focus
- astral characters (emoji, 😀 = 2 UTF-16 units) at every cut position, in text and in the ellipsis
- lone surrogates in input
- boundaries: length == max, length == max+1, max == ellipsis length, max < ellipsis length, max 0
- wrap: word length exactly width, exact multiple of width (no empty trailing line), width 1, long word first/middle/last, long word followed by short words
- wrap: empty string, whitespace-only, leading/trailing whitespace, newlines/tabs in input
- invalid width/max: 0, negative, NaN, non-integer, Infinity, string numbers; infinite-loop risk in wrap at width 0
- non-string text (numbers, null) — existing functions coerce with String()
- default parameter: passing `undefined` as ellipsis uses "…"

# Constraints
- No dependencies (zero-dep library is the product's point).
- src/slug.js and its tests unchanged.
- Existing test `wraps at width` in test/wrap.test.js unchanged.
- wrap keeps its whitespace-collapsing behaviour and default width 80.

# Rulings
- Ruling: "characters" means Unicode code points (`Array.from`/spread), in both truncate and wrap — it is what "character" means to a reader, and it makes splitting a surrogate pair impossible by construction — cost if wrong: results measured in UTF-16 units can exceed `max`/`width` when astral chars are present (e.g. truncate("😀😀😀",2) is 3 UTF-16 units).
- Ruling: grapheme clusters (ZWJ emoji, combining marks) are NOT kept together — the request names surrogate pairs only, and Intl.Segmenter handling is a bigger design — cost if wrong: "👨‍👩‍👧" or "é" can be cut mid-cluster.
- Ruling: truncate returns text unchanged when it fits (`[...text].length <= max`), with no ellipsis — standard truncate semantics — cost if wrong: none expected.
- Ruling: when max < ellipsis length, truncate returns the first `max` code points of text with no ellipsis (truncate("hello",2,"...") → "he") — a partial ellipsis like ".." carries no meaning, and the text is more useful — cost if wrong: caller can't see the text was truncated at tiny max.
- Ruling: truncate throws `RangeError("truncate: max must be a non-negative integer")` unless `Number.isInteger(max) && max >= 0` — silent nonsense on NaN/negative is worse than an error — cost if wrong: callers passing "5" or Infinity get an error.
- Ruling: truncate coerces text and ellipsis with String() — matches slugify/wrap convention — cost if wrong: none expected.
- Ruling: wrap: a word longer than width starts on a fresh line (as today) and is cut into width-sized chunks; the last chunk then behaves as a normal word, so following words may join its line — least change from current behaviour — cost if wrong: layout differs from Python-textwrap style (which fills the current line first).
- Ruling: wrap throws `RangeError("wrap: width must be a positive integer")` unless `Number.isInteger(width) && width >= 1` — width 0 with hard-breaking would loop forever, and fractional chunk sizes make no sense — cost if wrong: callers who passed 0, 7.5 or Infinity previously got output and now get an error.

# Tasks
## T1 truncate — tier: haiku — mode: worktree — AC: AC1–AC4, AC7
- Worktree: .orchestrator/worktrees/T1
- Files: src/truncate.js (new), src/index.js, test/truncate.test.js (new)
- Depends on: none
- Interfaces:
  - Consumes: none
  - Produces: `export function truncate(text, max, ellipsis = "…")` in src/truncate.js; `export { truncate } from "./truncate.js";` in src/index.js
- Tests allowed to change: none
- Status: pending

## T2 wrap hard-break — tier: haiku — mode: worktree — AC: AC5, AC6, AC7
- Worktree: .orchestrator/worktrees/T2
- Files: src/wrap.js, test/wrap.test.js (append only)
- Depends on: none
- Interfaces:
  - Consumes: none
  - Produces: `export function wrap(text, width = 80)` — same signature
- Tests allowed to change: none (append new tests only)
- Status: pending

# Shared-surface check
| Tasks | Shared file / interface | Resolution |
|---|---|---|
| T1, T2 | none (T1 alone edits src/index.js) | parallel OK |

Parallel chosen although tasks are small, because the user explicitly asked for parallel delegation where possible and the tasks share no files.

# Log
- iter 1: stamped main tree; T1 and T2 dispatched in parallel (haiku, worktrees .orchestrator/worktrees/T1, T2).
- T1 DONE (f51d686, decisions: none; code matches brief algorithm). T2 DONE (ab6cbb0, decisions: none). stray: OK.
- Merged T1 → 26/26 pass; merged T2 → 46/46 pass. Lint OK. old-tests: OK. package.json unchanged. Worktrees finished; reports in .orchestrator/reports/.
- Full verifier (opus) dispatched on diff-1.patch (HEAD f6806af).
- Verifier: FAIL on AC5 only. AC1–4, 6, 7 PASS (100k random cases each for truncate and wrap).
  - blocker src/wrap.js:44 `line.push(...wCodePoints)` → stack overflow for a word ≥ ~125k code points when width ≥ its length. Regression vs BASE. Root cause: my brief said to keep the line as a code-point array and didn't warn that spreading an unbounded array into call arguments hits V8's argument limit.
  - should-fix: no large-input test. Ruling: fix it in the same round, because it's cheap.
  - nit: no test pins that wrap output is unchanged for inputs without long words. Ruling: add one cheap equivalence test in the same fix round.
- fix 1 (finding: wrap stack overflow, round 1, sonnet): dispatched sequentially in the main tree on orch/truncate-wrap.
- fix 1 DONE_WITH_CONCERNS (36e2d4f). The spread was replaced with a for-of push loop, and 5 tests were added (3 large-input, 1 large long-word, 1 old-vs-new equivalence).
  - Deviations: the commit carries the session's attribution trailer, and 2 words over 5 letters in the equivalence list were swapped out.
  - Ruling: accept both. They are harmless, and the second enforces the brief's own constraint.
  - Planner check: 51/51 pass, lint OK, old-tests OK. The scoped verifier (sonnet) is dispatched on fix-1.patch.
- Scoped re-verify: PASS.
  - Findings 1–3 ADDRESSED. Tests 1–3 fail against pre-fix code and pass after the fix.
  - A 20k-case differential fuzz found pre-fix == post-fix wherever pre-fix didn't throw.
  - No other unbounded spread/apply anywhere in src/.
- DONE. Report in .orchestrator/report.md. Files are kept, as the user asked.
