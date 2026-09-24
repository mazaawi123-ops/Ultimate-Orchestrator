# Ultimate Orchestrator

A Claude Code skill for coding work, named `code-orchestrator` inside the files. It finishes a
change and proves it: every test result, review and report refers to one frozen candidate,
and "done" is refused when the evidence is missing, stale or doesn't match what's delivered.
It delegates to worker agents or adds an independent reviewer only when that earns its cost.

## How it works

Two decisions are made separately:

| Decision | Default | Increase it when |
|---|---|---|
| How many builders? | The main session plans and builds | Substantial independent pieces, useful context separation, or the user asks |
| How much review? | Automated checks and the main session's own inspection | Uncertain behaviour, serious consequences, weak tests, hard integration, or the user asks |

That gives three routes:
- **Direct:** the main session builds and checks.
- **Reviewed:** the main session builds, then one fresh reviewer checks the candidate against
  the original request, with at most two repair cycles.
- **Parallel:** a few workers on independent pieces, with the main session owning integration.

| Role | Model and effort (this repo's settings) |
|---|---|
| Main session | whatever you choose. Mo's setting is `/model opus`, then `/effort high` |
| `orch-worker-haiku` | Haiku: bounded mechanical tasks |
| `orch-worker-sonnet` | Sonnet, medium effort: substantial delegated pieces, repairs |
| `orch-verifier` | Opus, extra-high effort: independent review |
| `orch-rechecker` | Sonnet, high effort: targeted re-review after a risky repair |

The agent files in `agents/` set each role's model, effort, turn cap and tool limits. The
runtime enforces those limits: reviewers have no Edit, Write or Agent tools, and no agent can
delegate further. Bash can still write, so reviewers aren't strictly read-only. The helper
catches any change they make to the tree. The model and effort choices are candidates, not
proven optima.

## What the helper guarantees

`code-orchestrator/scripts/orch.sh` runs on bash 3.2+, on macOS and Linux. It's tested by
`tests/helper/` (32 tests).

| Guarantee | How |
|---|---|
| Tests, review and report concern the same code | `check` refuses uncommitted or untracked leftovers, freezes HEAD as the candidate, and records every command against it with exit code, time, environment fingerprint and log. A command that changes the tree voids its own evidence. `diff` only covers BASE..candidate. |
| No "done" on bad evidence | `gate` and `finish done` refuse missing, stale, failing or mismatched evidence, a required review that wasn't recorded, and unverified manual checks. |
| Old failures aren't blamed on the change | `start -- <tests>` records the baseline. Later failures are split into pre-existing and new. |
| Weakened tests are noticed | The audit flags deleted lines and added `skip`/`only`/`xfail`/`skipTest` markers in existing tests, runner and discovery configuration, fixtures and snapshots, and changes in skipped or executed counts. Deliberate changes are approved, with a reason, in `.orchestrator/approved-test-changes`, by path or as `count:skipped` / `count:executed`. |
| No network when promised | `--offline` uses `unshare -n` on Linux or `sandbox-exec` on macOS, and first proves with a loopback probe that the connection is blocked. It refuses (exit 5) where it can't enforce this. |
| Honest environment checks | `fresh` runs a fresh checkout of the candidate with an allowlisted environment and a temporary HOME. It says plainly that it is **not** a filesystem sandbox. |
| Workers don't share mutable dependencies | Worktrees get a copy of `node_modules` or the venv (copy-on-write where supported), not a writable link. |
| Bounded repair | `repair` allows 2 whole cycles per run. It's advisory: it records and warns. |
| An auditable record | `.orchestrator/` keeps the manifest, evidence table and logs after the run; only finished worktrees are removed. |

## Evidence so far

- **The independent review's four reproduced helper flaws are fixed.** The reviewer's own
  script reproduces 4 of 4 on revision 919240501; the same scenarios reproduce 0 of 4 on the
  current helper. See `docs/review/`.
- **The graders are self-tested.** For each of the 8 graded tasks, a correct reference must
  pass every core check, and 37 deliberately broken variants must each fail the checks aimed at
  them (`evals/README.md`).
- **Trigger description:** 20/20 on the development prompts; 18/20 on 20 held-out prompts,
  run once on the final wording (`evals/results/trigger/`).
- **Routing pilot on 2 held-out tasks** (`evals/results/pilot.md`): 12 runs, 3 routes, 2
  repeats. Every run passed every hidden check. Direct cost $0.82 a run and took 2.7 min;
  Reviewed cost $2.36 and 11.3 min; the previous always-delegate design cost $3.21 and
  14.3 min (all estimated). The reviews found real but low-severity issues, all in the
  reviewed runs' own drafts, and never changed task success. One old-design repair
  introduced a defect. It's directional: two tasks can't settle the question.
- **The pilot also exposed four reliability problems, now fixed:** count flags that couldn't
  be approved; a review lost in headless mode; a reviewer installing into the shared
  environment; and per-agent token accounting.
- Earlier designs' measurements, with the published run records, are in
  `evals/results/measurements.md`. Their limits are stated there: dollar figures are Claude
  Code's local estimates, not bills; the "no skill" runs were prompted to delegate; most
  configurations ran once.

## Install

From this repo's folder:

```
bash install.sh
```

It copies the skill to `~/.claude/skills/code-orchestrator/` and the agents to
`~/.claude/agents/`. Without the agents the skill still works, but every agent runs at the
default effort.

**Headless runs (`claude -p`):** set `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0`. Otherwise
Claude Code stops a background agent, such as a long review, after 10 idle minutes and drops
its result. That's what happened to one pilot run.

## Repo layout

```
code-orchestrator/               the skill (installed)
  SKILL.md                       routing, stop-and-ask, the loop, report, agents
  scripts/orch.sh                the helper
  references/                    run-record, worker-brief, reviewer-brief (loaded only when needed)
agents/                          the four agents: model, effort, tool limits, turn caps
install.sh
code-orchestrator.single-file.md the skill as one file (tools/build_single_file.py rebuilds it)
tests/helper/                    helper regression tests and the review's reproductions
evals/                           benchmark tasks, runner, graders with self-tests, results
docs/review/                     the independent review, the vNext proposal, before/after results
```
