`qs.parse` now takes a `parseNumbers` option, and all the checks pass: `npx tape 'test/**/*.js'` passes 1237 of 1237, and `npx eslint .` has 0 errors. The 12 lint warnings were all there before. The README examples also run cleanly under `evalmd`, which `npm test` runs first. A separate agent that didn't write the code reviewed it, and I reran the checks myself after its fixes. Nothing is committed.

**How it behaves:** with the option on, `'1'`, `'-2'`, `'1.5'` and `'0'` become numbers. `'01'`, `'1e3'`, `'0x10'`, `''`, `'NaN'`, `'Infinity'`, `'1.50'` and `'9007199254740993'` stay strings. Keys are never converted. It works in arrays, nested objects and with `comma` (`a=1,02,3.5` gives `[1, '02', 3.5]`). A non-boolean value throws a `TypeError`, as the other boolean options do.

**Changes:**
- `lib/parse.js`: the option, a small `parseNumber` helper, the conversion step and the validation.
- `lib/utils.js`: one line, explained below.
- `test/parse.js` and `test/utils.js`: the new tests.
- `README.md`: the rule and examples, in the "Parsing primitive/scalar values" section.

**Decisions I made:**
- **Extra check for `NaN` and `Infinity`.** Your rule `String(Number(v)) === v` alone would convert `'NaN'`, `'Infinity'` and `'-Infinity'`, because they come back unchanged. Since you said "finite", I added an `isFinite` check.
- **Change to `utils.merge`.** Without it, a numeric `0` was silently lost when merged into an existing key: `a[b]=1&a=0` dropped the `0`. It now merges the way `'0'` and `1` already do. This also changes one thing for callers who don't use the option: object input with a numeric `0`, like `qs.parse({ 'a[b]': 'x', a: 0 })`, now keeps the `0` (`{ a: [{ b: 'x' }, 0] }` instead of `{ a: { b: 'x' } }`). It has tests, but it's worth mentioning in the PR or changelog.
- **Strict rule.** Because the rule is exactly the round-trip, `'1e+21'`, `'1e-7'` and `'123456789012345680000'` convert, while `'-0'` and `'.5'` stay strings. The README says this.
- **What isn't converted.** The `null` from `strictNullHandling`, non-strings returned by a custom decoder, and object input (`qs.parse({ a: '1' }, …)`) are left unchanged.
- **Files left alone.** I didn't touch `dist/` (the release build) or `CHANGELOG.md`.

One side effect: the review agent's coverage runs deleted the repo's gitignored `.nyc_output` and `coverage` folders. `npm test` recreates them.

The plan, the review findings and the report are kept in the scratchpad. The review agent's probe scripts are in `verify/` beside them.

Files are in the scratchpad:
- PLAN.md
- VERIFICATION.md
- REPORT.md