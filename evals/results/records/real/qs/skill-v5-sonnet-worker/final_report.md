## Result: done

`qs.parse(str, { parseNumbers: true })` now turns a value into a number when `Number(v)` is finite and `String(Number(v)) === v`. The default is `false`. It's on branch `orch/parse-numbers` in two commits. The test suite and lint are green, and an independent verifier checked it.

- **Built:**
  - **Conversion (`lib/parse.js`):** it happens once, in `parseValues`, after percent-decoding and entity interpretation. It runs on every value, including each piece of a `comma`-split value, so it applies inside arrays, nested objects and repeated keys. Keys are never converted. `NaN` and `Infinity` pass the round-trip test, so they are excluded with a separate finiteness check.
  - **Validation:** `parseNumbers` is checked like `allowEmptyArrays`. Anything other than `true`, `false` or `undefined` throws a `TypeError`.
  - **Bug fix (`lib/utils.js`):** a value of `0` is now kept when it merges into a key that already exists. Before, it was silently dropped.
  - **README:** documents the option with an example that includes a value staying a string (`'01'`). 49 new tape tests.
- **Acceptance criteria:** 9/9 verified. They cover all your examples. '01', '1e3', '0x10', '', 'NaN', 'Infinity', '1.50' and '9007199254740993' stay strings, and so do '-0', '+1', '.5', '1.' and ' 1'. Keys are left alone, `comma` works, and a wrong option type throws.
- **Tests:** `npx tape 'test/**/*.js'` → 1190/1190 pass (1141 before the change). No existing test was edited. **Lint:** `npx eslint .` → 0 errors, with the same 12 warnings that were there before. The README examples also pass their check (`npx evalmd README.md`). **Clean-room:** not needed, since nothing calls an external service.
- **Iterations:** the first verification failed on one blocker. `utils.merge` starts with `if (!source) return target`, which never mattered while values were always strings. Once `'0'` becomes the number `0`, a later key merging into the same place lost it: `a[]=5&a=0` gave `[5]` instead of `[5, 0]`. Fix round 1 (Sonnet) added a narrow guard and fixed the README wording. The re-check passed: 16,590 random queries across many option combinations matched the old output with only the number conversion applied, and nothing was dropped.
- **Rulings I made:**
  - I applied your rule literally. So '1e-7' and '1e+21' **do** convert, because JavaScript prints those numbers exactly that way. '1e3' still stays a string.
  - When you pass an object to `qs.parse` instead of a string, its values aren't converted. That input path skips decoding too. The README says so.
  - The `0` fix only takes effect when `parseNumbers` is on, so behaviour with the option off is exactly as before.
  - The error message matches the other boolean options: `` `parseNumbers` option can only be `true` or `false`, when provided ``.
  - I left `dist/qs.js` and `CHANGELOG.md` alone, since they're updated at release time.
- **Open items:** one side effect of the `0` fix, which I accepted rather than fixed. With `parseNumbers: true` and **object** input, a numeric `0` that collides with another key is now kept instead of dropped. For example, `qs.parse({'a[b]':'1', a:0}, {parseNumbers:true})` now gives `{a:[{b:'1'},0]}`, where it used to give `{a:{b:'1'}}`. Without the option, nothing changes. Keeping the value seemed better than losing it, and changing it would mean passing extra information into `utils.merge`.
- **Not verified:** very old Node versions. The package claims to support Node ≥0.6, but only Node 22 was available here. The verifier read the new code and found no syntax newer than ES5.
- **Branch:** `orch/parse-numbers` from `main` at `07b1d4d`. Not pushed. To take it: `git merge orch/parse-numbers`
- **Mode:** Lite, planned on Opus. Agents: two Sonnet workers (the build and one fix round), one Opus verifier, one Sonnet re-checker. I estimated about $2.5–3 up front; the fix round added roughly $0.5 to that.

The plan (criteria, rulings and log), the repo notes, the worker reports and a short report are kept in `.orchestrator/`, which is git-ignored.