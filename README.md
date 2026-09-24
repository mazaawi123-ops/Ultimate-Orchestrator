# Ultimate Orchestrator

A Claude skill for coding work that spans several files and needs tests. Claude plans the
change and hands the building to cheaper models. An independent reviewer checks the result,
and the loop runs until every acceptance criterion is verified and the test suite is green:

**plan → build → test → verify → check → (fix → re-verify) → report**

The goal is a verified result at the lowest cost. The skill's name inside the files is
`code-orchestrator`.

## Roles

| Role | Model | Job |
|---|---|---|
| Planner | the session: Opus, high effort | Understands the request, writes checkable criteria and precise briefs, rules on findings |
| Workers | `orch-worker-haiku` (Haiku) for fully specified tasks; `orch-worker-sonnet` (Sonnet, medium effort) for judgement and fix rounds; Opus for a third fix round | Write the code and tests, in their own git worktrees when running in parallel |
| Verifier (full) | `orch-verifier`: Opus, extra-high effort | Runs once, after the first green build, and tries to show the change does *not* meet the criteria |
| Verifier (scoped) | `orch-rechecker`: Sonnet, high effort | After each fix round: were the findings addressed, and did anything else break |

Each agent's model and effort are set in `agents/*.md`.

The planner picks the cheapest mode that fits:
- **Direct:** a one-file change; no agents.
- **Lite:** the default. One worker, then the verifier.
- **Full:** a worker per substantial piece, in parallel when the pieces are independent.

## Measured

These are billed costs from real `claude -p` runs on three small two-task changes, one run
each (details in `code-orchestrator/references/example-run.md`):

| Setup | Cost (3 tasks) | Graded checks | Code checks |
|---|---|---|---|
| Opus, no skill | $5.24 | 32/41 | 28/29 |
| Sonnet, no skill | $2.33 | 31/41 | 28/29 |
| Skill, Opus planner | $6.65 | 40/41 | 28/29 |
| **Skill, Sonnet planner** | **$5.46** | **41/41** | **29/29** |
| Skill with the `agents/` settings (Opus high, verifier Opus extra high) | $8.76 | 40/41 | 28/29 |

- **Cost:** with a Sonnet planner, the skill costs about what Opus alone does, and passes every
  check. The default `agents/` settings put the verifier on extra-high effort. That found three
  times as many should-fix issues, for about +$0.70 per task. Plain Sonnet costs about 2.3x less, but ships the edge-case bugs the
  verifier catches.
- **Real repos:** on humanize, click and qs, final quality was equal for the skill and Opus alone,
  and the skill cost 1.6x more ($11.36 against $7.06). The verifier caught real bugs, but ones
  the delegated code had introduced. So for well-specified changes in well-tested repos, the
  skill now offers Direct mode.
- **Bugs caught:** in the benchmark, the loop's verifier caught a quadratic `wrap()` that hung
  on long words, and comma-only CSV rows being silently dropped.
- **Trap tests:** 4 red-team rounds against planners, workers and verifiers. Every gap found
  has a fix, and every fix has been re-tested. These include not touching production data,
  resuming an interrupted run, and keeping the plan cheap. All pass except one, and that one
  only partly: workers now report a typo in nearby code, but still missed a nearby crash.
- **Worker briefs:** pasting 15 lines of repo notes into each brief cut worker tokens by ~30%.
  "You are a senior developer" made no difference.

## What it guards against

- **Real repos:**
  - It works on an `orch/<name>` branch and never pushes.
  - It asks before touching uncommitted work, and resumes an interrupted run instead of
    overwriting it.
- **Stop and ask:**
  - irreversible actions
  - secrets
  - production data, even read-only
  - anything outside the repo
  - new dependencies or real services
  - a plan that turns out wrong
- **Tests that lie:**
  - Existing tests are fixed points: any deleted assertion is flagged.
  - A clean-room run with no `.env`, no credentials and service URLs at a closed port catches
    tests that call real services.
- **Parallel workers:** a timestamp check catches any worker that writes outside its own
  worktree.
- **Cheap-model mistakes:**
  - Haiku briefs carry exact input → output examples.
  - Workers list their decisions.
  - The verifier is the backstop.

## Repo layout

```
code-orchestrator/               the skill: install this folder
  SKILL.md
  scripts/orch.sh                one-call helpers: start, check, stamp/stray, worktrees,
                                 clean-room, old-tests, diff (bash 3.2+, macOS and Linux)
  references/
    plan-template.md             plan template with a filled-in example
    worker-brief.md              the brief every worker gets
    verifier-brief.md            full and scoped verifier briefs
    example-run.md               the measurements behind every rule
agents/                          the four subagents: model and effort per role
install.sh                       installs the skill and the agents into ~/.claude
code-orchestrator.single-file.md the same skill as one file (references and script as appendices)
tools/build_single_file.py       rebuilds the single-file version
evals/
  evals.json                     3 test tasks with assertions
  make_fixtures.py               creates the 3 small repos the evals run against
```

## Install

- **Claude Code:** from this repo's folder, run

  ```
  bash install.sh
  ```

  - It copies the skill to `~/.claude/skills/code-orchestrator/`, and the four agents to
    `~/.claude/agents/`. The agents set each role's model and effort. Without them the skill
    still works, but every agent runs at the default effort.
  - Then plan with `/model opus` and `/effort high`. `/model sonnet` is the cheaper
    alternative: in testing it scored as well for 18% less.
- **Claude app:** zip the `code-orchestrator/` folder and upload it where you add custom skills.

The planner needs the Agent tool to dispatch workers.

## Running the evals

```
python evals/make_fixtures.py   # creates evals/fixtures/{todo-cli,inventory,textkit}
```

Then give Claude each prompt in `evals/evals.json`, with the skill installed, and grade the
result against that eval's assertions.
