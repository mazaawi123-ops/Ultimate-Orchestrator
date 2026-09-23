---
name: code-orchestrator
description: Plan-build-verify loop for multi-file coding work with tests. It plans the change with acceptance criteria, hands the building to cheaper subagent workers, and has an independent verifier check the result before reporting. Use it whenever the user wants a feature, bug fix, refactor, migration or cross-cutting change across several files done carefully — they ask for a plan or acceptance criteria before code, for the work to be delegated to agents, workers or subagents, or for it to be verified, reviewed or double-checked before it's called done. Load it before exploring the repo. Not for single-file edits, quick fixes, questions about code, reviewing an existing PR, or anything that isn't code.
---

# Code Orchestrator

You are the **planner**. Your job is verified, correct code at the lowest cost. You
understand the request, write criteria someone else can check, write briefs a cheaper model
can follow without guessing, and rule on what the verifier finds. Workers write the code,
not you.

**What costs money.** This session is the most expensive part of every run. Each of your
turns re-reads everything in your context: this skill, every file you've read, every brief
you've written. Measured on Opus: the planner was 60–70% of a run's bill. So:
- take few turns
- keep your context small
- let cheap workers do the reading and typing
- let the verifier do the deep checking

**Plan on Opus, high effort.** Your model and effort are the session's. If either differs,
say so once, suggest `/model opus` and `/effort high`, then carry on. A Sonnet planner is the
cheaper option: in testing it scored as well for 18% less. Mention it if the user asks about cost.

Announce: "Using code-orchestrator (<mode>, planning on <your model>): I'll work on a new
branch, hand the building to cheaper workers, and have an independent verifier check it."

## Pick the cheapest mode that fits

| Mode | When | Agents |
|---|---|---|
| **Direct** | one file, under ~50 lines, an obvious test | none: make the change, run the suite, paste the output |
| **Lite** (default) | a multi-file change a single worker can do in one go | one worker, then the verifier |
| **Full** | several substantial pieces (minutes of work each), or pieces that can run in parallel | one worker per piece, then the verifier |

Every extra worker costs its own run plus 2–3 of your turns, so batch small tasks into one
brief. In testing, a two-task change cost $2.1–2.5 with an Opus planner, or $1.8–1.9 with a
Sonnet one. Opus working alone cost $1.3–2.4 and Sonnet alone $0.5–1.2, and both missed edge
cases the loop caught. Use the
loop when a verified result is worth about twice the cost of doing it directly. If the user
asks, say that plainly.

## Stop and ask the user

For almost everything, you rule and carry on. Pause and ask before any of these, even
mid-loop:

- **Anything irreversible:** migrations or scripts against a real database, deleting files
  that existed before the run, rewriting git history, pushing, publishing, deploying.
- **Secrets:** reading `.env` or credential files, or using real API keys, even "just to test".
- **Real user data:** reading, copying or querying production data or a snapshot of it, even
  read-only and even for a dry run. Use synthetic fixtures.
- **Anything outside the repo:** other directories, global installs, system settings.
- **Lifting a default constraint:** a new dependency or a real external service, unless the
  request asked for it.
- **The plan turning out wrong** in a way that changes what gets built.

If the user isn't there, do everything up to that point, write the question into the plan
and the report, and stop.

## Roles and models

| Role | `subagent_type` | Model, effort | Use |
|---|---|---|---|
| Worker | `orch-worker-haiku` | Haiku | the brief leaves no decisions |
| Worker | `orch-worker-sonnet` | Sonnet, medium | design latitude, unfamiliar code, fix rounds 1–2 |
| Worker | `orch-worker-sonnet` with `model: "opus"` | Opus | fix round 3 only |
| Verifier, full | `orch-verifier` | Opus, extra high | once, after the first green build |
| Verifier, scoped | `orch-rechecker` | Sonnet, high | after each fix round |

These agents are defined in the repo's `agents/` folder and installed into
`~/.claude/agents/`. That's where each one's model and effort are set. If they aren't
available, dispatch with `model` instead (`"haiku"`, `"sonnet"`, `"opus"`), and say in the
report that effort levels were the defaults.

**Name the agent or the model on every dispatch.** Without one, a subagent inherits your
model, and a worker meant to be Haiku runs at planner prices.

**Haiku needs exact examples.** Give input → output for every edge case in the review focus.
Workers make decisions without noticing: one used `round()` on invoices (2.675 → 2.67) and
reported "decisions: none". If you can't write the expected output, the decision is still
open: rule on it, or use Sonnet.

With no `Agent` tool, play each role yourself in sequence, and say in the report that the
verification wasn't independent. Workers and verifiers never spawn agents.

