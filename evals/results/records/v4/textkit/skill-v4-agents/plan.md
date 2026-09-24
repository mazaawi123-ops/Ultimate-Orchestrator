# Goal
Add `truncate(text, max, ellipsis = "…")` to textkit: result is at most `max` characters (code points) INCLUDING the ellipsis, never splits a surrogate pair, exported from src/index.js. Fix `wrap(text, width)` so words longer than `width` are hard-broken into width-sized chunks, so no output line ever exceeds `width`. Tests use node:test. Done = both behaviours covered by tests, full suite green, verified independently.

# Baseline
- branch: orch/textkit-truncate-wrap, from main (uncommitted work: none)
- BASE: 6ea27ab865b897684776452e2290b953378ec443
- tests at BASE: `npm test` → 3 pass, 0 fail; pre-existing failures: none
- lint at BASE: none configured; substitute `for f in src/*.js test/*.js; do node --check "$f" || exit 1; done` (loop, so every file is checked) → ok
- clean-room test command: n/a: no external services
- repo notes: .orchestrator/notes.md
- estimate given to the user: 2 Haiku workers (parallel) + 1 Opus verifier + Opus planner ≈ $2–2.5; more if a fix round runs (~$0.45 each)

# Acceptance criteria
- AC1: `import { truncate } from "./src/index.js"` works; `truncate` is a named export of src/truncate.js.
- AC2: For any string s and valid max, `Array.from(truncate(s, max, e)).length <= max`; if `Array.from(s).length <= max` the result === s (unchanged). Otherwise result = first (max − len(e)) code points of s + e when len(e) <= max, else the first max code points of s. (len = code-point count.)
- AC3: truncate never yields a lone surrogate from well-formed input: e.g. truncate("a😀b😀c", 3) === "a😀…", truncate("😀😀😀", 2) === "😀…", truncate("a😀b😀c", 5) === "a😀b😀c".
- AC4: truncate throws RangeError when max is not a non-negative integer (−1, 1.5, NaN, Infinity, "5").
- AC5: wrap: no output line has more than `width` code points for any input; words longer than width are split into consecutive width-sized chunks, e.g. wrap("abcdefghij", 4) === "abcd\nefgh\nij"; wrap never splits a surrogate pair.
- AC6: wrap keeps existing behaviour for words that fit (existing test "wraps at width" unchanged and passing); wrap throws RangeError when width is not a positive integer (0, −1, 1.5).
- AC7: `npm test` passes, with new tests for AC1–AC6; the node --check loop passes.

# Stop-and-ask items
- none

# Review focus
- max = 0, max = 1, max < / = / > ellipsis length; empty ellipsis; empty text; text exactly max long
- astral characters (emoji, surrogate pairs) in text, at the cut point, and in the ellipsis; lone surrogates in input
- count by code points vs .length (a 5-code-point / 7-unit string with max 5 must be unchanged)
- wrap: word exactly width long; word of 2×width; long word following a partial line; remainder chunk followed by short words; width 1; astral chars at chunk edges; multiple spaces/newlines in input; empty input
- wrap must not loop forever for any width

# Constraints
- No new dependencies; zero-dep ESM stays.
- Existing tests are fixed points (slug.test.js, "wraps at width").
- wrap keeps its whitespace-collapsing (split on /\s+/) and greedy fill for fitting words.

