---
name: code-orchestrator
description: Completion and verification workflow for coding work. It implements, debugs, refactors or migrates code, then proves the delivered change with evidence tied to the exact candidate. It delegates to worker agents or adds an independent reviewer only when that earns its cost. Use it whenever the user wants a feature, bug fix, refactor, migration or cross-cutting change done carefully — when they ask for a plan or acceptance criteria before code; want the work orchestrated, delegated to agents, workers or subagents, or built by a team with a planner, workers and a reviewer; want cheaper models on the routine parts; or want it verified, reviewed or double-checked before it's called done. Also use it when they name it. Load it before exploring the repo. Not for explaining code, reviewing an existing PR on its own, infrastructure orchestration such as Kubernetes, or anything that isn't code.
---

# Code Orchestrator

Deliver the requested behaviour with evidence, at the lowest practical total cost: planning,
building, review and repairs together. You are the main session. You understand the
request, choose the route, plan in proportion, build or delegate, integrate and finish.
Build it yourself unless delegating has a concrete benefit.

Everything you load is re-read on every later turn, so read references only at the step
that needs them, and keep your context small.

The mechanical guarantees live in `scripts/orch.sh` in this skill's directory. Run it as
`bash <skill-dir>/scripts/orch.sh <command>` from inside the repo; `help` lists everything.
It freezes the candidate you deliver, ties every piece of evidence to it, and refuses a
"done" result on missing, stale or mismatched evidence.

## Route: two separate decisions

| Decision | Default | Increase it when |
|---|---|---|
| **How many builders?** | You: one capable session plans and implements | Substantial independent pieces, useful context separation, or the user asks for delegation |
| **How much review?** | The relevant automated checks, and your own inspection of the diff | Behaviour is uncertain, consequences are serious, checks are weak, integration is hard, or the user asks for independent review |

- **Direct:** you build; you check. Most well-specified changes with effective tests.
- **Reviewed:** you build, then one fresh reviewer checks the candidate against the original
  request, followed by at most bounded repair. Use it for a one-line authorization change as
  readily as for a large feature: risk decides, not size.
- **Parallel:** a few workers on substantial independent pieces, with you owning the
  integration and the checks on the merged candidate.

In a 12-run pilot on two held-out tasks, all three routes passed every hidden check, and Direct
cost about a third of Reviewed (estimated). Say so if the user asks why you didn't delegate.

File count and line count don't decide the route. Resolve material ambiguity before splitting
work. Follow the user's explicit choices: mode, models, a time or spending budget. State the
route in one line when you start.

## Stop and ask the user

Continue through reversible work within the authorized goal, and adjust the plan as you
learn. Stop and ask before:

- **anything irreversible:** migrations or scripts against a real database, deleting files
  that existed before the run, rewriting git history, pushing, publishing, deploying
- **secrets:** reading `.env` or credential files, or using real keys, even "just to test"
- **real user data:** reading, copying or querying production data or a snapshot of it, even
  read-only; use synthetic fixtures
- **anything outside the repo:** other directories, global installs, system settings (scratch
  files and a throwaway environment under /tmp are fine)
- **a new dependency or a real external service** the request didn't ask for
- **a material change of scope**, or an ambiguity that changes what the user gets

If the user isn't there, do everything up to that point, record the question, and finish as
Blocked or Partial.

## The loop

1. **Start.** `orch.sh start <short-name> -- <test command>`.
   - **Exit 3, an unfinished earlier run:** read it with `orch.sh status`. If it's the same
     request and the branch hasn't moved, resume; otherwise ask which run to keep.
   - **Exit 4, uncommitted work:** ask whether to commit, stash or build on top. Never stash
     silently.
   - **Otherwise:** it branches `orch/<name>`, records BASE, and records the baseline test
     result, including tests that already fail.
   - If the existing tests might call real services, add `--offline` so even the baseline runs
     without network.
   - Save the user's request verbatim to `.orchestrator/request.md`. The reviewer and any
     resume need it.