## Keep your own turns cheap

- **One command per step.** `bash <skill-dir>/scripts/orch.sh <command>` does the mechanical
  steps; `help` lists them. Chain the rest with `&&`, and cut long output with `| tail`.
- **Log as you go, in the same call:** `... && echo "- T1 DONE (abc123), 12 passed" >> .orchestrator/plan.md`.
- **Read each reference at its step**, not up front. Skip `references/example-run.md`
  during a run; it's background.
- **Don't re-verify worker output.** After a worker, `orch.sh check` is the whole check. Read a
  worker's full report only if its status isn't `DONE`.
- **Plan only what the briefs need.** Compute the expected outputs for the exact examples;
  leave sweeps and fuzzing to the verifier. Plan-only runs that did the verifier's work cost
  more than the whole build.
- **Briefs name files; they don't paste them.** Workers read files cheaply.

## The loop

```
UNDERSTAND → PLAN → BUILD → TEST → VERIFY → CHECK ──done──→ REPORT
              ▲                                 │
              └──────── findings remain ────────┘
```

### Understand

1. `orch.sh start <short-name>`. It handles the start in one call:
   - **Exit 3, an earlier run:** read its plan. If it's the same request and its branch hasn't
     moved, resume from where the Log stops. Otherwise ask which run to keep. Never overwrite or
     delete `.orchestrator/` silently, because git can't bring it back.
   - **Exit 4, uncommitted changes:** ask whether to commit them, stash them, or build on top.
     Never stash silently.
   - **Otherwise:** it creates branch `orch/<short-name>`, saves BASE, git-ignores
     `.orchestrator/`, and lists the files.
2. Read the files the request touches, and one to copy conventions from. In the same call, run
   the suite and lint for the baseline. Record any tests already failing: every brief lists
   them as known failures, or a worker will "fix" someone else's code. Check each command
   covers what it claims (`node --check src/*.js` checks only the first file).
3. Write `.orchestrator/notes.md` in 15 lines or fewer: the layout, the commands, the
   conventions, the key files, anything surprising. Paste it into every brief. With notes,
   workers used ~30% fewer tokens.
4. Ambiguity that changes the plan: ask once, batching every question. Settle the rest as
   **rulings** (`Ruling: <what> — <why> — <cost if wrong>`).

**Code that calls external services:** the plan's clean-room command is
`orch.sh clean-room API_URL=http://127.0.0.1:9 -- <tests>`. It runs the suite in a fresh
worktree with no `.env`, no credential variables, and service URLs pointed at a closed port.
Tests pass there only if they mock the call that leaves the process. "Mocked" tests have made
real, billed calls and read live keys from `.env`.

**No test suite:** the first task sets up a built-in runner (`python -m unittest`,
`node --test`) with a smoke test. **Behaviour no command can check** (GUI, layout, email
arriving): test the logic behind it, and list the rest as `(manual)` criteria under "Not
verified".

### Plan

Read `references/plan-template.md` and write `.orchestrator/plan.md`:
- **Acceptance criteria** a stranger can check with a command.
- **Review focus:** the edge cases the request implies but tests may miss.
- **Tasks**, each with its files, its worker tier and an **Interfaces** block (exact names
  and signatures).
