# Goal
Add `truncate(text, max, ellipsis = "…")` to textkit: result is at most `max` characters
including the ellipsis, never splits a surrogate pair, exported from src/index.js. Fix
`wrap()` so words longer than `width` are hard-broken and no line ever exceeds `width`.
Tests with node:test. Done = both behaviours tested, full suite green, independently verified.

# Baseline
- branch: orch/textkit-truncate-wrap, from main (uncommitted work: none)
- BASE: 6ea27ab865b897684776452e2290b953378ec443
- tests at BASE: `npm test` → 3 pass, 0 fail; pre-existing failures: none
- lint at BASE: no linter; syntax check `for f in src/*.js test/*.js; do node --check "$f" || exit 1; done` (loop covers every file)
- clean-room test command: n/a: no external services
- repo notes: .orchestrator/notes.md
- estimate given to the user: 2 Haiku workers + 1 Opus verifier, ~$1.5–2.5 total, mostly planner (Opus)

# Acceptance criteria
- AC1: `import { truncate } from "./src/index.js"` works; `truncate(s, max, e)` returns `s` unchanged when `s.length <= max`, otherwise a string of `.length <= max` ending in the ellipsis (when the ellipsis fits). Examples in T1 all hold.
- AC2: truncate never leaves a lone high surrogate at the cut: `truncate("ab😀cd", 4) === "ab…"`, `truncate("😀😀😀", 4) === "😀…"`.
- AC3: truncate throws RangeError for max that is negative, non-integer, NaN or missing.
- AC4: `wrap()` hard-breaks words longer than width: for all inputs in T2 examples, output matches, and every line has `.length <= width` (sole exception: width 1 with an astral char, see Rulings).
- AC5: wrap hard-break never splits a surrogate pair; wrap throws RangeError for width < 1 / non-integer / NaN.
- AC6: existing tests unchanged and passing; `npm test` passes with new tests in test/truncate.test.js and test/wrap.test.js; node --check passes for all files.

# Stop-and-ask items
- none

# Review focus
- surrogate pair exactly at the cut (truncate and wrap); astral ellipsis; lone surrogates in input
- max === text.length, max === ellipsis.length, max < ellipsis.length, max 0, empty text, empty ellipsis
- word exactly width; word of width+1; very long word; long word following a partial line; remainder of a long word joined with the next word
- width 1; width 0 / invalid (must not infinite-loop)
- non-string input (numbers) coerced via String()

# Constraints
- No new deps (zero-dep lib). Existing test "wraps at width" must not change. Existing wrap
  whitespace semantics (split on /\s+/, collapse) unchanged.

# Rulings
- Ruling: "characters" = UTF-16 code units (JS `.length`), so `truncate(s,m).length <= m` and `wrap` lines `.length <= width` — matches how wrap already measures, and makes the surrogate-pair clause meaningful — cost if wrong: switch to code-point counting (small change in both functions).
- Ruling: only surrogate pairs are protected; grapheme clusters (ZWJ emoji, combining marks) may be split — the request names surrogate pairs only; grapheme segmentation needs Intl.Segmenter and changes counting — cost if wrong: family emoji etc. may be split mid-cluster.
- Ruling: when the cut would split a pair, keep one fewer code unit (result may be shorter than max) — never exceed max — cost if wrong: none significant.
- Ruling: if text fits (`s.length <= max`) return it unchanged, no ellipsis.
- Ruling: if `ellipsis.length > max`, return the text cut to `max` with NO ellipsis (e.g. `truncate("hello", 2, "...") === "he"`) — the "at most max" guarantee wins over always showing the ellipsis — cost if wrong: caller sees no truncation marker in that degenerate case.
- Ruling: `max` must be a non-negative integer, else `RangeError("max must be a non-negative integer")`; no default for max. text and ellipsis coerced with String().
- Ruling: truncate is a plain cut: no word-boundary logic, no trimming whitespace before the ellipsis — not requested.
- Ruling: wrap: a word longer than width always starts on a new line (current line flushed first), is cut into width-sized chunks, and its last (shorter or equal) chunk becomes the current line, which later words may join — simplest greedy rule — cost if wrong: slightly less dense output than filling the current line's remainder.
- Ruling: wrap hard-break also avoids splitting surrogate pairs (chunk one unit shorter); with width 1 an astral char can't fit, so it is emitted alone on its own line (length 2) — the only case a line exceeds width — consistent with truncate; alternative (splitting) produces garbage strings.
- Ruling: wrap width must be a positive integer, else `RangeError("width must be a positive integer")` — width 0 can't be satisfied and would loop forever with hard-breaking; previously width 0 put each word on its own line — cost if wrong: callers passing 0/Infinity now get an exception.
- Ruling: no shared surrogate helper module — keeps T1/T2 file-disjoint so they run in parallel; duplication is ~1 line.
- Ruling: Full mode with 2 parallel Haiku workers — user asked for parallel where possible; tasks are file-disjoint; though small, parallelism was explicitly requested.

# Tasks
## T1 truncate — tier: haiku — mode: worktree — AC: AC1, AC2, AC3, AC6
- Worktree: .orchestrator/worktrees/T1
- Files: src/truncate.js (new), src/index.js, test/truncate.test.js (new)
- Depends on: none
- Interfaces: Produces `export function truncate(text, max, ellipsis = "…")` in src/truncate.js, re-exported from src/index.js
- Tests allowed to change: none
- Status: pending

## T2 wrap hard-break — tier: haiku — mode: worktree — AC: AC4, AC5, AC6
- Worktree: .orchestrator/worktrees/T2
- Files: src/wrap.js, test/wrap.test.js (append only)
- Depends on: none
- Interfaces: `wrap(text, width = 80)` signature unchanged
- Tests allowed to change: none (append new tests only)
- Status: pending

# Shared-surface check
| Tasks | Shared file / interface | Resolution |
|---|---|---|
| T1, T2 | none (index.js only touched by T1) | parallel |

# Log
- stamp + worktrees T1, T2 created; dispatching 2 haiku workers in parallel
- T1 DONE (ae6a47c), merged; npm test 24 pass
- T2 DONE (91c02e1), merged. Stray: T2 wrote its report to main-tree .orchestrator/task-2-report/ (git-ignored, no source edits outside worktree); moved to reports/T2. Full suite green after both merges
- verify 1 (opus, full): PASS, AC1–AC6 all PASS; 200k/300k randomized checks clean; mutant (surrogate back-off removed) → 8 tests fail. Nits: (a) wrap property test checks NFC normalization, not isWellFormed — doesn't catch lone surrogates; (b) wrap.js doc comment sits above helpers not wrap(); (c) T1 commit message lacks blank line before trailers; (d) wrap now throws for "3"/null widths.
- Rulings on findings: (a)+(b) fix round 1 (sonnet) — test asserts something it doesn't check; cheap. (c) left: fixing needs history rewrite, cosmetic. (d) accepted under the width ruling; cost-if-wrong extended to numeric strings/null.
- fix 1 (findings a+b, round 1, sonnet): cd11f5c — property test now asserts isWellFormed (mutant w/o back-off fails it); comment moved above wrap(). npm test 41 pass
- scoped re-verify (sonnet): PASS — both findings ADDRESSED (mutant reproduced), AC4–AC6 hold, no new breakage. Run complete.
