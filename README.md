# Ultimate Orchestrator

A Claude skill for coding work that spans several files and needs tests. Claude takes the
planner role on the strongest model, hands the building to cheaper models, has the result
checked by an independent reviewer, and loops until every acceptance criterion is verified
and the test suite is green:

**plan → build → test → verify → check → (fix → re-verify) → report**

The skill's name inside the files is `code-orchestrator`.

## Roles

| Role | Model | Job |
|---|---|---|
| Planner | Opus | Understands the request, writes checkable acceptance criteria, splits the work into precise briefs, rules on what the verifier finds |
| Workers | Haiku for fully specified tasks, Sonnet where judgement is needed, Opus for a third fix round | Write the code and tests. Each works in its own git worktree when tasks run in parallel |
| Verifier (full) | Opus | Runs once after the first green build and tries to show the change does *not* meet the criteria |
| Verifier (scoped) | Sonnet | After each fix round, checks each finding was addressed and nothing else broke |

The planner picks parallel (git worktrees) or sequential mode for each task, based on
whether tasks share files or interfaces.

## What it guards against

- **Real repos:**
  - It works on an `orch/<name>` branch and never pushes.
  - It asks before touching uncommitted work.
  - It stages files by name, never with `git add -A`.
- **Existing tests are fixed points:** a worker that finds one contradicting the task stops and asks instead of editing it.
- **A clean-room test run:**
  - The suite runs in a fresh worktree with service URLs pointed at a closed port and no credentials.
  - This catches tests that call real services or read a local `.env`.
- **A stop-and-ask list:**
  - irreversible actions
  - secrets
  - production data, even read-only
  - anything outside the repo
  - lifting a default constraint
  - a plan that turns out wrong
- **Cheap-model mistakes:**
  - Haiku briefs carry exact input → output examples.
  - Workers must list their decisions and deviations.
  - The verifier is the backstop.

## Measured

These numbers come from real runs recorded in `references/example-run.md`:

- **Tiered vs single-model:**
  - Tiered: Haiku 111k, Sonnet 178k, Opus 84k tokens.
  - Sonnet workers throughout: 487k tokens, 205k of them on Opus.
  - The hierarchy doesn't cut total tokens. It moves them to cheaper models.
- **Parallel vs sequential:** parallel built a third faster at the same cost and quality.
- **Worker guard rails:** without them, 1 of 2 parallel workers wrote outside its worktree. With them, 0 of 6 did.
- **Red-team rounds:** three rounds of traps against planners, workers and verifiers. Every gap found got a fix.
  - **Re-tested:** fake mocks, tests reading `.env`, silent decisions, known failures, the old-test check.
  - **Not yet re-tested:** the production-data stop, the check for an earlier run, keeping the plan proportionate.

For a one-file change, a single session is cheaper, and the skill says so.

## Repo layout

```
code-orchestrator/               the skill: install this folder
  SKILL.md
  references/
    plan-template.md             plan template with a filled-in example
    worker-brief.md              the brief every worker gets
    verifier-brief.md            full and scoped verifier briefs
    example-run.md               real runs with token counts
code-orchestrator.single-file.md the same skill as one file, references as appendices
evals/
  evals.json                     3 test tasks with assertions
  make_fixtures.py               creates the 3 small repos the evals run against
```

## Install

- **Claude Code:**
  - Copy `code-orchestrator/` to `~/.claude/skills/code-orchestrator/` to use it everywhere.
  - Or copy it to `.claude/skills/code-orchestrator/` inside a project to use it there only.
- **Claude app:** zip the `code-orchestrator/` folder and upload the zip where you add custom skills.

The planner needs the Agent tool to dispatch workers, so use it in a session where subagents are available.

## Running the evals

```
python evals/make_fixtures.py   # creates evals/fixtures/{todo-cli,inventory,textkit}
```

Then give Claude each prompt in `evals/evals.json` with the skill installed, and grade the result
against that eval's assertions.
