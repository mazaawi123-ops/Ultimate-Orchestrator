Both changes are in and an independent check found no bugs. `npm test` passes 23 of 23 tests, and the checker's own script passes 53,596 of 53,596 assertions. Nothing is committed, since you didn't ask for a commit.

**What changed**
- **`truncate(text, max, ellipsis = "…")`** is new, in `src/truncate.js`, and is exported from `src/index.js`. The result is never longer than `max` characters, ellipsis included. It counts characters as Unicode code points, so a surrogate pair (such as an emoji) is never split. Text that already fits comes back unchanged. If the ellipsis alone is longer than `max`, the ellipsis itself is cut to `max`.
- **`wrap()`** now splits any word longer than `width` into `width`-sized pieces, so no line is ever longer than `width`. Its width is also counted in code points and it never splits a surrogate pair. For ordinary (non-emoji) text where every word fits, the output is the same as before.
- **Tests:** `test/truncate.test.js` is new with 11 tests, and `test/wrap.test.js` went from 1 test to 10. Both use Node's built-in runner.
- **README:** it now describes all three functions.

**How it ran**
1. I wrote the plan and the decisions below.
2. Two workers built `truncate` and the `wrap` fix in parallel, on separate files.
3. A fresh agent that hadn't written any code checked the result.
   - It ran 6,000 random inputs through each function, including emoji and accented letters.
   - It compared the new `wrap` against the original on ordinary text.
   - It deliberately broke copies of the code in six ways to make sure its checks would notice; they caught all six.
4. I fixed two small things it pointed out: the two error messages now use the same wording, and the README had two gaps.

**Decisions I made without you** (all recorded in `.orchestrator/PLAN.md`)
- **Behaviour change:** `wrap` now throws `RangeError` unless `width` is a whole number of at least 1. Before, `wrap(x, 0)` put one word per line and `wrap(x, Infinity)` gave a single line. With splitting, a width of 0 or less would loop forever.
- **"Character" means a code point**, not what a reader sees as one symbol. Multi-part emoji (like family emoji) and accented letters built from combining marks can still be cut apart. Keeping those whole would need `Intl.Segmenter`.
- **A long word in `wrap` always starts a new line** rather than filling the end of the current one. Other words can then join its last piece: `wrap("a bbbbbbbbbb c", 4)` gives `"a\nbbbb\nbbbb\nbb c"`.
- **`truncate` doesn't trim spaces before the ellipsis**, and `max` must be a whole number of 0 or more, otherwise it throws `RangeError`.

Everything is in `.orchestrator/`, which your `.gitignore` already excludes:
- PLAN.md
- REPORT.md
- verify/VERDICT.md
- verify/verify.mjs
- verify/output.txt