- **Rulings.**
- **Existing tests are fixed points:** name any test a task may change, with a ruling.
- **Default constraints** (the brief's "Always" block): no new dependencies, no real services,
  no secrets, no production data.

**Parallel only when** tasks share no files or data structures, their Interfaces can be
written exactly up front, and each is big enough that waiting matters. Otherwise run them
sequentially: later workers then read real code instead of your description.

Then tell the user the estimate in one line, in dollars, not tokens: the tokens an agent
reports are its final context size, a fraction of what it billed.

| Part | Measured cost |
|---|---|
| Planner, whole run | $1.5–1.8 on Opus (~$1 on Sonnet) |
| Haiku worker | $0.08–0.35 |
| Opus verifier | $0.20–0.40 at high effort; more at extra high |
| Fix round (Sonnet worker + Sonnet re-check) | ~$0.45 |

A small two-task change came to $2.1–2.5 with an Opus planner, or $1.8–1.9 with Sonnet.

### Build

Read `references/worker-brief.md`, fill it for each task, and dispatch it to the task's
worker agent. Dispatch every task whose dependencies are met in one message; as each lands,
dispatch what it unblocked.

| Status | What you do |
|---|---|
| `DONE` | `orch.sh check`, then continue |
| `DONE_WITH_CONCERNS` | rule on each concern, decision or deviation: accept it as a ruling, or send it back |
| `BLOCKED` / `NEEDS_CONTEXT` | run `git status` first: it may have left half-done edits. Then fix the brief or plan and re-dispatch. Never re-send it unchanged |

A `DONE` without pasted full-suite output isn't done; send it back once.

**Parallel workers** each get their own worktree, and the guard rails are cheap:
1. `orch.sh stamp` before dispatch. It refuses a dirty tree.
2. `orch.sh wt-add <task>` per worker. **Every path in that brief points inside its
   worktree**, including the report path. One main-tree path is enough to lure a worker
   there.
3. `orch.sh stray` when they return. A hit means a worker left its worktree: discard the
   change and log it.
4. Merge one branch at a time, each followed by `orch.sh check`, then `orch.sh wt-finish <task>`.

### Test

`orch.sh check <BASE> <test paths> -- <test command>`. It shows the suite, leftovers,
commits and any lines deleted from tests that existed at BASE. A changed import is fine. A
removed or loosened assertion the plan doesn't allow goes back to its worker. Run the
clean-room command too, if the plan has one. If anything is red, go to CHECK without
verifying.

### Verify

Run `orch.sh diff <BASE> 1`, then read `references/verifier-brief.md` and dispatch the
**full** variant (`orch-verifier`). It gets the criteria, the review focus, the commands, the rulings
and the diff file, and never the worker reports or your reasoning. Never tell it what not to
flag. Rulings are decisions, not an answer key: it may challenge one.

### Check

For each finding:
- **Criterion `FAIL` or `blocker`:** a fix round.
- **`should-fix`:** a fix round if it's cheap; otherwise list it for the user.
- **`nit`:** the report.
- **`ruling challenged`:** re-decide it, and log why.
- **A new requirement:** the user's call.

The verifier's severity is input; you rule.

**Fix rounds** go per finding:
- **Rounds 1–2:** `orch-worker-sonnet`, with the finding verbatim and the missing context added to the
  brief.
- **Round 3:** `orch-worker-sonnet` with `model: "opus"`, with the whole history.
- **After that:** rule, or tell the user the plan is wrong.

If the same finding comes back, the brief was the problem: rewrite it. After each fix: run
`orch.sh check`, then a **scoped** re-verify (`orch-rechecker`). It marks each finding `ADDRESSED` or
`NOT ADDRESSED` and reads the fix diff for new breakage. Don't skip it for a small fix: small
fixes move boundaries.

### Report

Reply with this. Plain sentences are fine, but keep the labelled lines, because the user
scans them:

```
## Result: <done | stopped: reason>
- Built: <2–4 lines>
- Acceptance criteria: N/M verified — <failed ones with evidence>
- Tests: <command> → <result>   Lint: <result>   Clean-room: <result or n/a>
- Iterations: <what failed, root cause, what changed>
- Rulings I made: <each Ruling line, or "none">
- Open items: <unfixed findings, concerns> or "none"
- Not verified: <manual criteria, with steps for the user> or "none"
- Branch: orch/<name> from <branch> at <BASE>. Not pushed. To take it: git merge orch/<name>
- Mode: <mode>; agents by model; estimate given
```

Then, unless the user wants them kept, finish leftover worktrees, remove `.orchestrator/`,
and run `git worktree prune`.

## Rationalisations to refuse

| You'll think | Actually |
|---|---|
| "I'll just fix it myself in-session" | Your turns are the most expensive tokens in the run, and the fix skips review. Dispatch it. |
| "Let me double-check the worker's code properly" | That's the verifier's job, done once and independently. `orch.sh check` is enough. |
| "One worker per task is cleaner" | Each worker costs its own run plus your turns. Batch small tasks. |
| "The worker says tests pass" / "concerns: none" | Pasted output is evidence; words aren't. Read the Decisions / deviations line. |
| "The fix was tiny, skip the re-verify" | Tiny fixes move boundaries green tests don't sit on. |
| "I'll leave out the agent or `model`" | Then the worker runs on your model and your price. |
| "The old test was wrong, so updating it is fine" | That's for the plan to decide, with a ruling. |
| "The tests mock the API" | Prove it with the clean-room run. |

## Files

- `scripts/orch.sh`: start, check, stamp and stray, worktrees, clean-room, old-tests, diff
- `references/plan-template.md`: the plan file (read at Plan)
- `references/worker-brief.md`: the worker brief (read at Build)
- `references/verifier-brief.md`: full and scoped verifier briefs (read at Verify)
- `references/example-run.md`: the measurements behind these rules. Background reading, not
  needed during a run
