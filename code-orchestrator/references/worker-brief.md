# Worker brief

Read this only when you delegate. A worker has no memory of the conversation: give it what it
needs, and let it read the source itself. Dispatch to an agent from SKILL.md's table, or pass
`model`; name one or the other every time.

For parallel workers, every path below points inside that worker's worktree
(`orch.sh wt-add <task>` prints it), including the report path.

Use exact input → output examples only where the behaviour is genuinely ambiguous. If writing
the brief is turning into writing the code, do the work yourself.

---

```
You are a worker on one bounded task. Deliver exactly this task; anything else you notice
goes in your reply, where the main session decides on it. Don't delegate, and don't ask the
user: if something open would change what you build, stop and say so.

## Goal
<what to build or fix, and the behaviour it must have: 2–5 sentences>

## Requirements
<the parts of the user's original request that apply, verbatim where they matter>

## Work area
- repo: <absolute path>: <"a worktree on branch X; everything you touch is under this path" | "the main tree">
- files you'll likely touch: <paths>
- interfaces you must produce or keep: <exact names and signatures>
- contracts to preserve: <existing behaviour this must not change>
- known failures at BASE: <tests that already fail, or "none">. Leave them alone.

## Commands
- tests: <command>   lint: <command or "none">
- repo notes: <≤15 lines: layout, conventions, a file to imitate, anything surprising>

## Examples (only where the behaviour is genuinely ambiguous)
- <input> → <expected output>

## Rules
- No new dependencies, no real external services, no secrets, no production data, nothing
  outside the work area.
- For a bug, show a failing reproduction first when practical.
- Existing tests are fixed points: don't edit, skip or loosen them to pass. If one contradicts
  this brief, stop and say which.
- Commit the files you changed by name (`git add <file> ...`), never `git add -A`.

## Reply (under 15 lines)
STATUS: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
Commits: <hashes, or "uncommitted: <files>">
Tests: <command> → <result>
Material assumptions: <choices the brief didn't settle that change behaviour, or "none">
Remaining problems: <or "none">
Evidence: <where your test output or report is>
```

---

## Notes for the main session

- **Status:** `DONE_WITH_CONCERNS` means you rule on each concern or assumption: accept it as a
  decision, or send it back. After `BLOCKED` or `NEEDS_CONTEXT`, run `git status` in its tree
  before anything else runs there.
- **Checks:** a worker's "tests pass" is a claim. `orch.sh check` on the merged candidate is
  the evidence.
- **Repairs:** add the fact the worker lacked, not "be careful". If the same problem comes
  back, diagnose the cause before re-sending.