# Rulings
- Ruling: "characters" = Unicode code points (Array.from), for truncate and for wrap's width — the surrogate-pair requirement implies code-point counting, and wrap should agree — cost if wrong: grapheme clusters (ZWJ emoji, combining marks) can still be split; astral-heavy wrap lines can be up to 2× width in UTF-16 units.
- Ruling: if the text fits (≤ max code points), return it unchanged, no ellipsis — standard truncate semantics — cost if wrong: none expected.
- Ruling: if the ellipsis itself is longer than max, return the first max code points of the text with no ellipsis (e.g. truncate("hello", 2, "...") === "he") — the "at most max" limit is the hard guarantee; a partial ellipsis carries less information than text — cost if wrong: callers see a hard cut with no ellipsis marker at tiny max.
- Ruling: if len(ellipsis) === max and the text doesn't fit, return just the ellipsis (truncate("hello", 3, "...") === "...") — follows the one formula without a special case — cost if wrong: small-max output is all ellipsis.
- Ruling: max must be a non-negative integer (Number.isInteger), else RangeError "max must be a non-negative integer" — silent coercion hides bugs — cost if wrong: callers passing "5" must convert.
- Ruling: text and ellipsis are coerced with String(), matching slugify/wrap — cost if wrong: none.
- Ruling: no whitespace trimming before the ellipsis — not asked for — cost if wrong: "hello …" style output.
- Ruling: wrap width must be a positive integer, else RangeError "width must be a positive integer" — width 0 would loop forever when hard-breaking — cost if wrong: callers passing 0 previously got one word per line; now they get an error.
- Ruling: a word longer than width always starts on a fresh line (not packed onto the tail of the current line); its last chunk becomes the current line, so following short words can join it greedily (wrap("abcdefg hi", 5) === "abcde\nfg hi") — conventional hard-wrap behaviour — cost if wrong: a slightly different line layout.

# Tasks
## T1 truncate — tier: haiku — mode: worktree — AC: AC1, AC2, AC3, AC4, AC7
- Worktree: .orchestrator/worktrees/T1
- Files: src/truncate.js (new), test/truncate.test.js (new), src/index.js (add export line)
- Depends on: none
- Interfaces: Produces `export function truncate(text, max, ellipsis = "…")` in src/truncate.js; src/index.js adds `export { truncate } from "./truncate.js";`
- Tests allowed to change: none
- Status: pending

## T2 wrap hard-break — tier: haiku — mode: worktree — AC: AC5, AC6, AC7
- Worktree: .orchestrator/worktrees/T2
- Files: src/wrap.js, test/wrap.test.js (append tests only)
- Depends on: none
- Interfaces: `export function wrap(text, width = 80)` — signature unchanged
- Tests allowed to change: none (append new tests; "wraps at width" untouched)
- Status: pending

# Shared-surface check
| Tasks | Shared file / interface | Resolution |
|---|---|---|
| T1, T2 | none (T1 alone edits src/index.js) | parallel |

# Log
- stamp + worktrees T1, T2 created
- T1, T2 dispatched in parallel (orch-worker-haiku)
- T1 DONE (15ac1d9), merged; suite green
- STRAY: T2 worker edited/committed in the main tree (7de321c on orch/textkit-truncate-wrap), not its worktree; T1 merged on top (79211b5) before this was noticed. 7de321c touches only src/wrap.js, test/wrap.test.js (disjoint from T1). Awaiting T2 return.
- Ruling: discard stray T2 commit per skill rule (worker left worktree; its report can't be trusted on isolation) — reverted with git revert (no history rewrite) — cost: one extra Haiku run. Re-dispatching T2 sequentially in the main tree.
- T2 redo DONE (23add3f) in main tree; 39/39 pass; diff-1 written
- iter 1: full verifier (orch-verifier) dispatched on diff-1.patch
- iter 1 verifier: FAIL on AC7 (no test imports truncate via src/index.js — deleting the export kept 39/39 green). should-fix: src/wrap.js:17 fit check still uses UTF-16 .length (brief step 2 said len(); T2 worker skipped it and reported no deviations) → wrap("😀 a",3) === "😀\na". nit: long header comment in wrap.js.
- Ruling: wrap's fit check counts code points too (len()) — follows the code-point ruling; AC6's "existing behaviour for fitting words" means ASCII/BMP layout is unchanged (verifier: 0 diffs on ASCII) — cost if wrong: astral-heavy text packs slightly more per line than at BASE.
- fix 1 (both findings + nit, round 1, orch-worker-sonnet) dispatched; FIXBASE=23add3f
- fix 1 DONE (2be5387), 44/44; fix-1.patch + diff-2.patch written; rechecker dispatched
- scoped recheck PASS (fix 1 ADDRESSED x3). DONE. report.md written; .orchestrator/ kept per user.
