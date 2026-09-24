# Repo notes — textkit
- Zero-dependency ESM string helpers. package.json has `"type": "module"`, NO dependencies. Keep it that way.
- Node v22 (built-in `node:test` runner + `node:assert/strict`).
- Layout:
  - src/index.js — barrel: `export { slugify } from "./slug.js";` / `export { wrap } from "./wrap.js";`
  - src/slug.js — slugify(input); coerces with String(input)
  - src/wrap.js — wrap(text, width = 80); splits on /\s+/, greedy fill, joins lines with "\n"
  - test/slug.test.js, test/wrap.test.js — one file per module
- Test command (full suite): `npm test`  (= `node --test test/*.test.js`)
- Lint (syntax check, per file — `node --check a b` only checks the first file):
  `for f in src/*.js test/*.js; do node --check "$f" || exit 1; done`
- Baseline at BASE 6ea27ab: 3 tests, 3 pass, 0 fail. Lint clean. No known failures.
- Conventions (imitate test/wrap.test.js and src/wrap.js):
  - Named exports only, `export function name(...)`, double quotes, semicolons, 2-space indent.
  - Tests: `import { test } from "node:test"; import assert from "node:assert/strict";`
    import the module directly from "../src/<module>.js"; one-line `test("name", () => ...)` where possible.
  - Inputs coerced with `String(x)` rather than type-checked.
  - A one-line `//` comment above the function describing it.
- Surprises: wrap() collapses ALL whitespace (including newlines) into single spaces; that stays as is.
