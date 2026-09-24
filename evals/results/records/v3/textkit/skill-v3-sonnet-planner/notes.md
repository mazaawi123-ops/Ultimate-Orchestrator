# Repo notes — textkit

- Zero-dep ESM string lib. `"type": "module"` in package.json.
- Layout: `src/<fn>.js` implements one export; `src/index.js` re-exports everything;
  `test/<fn>.test.js` mirrors it 1:1.
- Test command: `npm test` = `node --test test/*.test.js` (node's built-in runner,
  `node:test` + `node:assert/strict`).
- No lint script configured. No build step.
- Existing style (see src/slug.js, src/wrap.js): plain function, no classes, `String(input)`
  coercion at the top, no external deps, short top-of-file comment only when non-obvious.
- Tests use `import { test } from "node:test"; import assert from "node:assert/strict";`
  and `assert.equal(fn(...), expected)`.
- Baseline: `npm test` → 3 passed, 0 failed (slug x2, wrap x1). No lint command exists.
- No external services, no .env, no secrets involved anywhere in this repo.