2. **Define done.** Read only enough to know the behaviour, the interfaces and useful checks.
   - Find the repo's own CI checks (its workflow, Makefile, tox or package scripts): tests,
     formatting, lint and types, with their pinned tool versions.
   - Write short acceptance criteria someone else could check, and note known failures.
   - Keep small tasks in the conversation. Delegated, reviewed or interruptible work gets a
     durable record: `references/run-record.md` into `.orchestrator/record.md`.
   - Preserve established contracts and conventions unless the request deliberately changes
     them.
   - Where the request introduces new input handling, prefer a clear error to silently
     dropping, coercing or guessing at data. Planners have ruled comma-only CSV rows "blank",
     and the rows vanished. That rule is not permission to make existing APIs stricter.
   - Record material decisions (`Decision: <what> — <why> — <cost if wrong>`), not every
     conceivable input.

3. **Route**, as above. For Reviewed, run `orch.sh require review`. For code that calls
   external services, run `orch.sh require offline`.

4. **Delegate only with a reason.** Brief with `references/worker-brief.md`, dispatch to an
   agent from the table below, and name the agent or the `model` every time: unnamed, a
   subagent runs on your model. Keep the worker count small. For parallel workers:
   - `orch.sh stamp` first.
   - `orch.sh wt-add <task>` per worker. It makes a worktree from HEAD with copied
     dependencies, not shared ones.
   - Every path in that brief points inside its worktree.
   - `orch.sh stray` when they return.
   - Merge one at a time, then `orch.sh wt-finish <task>`.
   - Don't use the Agent tool's `isolation: "worktree"`: by default it starts from the
     remote default branch, not your HEAD.

5. **Build and check as you go.** For a bug, get a focused failing reproduction first when
   practical. Run targeted tests while editing. Commit the intended files by name, never
   `git add -A`. Never weaken, skip or delete a test to get green. When an existing test
   must change because the requested behaviour changes, record it:
   `path  reason` in `.orchestrator/approved-test-changes`. When the skipped or executed
   count moves for a reason you can name (a new test that skips without an optional
   dependency, like its neighbours), record `count:skipped  reason` or
   `count:executed  reason`. The report lists every approval.

