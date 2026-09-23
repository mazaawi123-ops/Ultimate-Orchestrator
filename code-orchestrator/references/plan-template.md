# Plan template

Write this to `.orchestrator/plan.md` before dispatching anything. Keep it current, and log
each step as it finishes: the plan survives your context filling up and the session being
interrupted, and it becomes the report.

```markdown
# Goal
One paragraph in your own words: what the user wants and what "done" means to them.

# Baseline
- branch: orch/<name>, from <user's branch> (uncommitted work: <none | committed | stashed | built on — as the user chose>)
- BASE: <sha>
- tests at BASE: <command> → <result>; pre-existing failures: <list or "none">
- lint at BASE: <command> → <result> (checked that it covers every file it claims to)
- clean-room test command: <`bash <skill-dir>/scripts/orch.sh clean-room SERVICE_URL=http://127.0.0.1:9 -- <tests>`,
  or "n/a: no external services">
- repo notes: .orchestrator/notes.md (pasted into every brief)
- estimate given to the user: <agents by model, tokens, share on Opus>

# Acceptance criteria
- AC1: <checkable by a stranger with a command or an observation>
- AC2: ...
- AC3 (manual): <only for what no command can check; these go under "Not verified" in the report>

# Stop-and-ask items
- <anything from the skill's stop-and-ask list this plan touches, and the user's answer> or "none"

# Review focus
Input classes / failure modes implied by the request that no task's tests are likely to hit:
- <empty input> <unicode> <boundary values> <error path> <concurrency> <line endings> ...

# Constraints
- <what must not change, dependencies not allowed, conventions — each with its reason>

# Rulings
- Ruling: <decision> — <why> — <cost if wrong>

# Tasks
## T1 <title> — tier: haiku | sonnet — mode: worktree | sequential — AC: AC1
- Worktree: <path from `orch.sh wt-add T1`, or "main tree">
- Files: <paths>
- Depends on: <task ids or "none">
- Interfaces:
  - Consumes: <exact names/signatures from other tasks or existing code>
  - Produces: <exact names/signatures other tasks rely on>
- Tests allowed to change: <names, each with the ruling that allows it, or "none">
- Status: pending | dispatched | DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT

## T2 ...

# Shared-surface check
One row per pair of tasks that touch the same file or interface. Any row here means those
tasks are sequential, or their Interfaces blocks must match exactly.
| Tasks | Shared file / interface | Resolution |
|---|---|---|

# Log
- iter 1: <what ran, what the verifier found, root cause of each failure>
- fix 1 (finding X, round 1, sonnet): <what changed>
```

## Checks before dispatching

- Every AC is covered by at least one task, and every task names at least one AC.
- No placeholders: "add appropriate error handling", "similar to T2", "write tests for the
  above" with no test cases named. Each is a place where a worker will guess.
- Names in Interfaces blocks match across tasks: same function name, same argument order.
- Every Haiku task leaves no decisions open. If one does, move it to Sonnet.
- Every Haiku brief gives exact input → output examples for each edge case its review focus
  names. If you can't write the expected output, the decision is still open.
- Every dispatch names its agent (`orch-worker-haiku`, `orch-worker-sonnet`, ...) or its `model`.
- Before a parallel dispatch: `orch.sh stamp`, and every path in each brief is inside that
  worker's worktree.

## Example (abridged, from a real run)

```markdown
# Goal
Stop Inventory.ship() driving stock negative, and add Inventory.import_csv(path) for bulk
receiving from a sku,qty CSV, with line-numbered errors for bad rows.

# Acceptance criteria
- AC1: ship(sku, qty) with qty > level raises InsufficientStock, level unchanged; qty == level succeeds
- AC2: import_csv on "sku,qty\nA,5\n\nB,2\n" → A=5, B=2 (blank line skipped)
- AC3: bad row (non-int / non-positive qty, missing sku) → ValueError containing "line N",
       N = physical line (header = 1); inventory unchanged after the error
- AC4: python -m pytest -q passes; new tests for AC1–AC3

# Review focus
CRLF; blank lines before a bad row; quoted fields containing newlines; BOM; header column
order; rows of only commas

# Rulings
- Ruling: header row required — the request says "columns sku,qty", which implies a header
  — cost if wrong: headerless files are rejected with "line 1: missing header"
- Ruling: validate all rows before receiving any — a half-imported file is worse than none
  — cost if wrong: a user wanting partial import has to split the file

# Tasks
## T1 fix ship overdraw — tier: haiku — sequential — AC1
- Files: inventory/stock.py, tests/test_stock.py
## T2 import_csv — tier: haiku — sequential, after T1 — AC2, AC3
- Files: inventory/stock.py, tests/test_import_csv.py
- Interfaces: Produces Inventory.import_csv(path: str | Path) -> int

# Shared-surface check
| T1, T2 | inventory/stock.py | sequential |
```
