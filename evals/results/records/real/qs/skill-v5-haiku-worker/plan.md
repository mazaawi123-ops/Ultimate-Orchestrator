# Goal
Add a `parseNumbers` boolean option (default false) to qs.parse. When true, each parsed *value* string v becomes Number(v) iff Number(v) is finite AND String(Number(v)) === v. Keys never change. Must work for plain values, arrays (bracket, indexed, duplicate keys), nested objects and `comma: true`. Validate like other boolean options, document in README, tape tests; tests + eslint stay green.

# Baseline
- branch: orch/parse-numbers from main (clean tree)
- BASE: 07b1d4d82c8f9301c105ea4b94fa2302cfd6e8b4
- tests: `npx tape 'test/**/*.js'` → 1141 pass, 0 fail; pre-existing failures: none
- lint: `npx eslint .` → 0 errors, 12 warnings (pre-existing); `npx evalmd README.md` → ok
- clean-room: n/a (no external services)
- repo notes: .orchestrator/notes.md
- estimate given: Lite — 1 Haiku worker + 1 Opus verifier (+ fix rounds if needed), ~$2.5–3.

# Acceptance criteria
- AC1: `qs.parse('a=1&b=-2&c=1.5&d=0', {parseNumbers:true})` deepEquals `{a:1,b:-2,c:1.5,d:0}` (numbers, typeof 'number').
- AC2: with parseNumbers:true these stay strings: '01','1e3','0x10','','NaN','Infinity','-Infinity','1.50','9007199254740993','-0','+1',' 1','1.','.5','abc','1,5' (comma off).
- AC3: default (option absent or false) output is byte-identical to BASE behaviour: `qs.parse('a=1')` → `{a:'1'}`; full existing suite passes unchanged.
- AC4: keys unaffected: `qs.parse('1=2&a[1]=3', {parseNumbers:true})` → `{ '1': 2, a: [3] }`; `qs.parse('a[01]=1',{parseNumbers:true})` → `{a:{'01':1}}`.
- AC5: arrays / nesting / comma: `a[]=1&a[]=x` → `{a:[1,'x']}`; `a=1&a=2` → `{a:[1,2]}`; `a[0]=1&a[1]=2` → `{a:[1,2]}`; `a[b][c]=3` → `{a:{b:{c:3}}}`; `a=1,2,x` with comma:true → `{a:[1,2,'x']}`; `a[]=1,2` with comma:true → `{a:[[1,2]]}` (same shape as BASE with strings); `a=%31` → `{a:1}` (conversion after decoding).
- AC6: `parseNumbers` non-boolean (e.g. 'true', 1, null) throws TypeError '`parseNumbers` option can only be `true` or `false`, when provided'; undefined allowed.
- AC7: README documents the option with a runnable example; `npx evalmd README.md` ok.
- AC8: `npx tape 'test/**/*.js'` all pass (1141 + new), `npx eslint .` 0 errors.

# Stop-and-ask items
- none

# Review focus
NaN/Infinity pass the String round-trip but are not finite; -0 ('-0' → '0'); precision loss >2^53; exponent forms that ARE canonical ('1e+21', '5e-7'); strictNullHandling null values; custom decoder returning non-strings; interpretNumericEntities + iso-8859-1 charset ordering; allowEmptyArrays with '' ; arrayLimit overflow objects; duplicates first/last; object (non-string) input; plainObjects.

# Constraints
- No new deps; don't touch dist/qs.js; keep ES5 style; no change to stringify.

# Rulings
- Ruling: the rule is literally `isFinite(n) && String(n) === v`, so canonical exponent strings like '1e+21' and '5e-7' DO convert while '1e3' doesn't — the user defined the rule as the round-trip — cost if wrong: rare large/small numeric strings become numbers.
- Ruling: '-0' stays a string (String(-0) is '0') — falls out of the rule — cost if wrong: none practical.
- Ruling: conversion applies after decoding and after interpretNumericEntities, so '%31' → 1 — values are compared in decoded form — cost if wrong: percent-encoded digits convert.
- Ruling: only string values produced by parsing a string input convert; null (strictNullHandling), non-string decoder results, and values in object (non-string) input pass through unchanged — callers passing objects already own their types — cost if wrong: object input stays unconverted.
- Ruling: validation message uses the allowEmptyArrays style ('can only be `true` or `false`, when provided') — 2 of 3 existing boolean validations use it — cost if wrong: cosmetic.
- Ruling: CHANGELOG and dist/qs.js untouched — maintainers update them at release — cost if wrong: a line to add later.

# Tasks
## T1 parseNumbers option — tier: haiku — sequential — AC1–AC8
- Worktree: main tree
- Files: lib/parse.js, test/parse.js, README.md
- Depends on: none
- Interfaces: option `parseNumbers` (boolean, default false) in `defaults` and `normalizeParseOptions` output
- Tests allowed to change: none (append new tests only)
- Status: dispatched

# Log
- T1 DONE (71c7fe0, haiku), check run
- iter 1 verify (opus): all AC PASS; FAIL on blocker — utils.merge `if (!source) return target` drops converted 0 on merge into existing path (a[]=1&a=0 → {a:[1]}). Root cause: brief/plan didn't consider that numbers flow through merge where falsy checks assumed strings. Also should-fix README assert.deepEqual is loose; nit tests nested inside duplicates test.
- Ruling: fix merge only when options.parseNumbers is true — unconditional `source !== 0` would change BASE behaviour for object input holding 0 (AC3) — cost if wrong: that latent object-input bug stays as it was at BASE.
- Ruling: a custom decoder returning an array has its elements converted (same as comma arrays) — accepted as-is, verifier nit — cost if wrong: an odd decoder sees numbers.
- fix 1 (blocker+should-fix+nits, round 1, sonnet): 53d4962, 1189 pass
- recheck fix 1 (sonnet): PASS; all 5 findings ADDRESSED; 30k-case differential fuzz vs BASE, 0 divergences.
- Ruling: with parseNumbers:true, object input holding a native 0 now keeps it on merge (`qs.parse({'a[]':'x', a:0}, {parseNumbers:true})` → {a:['x',0]}; BASE and option-off drop it) — side effect of the gated merge fix; keeping a real 0 is correct, and default behaviour is unchanged — cost if wrong: one odd object-input case differs only when the option is on.
- DONE: branch orch/parse-numbers, commits 71c7fe0, 53d4962. Report: .orchestrator/report.md