6. **Check the exact candidate.** `orch.sh check -- <test command>`. It refuses leftovers,
   freezes HEAD as the candidate, runs the suite against it, voids the result if the run
   changed the tree, and audits test changes. Treat each flag as a signal to read, not a
   verdict.
   - Anything you change afterwards needs a new `check`.
   - Run the repo's CI checks on the candidate with `orch.sh run <label> -- <command>`, using
     the pinned versions (in a throwaway environment under /tmp if they aren't installed).
     A formatting or lint failure fails CI too: in the routing pilot, 3 of 6 first drafts of
     one task failed the repo's pinned `black` check. Record other evidence the same way: a
     reproduction, a benchmark.
   - `orch.sh fresh [--offline] -- <tests>` runs a fresh checkout, which catches reliance on
     untracked files, local secrets or the network.
   - `--offline` is enforced and verified, or refused. `fresh` does not sandbox the
     filesystem. Where you promise isolation the helper can't give, use the host's sandbox,
     or say plainly that it wasn't isolated.

7. **Independent review (Reviewed mode).**
   - Run `orch.sh diff`, then brief the `orch-verifier` agent from
     `references/reviewer-brief.md`.
   - It gets the original request verbatim, the relevant contracts, your criteria, your
     decisions labelled as decisions, the commands, and the candidate patch.
   - It never gets a worker's self-assessment. It may challenge criteria that miss or
     contradict the request. A clean review is a valid result.
   - Record the outcome against the candidate: `orch.sh record review pass|fail "<summary>"`.

8. **Repair, bounded.** Fix confirmed failures and regressions only, grouping related ones.
   - Open each whole cycle with `orch.sh repair "<reason>"`. The budget is 2 cycles for the
     whole run, and a new finding doesn't reset it.
   - After each fix, run `check` again, re-test the reproduced failure and its neighbours, and
     get a targeted re-review when the fix is risky (`orch-rechecker`, then
     `orch.sh record recheck pass|fail`).
   - If a repair doesn't work, diagnose before retrying: a missing requirement, the
     environment, model capability, a flaky test, or a wrong fix. Then change that.
   - Stop when the budget is spent or when progress stops, and honour the user's own time or
     spend budget.

9. **Finish.** `orch.sh gate`, then `orch.sh finish done|partial|blocked "<note>"`. `done` is
   refused unless the gate passes. The record in `.orchestrator/` is kept; only finished
   worktrees are removed.

## Report

```
## <Done | Partial | Blocked>: <one line>
- Built: <2–4 lines>
- Criteria: N/M met — evidence: candidate <commit>, <command> → <result> (<log>)
- Known failures: <pre-existing, disclosed> or "none"
- Test changes: <approved changes with reasons> or "none"
- Review: <not reviewed | reviewer's blocking findings and what happened to each; optional ones left>
- Not verified: <manual or environment-blocked checks, with steps for the user> or "none"
- Decisions: <material decisions> or "none"
- Branch: orch/<name> from <branch> at <BASE>, not pushed. To take it: git merge orch/<name>
- Route and models: <Direct | Reviewed | Parallel>; agents by model; cost if known (a local estimate, not a bill)
```

A failed check doesn't become a passing one through wording. Unrelated failures are disclosed,
and count as acceptable only if the requirement allows them.

## Agents and models

The main session is whatever model the user chose. Keep it.

| Agent (`subagent_type`) | Use | Set in `agents/` |
|---|---|---|
| `orch-worker-haiku` | a bounded mechanical task, where writing the brief is clearly less work than doing it | Haiku; no nested agents |
| `orch-worker-sonnet` | a substantial delegated piece; a repair that needs a second pair of hands | Sonnet, medium effort; no nested agents |
| `orch-verifier` | the independent review | Opus, extra-high effort; no Edit/Write/Agent tools |
| `orch-rechecker` | a targeted re-review after a risky repair | Sonnet, high effort; no Edit/Write/Agent tools |

The runtime enforces the tool limits and turn caps in these files: a probe agent couldn't
call Write or Agent, and it stopped at its turn cap. But Bash can still write files. So
reviewers aren't strictly read-only: `orch.sh gate` catches any change they make to the tree.
These model and effort settings are candidates, not proven optima: extra-high review effort
hasn't yet shown a measurable gain. If the agents aren't installed, pass `model` instead and
say the effort was the default.

**Agents in the background.** Claude Code can move a long-running agent to the background,
even one you dispatched in the foreground. In a headless session (`claude -p`), after your
last turn it waits for such an agent only up to an idle limit (10 minutes by default), then
stops it and drops its result. If a result you need never arrives, report that step as not
done.

## Rationalisations to refuse

| You'll think | Actually |
|---|---|
| "More agents make it more reliable" | Delegated code has introduced the very bugs the reviewer then paid to catch. Delegate for a reason. |
| "The tests passed a minute ago" | Evidence belongs to one candidate. Anything changed since needs a new `check`. |
| "It's only a skip marker" | A skipped or loosened test is how broken code passes. Approve it with a reason, or revert it. |
| "The reviewer found nothing, so it didn't look" | A clean review is valid. Judge findings by their evidence. |
| "One more repair will do it" | The budget covers the whole run. Diagnose, or finish Partial. |
| "The clean room proves it's offline" | Only a verified `--offline` run proves no network access, and nothing here sandboxes the filesystem. |

## Files

- `scripts/orch.sh`: start, check, run, fresh, tests, diff, record, repair, gate, finish,
  and the parallel-worker commands
- `references/run-record.md`: the durable record, for delegated, reviewed or interruptible work
- `references/worker-brief.md`: read only when delegating
- `references/reviewer-brief.md`: read only for an independent review or re-check
