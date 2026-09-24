# Repo notes (qs)
- Pure ES5 CommonJS lib: lib/parse.js (parse), lib/stringify.js, lib/utils.js (maybeMap, combine, merge, compact), lib/index.js.
- Tests: tape, test/parse.js (big file of `t.test(...)`/`st.deepEqual`/`st['throws']`), run `npx tape 'test/**/*.js'` → 1141 pass at BASE.
- Lint: `npx eslint .` → 0 errors, 12 pre-existing warnings at BASE (warnings OK, errors not). ES5 style: `var`, no arrow fns, 4-space indent, `st['throws']`.
- parse.js flow: normalizeParseOptions(opts) validates + builds options object (keys alphabetical in both `defaults` and returned object); parseValues(str) splits on delimiter, decodes each key/value (values via utils.maybeMap so comma-split arrays are handled), applies interpretNumericEntities, then builds a flat key→val map; parseKeys/parseObject then build nested objects/arrays from bracket keys; utils.merge/compact finish.
- Boolean-option validation pattern: `if (typeof opts.X !== 'undefined' && typeof opts.X !== 'boolean') throw new TypeError('`X` option can only be `true` or `false`, when provided');` (see allowEmptyArrays/decodeDotInKeys). Tests for it: test/parse.js 'throws when decodeDotInKeys is not of type boolean' (~line 147).
- qs.parse also accepts a non-string object as input (values passed through, not decoded).
- README.md parse options are documented around lines 175-200 (allowDots, decodeDotInKeys, allowEmptyArrays, duplicates), each a sentence + ```javascript block with assert.deepEqual.
- dist/qs.js is a release build artefact: do not touch. CHANGELOG.md: do not touch.
