Both pieces are done and independently verified.

**`truncate(text, max, ellipsis='…')`** — `src/truncate.js`, exported from `index.js`. Counts in Unicode code points (`Array.from`) so surrogate pairs are never split; total length including ellipsis is exactly `max`; handles `max=0` and `max` smaller than the ellipsis length as edge cases.

**`wrap()`** — `src/wrap.js` now hard-breaks any word longer than `width` into `width`-sized chunks before continuing, so no line ever exceeds `width`. Original passing test untouched.

7 new truncate tests + 4 new wrap tests added (`node --test`). `npm test`: **14/14 pass**. I re-ran the suite myself and did extra ad-hoc spot checks (emoji truncation, exact-length boundaries, evenly-divisible long-word wrapping) independent of what each worker tested, all correct.

Plan/notes with the full spec and verification log are kept at `scratchpad/plan.md`.