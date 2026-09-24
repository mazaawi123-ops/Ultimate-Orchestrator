`truncate()` is added and exported from `src/index.js`, and `wrap()` now splits long words so no line is longer than `width`. The work is on a new branch, `orch/truncate-wrap`, off `main`; nothing is pushed.

- **Tests:** `npm test` → 51 pass, 0 fail (3 before). The syntax check (`node --check` on every file) is clean. The 3 original tests are unchanged, and no dependencies were added.
- **Verification:** an Opus verifier that saw only the diff and the criteria checked all 7 criteria, including 100k random inputs each for `truncate` and `wrap`.

## What changed
- **`truncate(text, max, ellipsis = "…")`** (new `src/truncate.js`):
  - The result is at most `max` characters, ellipsis included, and never splits a surrogate pair (an emoji won't be cut in half).
  - Text that already fits comes back unchanged.
  - Example: `truncate("a😀b😀c", 4)` → `"a😀b…"`.
- **`wrap()`** (`src/wrap.js`):
  - A word longer than `width` starts a new line and is cut into `width`-sized pieces.
  - The next word can share a line with the last piece: `wrap("abcdef g", 4)` → `"abcd\nef g"`.
- **Tests:** new tests are in `test/truncate.test.js`, and `test/wrap.test.js` only has tests appended.

## How it ran
- Two Haiku workers built the two parts in parallel, each in its own copy of the repo. Neither wrote outside its copy.
- The verifier found one real bug: `wrap` crashed with a stack overflow on a single word of about 125,000+ characters when `width` was at least that long. The old `wrap` handled that input.
- The cause was a detail my brief didn't cover (spreading a very long array into `push(...)`). A Sonnet worker replaced it with a loop and added tests that fail on the old code.
- A second check passed, and found the output unchanged from before the fix on 20,000 random inputs.

## Decisions I made without you
- **"Character" means Unicode code point** in both functions. Multi-part emoji like 👨‍👩‍👧 or accented letters built from two code points can still be cut in the middle; you only named surrogate pairs.
- **When `max` is smaller than the ellipsis**, `truncate` returns plain text with no ellipsis: `truncate("hello", 2, "...")` → `"he"`, not `".."`.
- **Invalid `max` or `width` now throws a `RangeError`.** This is a behaviour change for `wrap`: callers who passed 0, 7.5 or `Infinity` used to get output and now get an error. Hard-breaking at width 0 would otherwise loop forever.
- **`wrap` still turns all whitespace, newlines included, into single spaces**, as before.
- **The workers ran in parallel** even though the tasks were small, because you asked for it and they shared no files.

Five agents ran: 2 Haiku workers, 1 Opus verifier, 1 Sonnet fix and 1 Sonnet re-check. Together they used about 223k tokens, within my 300–400k estimate; my own planning tokens aren't counted.

To take the branch: `git merge orch/truncate-wrap`

The plan, notes and full report are kept in `.orchestrator/` (git-ignored), along with each worker's report and the diffs:
- `.orchestrator/plan.md`
- `.orchestrator/notes.md`
- `.orchestrator/report.md`