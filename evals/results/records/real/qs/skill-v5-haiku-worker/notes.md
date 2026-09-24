# Repo notes (qs)
- Library: lib/parse.js (qs.parse), lib/stringify.js, lib/utils.js. ES5 style: `var`, no arrow fns, 4-space indent, single quotes.
- dist/qs.js is a browserify build artifact — do NOT edit or rebuild it.
- Tests: tape, `npx tape 'test/**/*.js'` (BASE: 1141 pass, 0 fail). Parse tests in test/parse.js, pattern `t.test('...', function (st) { st.deepEqual(qs.parse(...), {...}); st.end(); });`.
- Lint: `npx eslint .` (BASE: 0 errors, 12 pre-existing warnings — fine). README examples are executed: `npx evalmd README.md` (BASE: ok) — every ```javascript block in README must run with `assert`/`qs` in scope.
- parse.js: `defaults` object (alphabetical), `normalizeParseOptions` validates + builds options (alphabetical keys), `parseValues` splits the string and decodes each value (`utils.maybeMap` over comma-split arrays), then `parseKeys`/`parseObject` build nesting. Values only pass through parseValues when input is a string.
- Existing boolean validation message style: '`allowEmptyArrays` option can only be `true` or `false`, when provided' (TypeError).
- README: parse options documented under "### Parsing Objects"/"### Parsing Arrays"; "### Parsing primitive/scalar values (numbers, booleans, null, etc)" at ~line 377 says values are strings by default.
- No known failing tests at BASE.
