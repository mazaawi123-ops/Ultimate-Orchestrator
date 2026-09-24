# Goal
Add a `parseNumbers` boolean option (default false) to `qs.parse`. When true, each parsed *value* (never keys) that is a string in canonical finite decimal form — `isFinite(Number(v)) && String(Number(v)) === v` — becomes a number. Must work for plain values, array elements, nested objects, duplicate-key combining and `comma: true`. Invalid option types throw TypeError like other boolean options. Documented in README, tested with tape; tests + eslint stay green.

# Baseline
- branch: orch/parse-numbers, from main (no uncommitted work)
- BASE: 07b1d4d82c8f9301c105ea4b94fa2302cfd6e8b4
- tests at BASE: `npx tape 'test/**/*.js'` → 1141/1141 pass; pre-existing failures: none
- lint at BASE: `npx eslint .` → 0 errors, 12 warnings (pre-existing)
- clean-room: n/a: no external services
- repo notes: .orchestrator/notes.md
- estimate given to the user: 1 Sonnet worker + 1 Opus verifier (+ Opus planner) ≈ $2.5–3.

# Acceptance criteria
- AC1: `qs.parse('a=1&b=-2&c=1.5&d=0', {parseNumbers:true})` → `{a:1,b:-2,c:1.5,d:0}` (numbers, strict-equal).
- AC2: with parseNumbers:true these values stay strings: '01', '1e3', '0x10', '', 'NaN', 'Infinity', '-Infinity', '1.50', '9007199254740993', ' 1', '+1', '-0', '.5', '1.', 'abc'.
- AC3: default (option omitted or false) output is unchanged: `qs.parse('a=1')` → `{a:'1'}`; full existing suite passes untouched.
- AC4: keys are never converted: `qs.parse('1=1', {parseNumbers:true})` → `{'1':1}` (key string '1'); `qs.parse('a[0]=1&a[1]=x', {parseNumbers:true})` → `{a:[1,'x']}`.
- AC5: arrays/nested/duplicates/comma: `a[]=1&a[]=2` → `{a:[1,2]}`; `a[b][c]=3` → `{a:{b:{c:3}}}`; `a=1&a=2` → `{a:[1,2]}`; with `comma:true`, `a=1,2,x` → `{a:[1,2,'x']}` and `a[]=1,2` → same shape as today but numbers.
- AC6: percent-encoded values are converted after decoding: `a=%2D5` → `{a:-5}`; `a=1%2E5` → `{a:1.5}`.
- AC7: `parseNumbers` of a non-boolean (e.g. 'true', 1, null, {}) throws TypeError; `undefined` is allowed.
- AC8: README documents `parseNumbers` with an example (including a stays-a-string example).
- AC9: `npx tape 'test/**/*.js'` all pass with new tests for AC1–AC7; `npx eslint .` 0 errors.

# Stop-and-ask items
- none

# Review focus
- NaN/Infinity pass `String(Number(v)) === v` — finiteness must be checked separately.
- '-0' → Number is -0, String(-0) is '0' → stays string.
- strictNullHandling: `a` (no '=') → null must stay null; `a=` → '' stays ''.
- allowEmptyArrays + `foo[]=` must still yield [] / behave as before ('' not converted).
- custom decoder returning non-strings: only convert typeof 'string'.
- charset iso-8859-1 + interpretNumericEntities: `a=%26%2349%3B` ('&#49;' → '1') → conversion after entity interpretation.
- Object input (`qs.parse({a:'1'}, {parseNumbers:true})`).
- comma with arrayLimit overflow / throwOnLimitExceeded paths unaffected.
- parseArrays:false, allowSparse, duplicates first/last.

# Constraints
- ES5 only (repo supports very old node). No new deps. Don't touch dist/, CHANGELOG.md, stringify.
- Existing tests are fixed points; none may change.

# Rulings
- Ruling: the conversion rule is exactly `typeof v === 'string' && isFinite(Number(v)) && String(Number(v)) === v` (use a Number-based finiteness check, e.g. `var n = Number(v); n === n && n !== Infinity && n !== -Infinity`, or global isFinite on the number) — it is the user's stated definition — cost if wrong: canonical JS exponent strings such as '1e-7' and '1e+21' DO convert, since String(Number) round-trips them; user's '1e3' example still stays a string.
- Ruling: convert in parseValues after decoding and after interpretNumericEntities, via utils.maybeMap on the value, so comma arrays, duplicates and nested keys all see numbers — single choke point — cost if wrong: none expected.
- Ruling: object input (non-string `str`) is NOT converted, matching how decoder/other value options only apply to string parsing — cost if wrong: users passing pre-parsed objects get strings; easy to extend.
- Ruling: validation message: '`parseNumbers` option can only be `true` or `false`, when provided' (same as allowEmptyArrays) — consistency.
- Ruling: don't rebuild dist/qs.js or edit CHANGELOG — release artefacts owned by maintainers.

# Tasks
## T1 parseNumbers option — tier: sonnet — sequential — AC: AC1–AC9
- Worktree: main tree
- Files: lib/parse.js, test/parse.js, README.md
- Depends on: none
- Interfaces: Produces option `parseNumbers` (boolean, default false) in `defaults` and normalizeParseOptions output.
- Tests allowed to change: none (only add new tests)
- Status: pending

# Shared-surface check
| n/a (single task) | | |

# Log
- T1 DONE (2235917), 1179 passed, lint 0 errors
- iter 1 verify (opus): FAIL. All AC1–AC9 pass, but blocker: utils.merge `if (!source) return target` (lib/utils.js:126) drops numeric 0 produced by parseNumbers when merging into an existing key (a[]=5&a=0 → [5]; base gives ['5','0']). Root cause: before this change parsed values were never falsy numbers; brief didn't flag merge/compact falsy checks. Also ruling challenged (object input not converted though comma applies to object input), nit README wording.
- Ruling (fix 1): guard the merge fix on options.parseNumbers — `if (!source && !(source === 0 && options && options.parseNumbers))` — keeps default behaviour byte-for-byte (AC3) — cost if wrong: object-input 0 collisions without the option are still dropped, as at BASE.
- Ruling re-decided (object input): KEEP not converting object input — qs.parse(object) is a pass-through for already-structured data and the request is about query-string values; comma touching it is legacy behaviour — but DOCUMENT it in README. Cost if wrong: users must convert pre-parsed objects themselves.
- Ruling: README nits fixed in same round (non-finite wording, state default false, string-input only).
- fix 1 (blocker, round 1, sonnet): c7fa087, 1190 passed, lint 0 errors
- re-check 1 (sonnet rechecker): PASS. Finding 1 & 2 ADDRESSED; 16,590-case differential fuzz vs BASE, 0 failures; 1190/1190, lint 0 errors, evalmd ok.
- Ruling (re-check should-fix, accepted, not fixed): with parseNumbers:true on OBJECT input, a literal numeric 0 that collides with another key is now kept (`qs.parse({'a[b]':'1', a:0}, {parseNumbers:true})` → `{a:[{b:'1'},0]}`; without the option it's still dropped, as at BASE) — keeping data beats dropping it, no value is converted so the README sentence still holds, and scoping the guard to string input means threading provenance into utils.merge — cost if wrong: one niche object-input shape differs only when the option is on.
