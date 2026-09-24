## Result: done

`qs.parse` now has a `parseNumbers` option, default false. The Opus verifier and the Sonnet re-check after the fix both passed it, and the tests, lint and README examples all pass.

- **Built:**
  - A value becomes a number only when `Number(v)` is finite and `String(Number(v)) === v`. Keys are never converted.
  - It works in arrays, nested objects, with `comma`, and with repeated keys.
  - A value that isn't `true` or `false` throws a TypeError in the same style as `allowEmptyArrays`.
  - The README has a new section with an example that is actually run and would catch a missed conversion.
  - 48 new tape tests.
- **Acceptance criteria:** 8/8 verified. Both verifiers also compared the output against the original code on tens of thousands of random inputs (zero-heavy in the re-check) and found no differences once fixed.
- **Tests:** `npx tape 'test/**/*.js'` → 1189/1189 pass (1141 before). **Lint:** `npx eslint .` → 0 errors, the same 12 warnings as before. **README examples:** `npx evalmd README.md` → ok. Clean-room: n/a, no external services.
- **Iterations:** one fix round. The verifier found that a value converted to `0` was dropped when it joined an existing key: `a[]=1&a=0` gave `{a:[1]}`. The cause was `if (!source) return target` in `lib/utils.js` `merge`, which was written when values were always strings. I made the fix apply only when `parseNumbers` is on, so default behaviour stays exactly as before. The same round made the README example use `assert.deepStrictEqual`, because the loose `deepEqual` couldn't tell `'1'` from `1`. It also moved the tests into their own top-level block and added edge-case tests.
- **Rulings I made:**
  - Following your round-trip rule literally, `'1e+21'` and `'5e-7'` do convert, while `'1e3'` stays a string.
  - `'-0'` stays a string.
  - Values are checked after percent-decoding, so `%31` becomes `1`.
  - `null` values (from `strictNullHandling`) and values in object input aren't converted.
  - A custom decoder that returns an array has each element converted.
  - With the option on, object input holding a real `0` now keeps it where it used to be dropped. Without the option nothing changes.
  - I didn't touch `CHANGELOG.md` or the `dist/qs.js` build file.
- **Open items:** only one cosmetic problem. The first commit's attribution lines ended up on the subject line. Fixing that means rewriting history, so I left it for you.
- **Not verified:** none.
- **Branch:** `orch/parse-numbers` from `main` at `07b1d4d`, 2 commits. Not pushed. To take it: `git merge orch/parse-numbers`
- **Mode:** Lite. One Haiku worker, one Opus verifier, one Sonnet fix worker and one Sonnet re-check. The estimate I gave was about $2.5–3.

As you asked, I kept the plan, notes, worker reports and final report in the git-ignored `.orchestrator/` folder: `plan.md`, `notes.md` and `report.md`.