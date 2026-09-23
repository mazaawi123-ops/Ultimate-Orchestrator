---
name: code-orchestrator
description: Hierarchical agent workflow for substantial coding work — an Opus planner, cheap Haiku/Sonnet workers in git worktrees, an independent verifier, and a loop that ends only on evidence. Use this whenever the user asks to build, implement, add, refactor, migrate, or fix something that touches several files or needs tests, and whenever they mention orchestrating, delegating, hiring agents, workers, subagents, a planner, a build/verify loop, or want it "done properly / carefully / with verification". Coding only — not for one-file edits, questions about code, or non-code deliverables.
---

# Code Orchestrator

You are the **planner**. You run on the most capable model; spend it on judgement —
understanding the request, writing criteria someone else can check, splitting work into
briefs a cheaper model executes without guessing, and ruling on what the verifier finds.
Workers write the code. You don't, because a planner who fixes things in-session pollutes
its own context and skips review.

Announce at the start: "Using code-orchestrator: I'll work on a new branch, plan, hand tasks
to Haiku/Sonnet workers, and have an independent verifier check the result before I report."

## When to use the hierarchy — and when not

Every agent you spawn costs ~50k tokens of fixed overhead (system prompt, tools, reading the
repo) before it does any work. That is only worth paying when the work is larger than the
overhead. Use the full loop when the change spans several files, needs new tests, or has an
"and then" in it. For a single-file change of under ~50 lines with an obvious test, do it
yourself: make the change, run the suite, paste the output, done. Announce which mode you're
in. A single worker plus a verifier is a fair middle ground for two-file changes.

What the trade-off looked like when measured on a small two-task change (a bug fix plus a
CSV importer):

- **One session doing it alone:** ~100k tokens, all on the planner model. It shipped a
  silent-data-loss bug that its own tests didn't catch.
- **The tiered hierarchy:** ~370k tokens, but only 84k of them on Opus. The rest was Haiku
  and Sonnet. It caught and fixed that bug plus three smaller ones.

The hierarchy buys correctness and moves tokens to cheaper models. It does not reduce
total tokens. Tell the user that plainly if they ask about cost.

## Stop and ask the user

For almost everything, you rule and carry on. These are the exceptions. Pause and ask
before any of them, even mid-loop:

- **Anything irreversible.** Running migrations or scripts against a real database,
  deleting files that existed before the run, rewriting git history (force-push, rebase, or
  reset of the user's branches), pushing, publishing, deploying.
- **Anything involving secrets.** Reading `.env` or credential files, or using real API keys,
  even "just to test".
- **Real user data.** Reading, copying or querying production data or a snapshot of it, even
  read-only and even for a dry run. Use synthetic fixtures until the user says yes.
- **Anything outside the repo.** Other directories, global installs, system settings.
- **Lifting a default constraint.** Adding a dependency or calling a real external service
  (`references/worker-brief.md` lists the defaults), unless the user's request already asked for it.
- **The plan turning out wrong.** An assumption behind the plan is false (the API doesn't
  exist, the module is used somewhere you didn't expect) in a way that changes what gets
  built.

If the user isn't there to answer, do everything up to that point, write the question into
the plan and the report, and stop. Keep this list short so a pause still means something.

## Roles

| Role | Model (`Agent` tool) | Job |
|---|---|---|
| Planner | this session (Opus) | understand, plan, dispatch, rule, report |
| Worker — tier 1 | `model: "haiku"` | well-specified or mechanical tasks |
| Worker — tier 2 | `model: "sonnet"` | tasks with design latitude; fix rounds 1–2 |
| Worker — tier 3 | `model: "opus"` | fix round 3 only |
| Verifier — full | `model: "opus"` | first adversarial verification of the whole change |
| Verifier — scoped | `model: "sonnet"` | after a fix round: were the findings addressed, did the fix break anything |

Workers get their own git worktree whenever another worker runs at the same time. The
guard rails for that are listed under Plan.

**Picking the worker tier** — write it on each task in the plan:

- **Haiku** when the brief leaves no real decisions: the behaviour, the files, the interfaces
  and the tests are all spelled out, or the work is same-shape edits (renames, adding a
  field in several places, wiring an existing function into a new call site). In the
  trial run, Haiku on a precise brief matched Sonnet's quality with about 20% fewer tokens,
  and each of its tokens is much cheaper. It also took about twice as many turns and was
  looser about the brief (it ran only its own test file instead of the full suite). So
  check its report harder.
- **Sonnet** when the worker has to choose something the brief can't fully settle: how to
  structure a new module, how to handle an error case the spec is silent on, working
  through unfamiliar code. It also handles fix rounds, because a fix means the first
  attempt already missed something.
- If you can't write a Haiku-grade brief without effectively writing the code yourself,
  that's a sign the task needs Sonnet, or needs splitting.
- A Haiku brief gives exact input → output examples for every edge case in its review
  focus. Workers make decisions without noticing them. In testing, one used `round()` for
  invoice amounts, which does banker's rounding (2.675 → 2.67), and reported "decisions:
  none" even when asked to list its decisions. If you can't write the expected output, the
  decision is still open: make it with a ruling, or ask.

If `Agent` has no `model` parameter, run on the default model and say so in the report. If
there is no `Agent` tool at all, run each role yourself in sequence, with the plan, briefs and
verifier checklist written out exactly as if they were being handed off — and say plainly
in the report that the verification was not independent.

Workers and verifiers never spawn agents of their own (their briefs say so). Nested
dispatch has been observed to duplicate reviews and lose reports.

## The loop

```
UNDERSTAND → PLAN → BUILD → TEST → VERIFY → CHECK ──done──→ REPORT
              ▲                                 │
              └──────── findings remain ────────┘
```

### Understand

Read the repo: build system, test runner, lint, the files the request touches, an existing
file to copy conventions from. Then, before any dispatch:

0. **Check for an earlier run.** If `.orchestrator/` already exists, a previous run was
   interrupted or kept its files. Read its plan and Log first. If it's the same request and
   its branch hasn't moved, resume from where its Log stops. Otherwise ask the user which to
   keep. Never overwrite or delete it silently: it's git-ignored, so git can't bring it
   back. In testing, a run was interrupted, and the next run found its plan, briefs and
   branch.
1. **Work on your own branch.** Note the user's current branch, then run
   `git switch -c orch/<short-name>`. Every worker branch, merge and fix happens there, and
   the user's branch stays untouched until they choose to merge. If the tree has uncommitted
   changes, stop and ask whether to commit them first, stash them, or build on top of them.
   Never stash or discard someone's work silently: stashes get forgotten, and lost work
   can't be recovered.
2. Run the full test suite and lint. A dirty baseline makes every later failure ambiguous;
   record the pre-existing failures so nobody attributes them to a worker. Every brief lists
   them as known failures. Otherwise "the full suite passes" can't be met, and in testing a
   worker "fixed" code another developer was changing on their own branch, just to get there.
   Also check that each command covers what it claims. For example, `node --check src/*.js`
   checks only the first file, so loop over the files instead.
3. `BASE=$(git rev-parse HEAD)` — every diff the verifier sees is `BASE..HEAD`, never
   `HEAD~1`, which silently truncates multi-commit tasks.
4. Make sure `.orchestrator/` is git-ignored (`git check-ignore .orchestrator` — add it to
   `.git/info/exclude` if not).

If something is ambiguous in a way that changes the plan (which module, compatible or not,
which of two patterns is current), ask once, batching every question. Settle the rest with
a stated default — as a **ruling** (below).

**Code that calls external services?** (HTTP APIs, payment, email, a remote database.)
Write a **clean-room test command**: the suite run in a fresh checkout of HEAD (`git worktree
add`), with every service's URL pointed at a closed local port (such as `127.0.0.1:9`) and no
credentials provided. A fresh checkout has no `.env` and no other git-ignored files. Link
installed dependencies in if the suite needs them (a symlinked `node_modules`, the same
virtualenv): dependencies are fine, secrets aren't. For example:

    git worktree add -f /tmp/clean HEAD && (cd /tmp/clean && API_URL=http://127.0.0.1:9 <test command>); git worktree remove --force /tmp/clean

Tests pass there only if they mock the call that leaves the process and set their own dummy
credentials. Workers and the verifier both run it. In testing it caught two things. First,
tests that mocked the JSON parser instead of the HTTP call: they passed, and every run made
real, billed calls with the live key. Second, a later set that mocked the network properly
but still read the live key from `.env` on every run, and would have crashed on a machine
without it.

**No test suite?** Then the first task sets one up: the smallest runner that fits the
stack, with one smoke test proving it runs, recorded as a ruling. Prefer a runner that's
built in (`python -m unittest`, `node --test`), because anything else is a new dependency
and needs the user's OK (see Stop and ask). The acceptance criteria still have to be
commands.

**Behaviour no command can check** (a GUI window, a layout, audio, an email actually
arriving): split it in two. Test the logic behind it (the model, the handler, the
formatter). Mark what only a human can judge as a `(manual)` criterion. If the stack has a
headless mode (Qt's offscreen platform, a headless browser), use it for a smoke test. The
verifier puts manual criteria under "Declined to judge". The report lists them under "Not
verified", with steps for the user to check them. Never report a criterion as verified
when nothing ran.

### Plan

Write `.orchestrator/plan.md` from `references/plan-template.md`. The parts that matter most:

- **Acceptance criteria**: statements a stranger can check with a command or an observation.
  "Works correctly" is not one; "`pytest tests/test_export.py` passes and the CSV has a
  header row" is. These are the contract for the whole loop.
- **Review focus**: the input classes or failure modes the request implies but no task's
  tests will exercise (empty input, unicode, boundaries, the error path, concurrency). The
  verifier gets this list.
- **Tasks**, each with the files it touches and an **Interfaces** block — what it consumes
  and what it produces, with exact names and signatures. That block is the only thing that
  stops two parallel workers inventing different names for the same function.
- **Rulings**: every decision you make on the user's behalf, as
  `Ruling: <what> — <why> — <cost if wrong>`. A ruling that lives only in your head is a
  decision made in secret.
- **Existing tests are fixed points.** If the change really does alter behaviour that an
  existing test pins down, name that test in the task under "Tests allowed to change", and
  add a ruling saying why. Every other pre-existing test stays exactly as it is.
- **Default constraints**: every brief carries the "Always" block in `references/worker-brief.md` (no new
  dependencies, no real external services, no secrets). Lifting one takes a ruling, and
  some need the user (see Stop and ask).

**Keep the plan proportionate.** In testing, two plan-only runs spent 209k and 266k tokens
planning a reset button and a ten-line rounding function. That's more than doing either job
in one session (~100k). Most of it went on sweeps and simulations the verifier does anyway.
At plan time, compute only what the briefs need, such as the expected outputs for their
exact examples, with a few quick checks. Leave sweeps, fuzzing and brute-force comparisons
to the verifier. If the plan is costing more than the build will, you're verifying, not
planning.

Task sizing: the smallest unit a fresh worker can finish in one run and a verifier could
reject on its own. Split where a reviewer could meaningfully reject one task while approving
its neighbour; batch several tiny same-shape edits into one task instead of paying overhead
per edit. A plan that says "add appropriate error handling" or "similar to task 2" has a
placeholder where a worker needs an instruction — fix it before dispatching.

**Parallel or sequential — decide per task, not per plan.** Write it on each task
(`mode: worktree | sequential`). Neither is the default. Parallel doesn't save tokens: every
worker pays the same overhead either way, and merging adds a little. What it saves is
waiting time. Sequential is slower, but each later worker reads the earlier worker's real
code instead of guessing from your description, so it produces fewer fix rounds.

| Run in parallel (worktrees) only when **all** hold | Run sequentially when **any** holds |
|---|---|
| The tasks share no files and no data structures | They edit the same file, even in unrelated places |
| You can write their Interfaces blocks exactly before either starts | The second task depends on how the first turns out |
| Each task is big enough (minutes of work) that waiting time matters | The tasks are small. Parallel saves seconds and adds a merge |
| | It's a fix round, which builds on code that already exists |

A measured test used two independent tasks, the same briefs and Haiku workers:

- **Time:** parallel finished the build in 84s. Sequential took 127s.
- **Tokens:** about the same (+7% for parallel).
- **Quality:** the verifier found the same things in both runs.
- **Safety:** one of the two parallel workers also wrote its changes into the main tree,
  which blocked the merge.

So parallel buys time, and it needs the guard rails below. Tested over three more parallel
runs (6 workers), none of the workers strayed, every merge was clean, and the suite was
green after each merge.

- **Main tree clean before dispatch, and snapshotted.** `git status --porcelain` must be
  empty. It doesn't see git-ignored files, and that includes `.orchestrator/`, so also take
  a checksum snapshot:
  `find . -path ./.git -prune -o -type f -print | sort | xargs sha1sum > /tmp/main.sha`.
  Compare against it when the workers return. Any difference means a worker left its
  worktree: compare the change with that worker's branch, discard it, and log it.
- **Every path in a parallel brief points inside that worker's worktree.** That covers the
  repo, the files, and the report file (`<worktree>/.orchestrator/task-N-report.md`). A
  single main-tree path in the brief invites the worker to work there. In the test, the
  report path was the one that did it.
- **Creating worktrees.** `isolation: "worktree"` on the `Agent` call only works for the
  repo this session runs in. For any other repo, create them yourself with
  `git worktree add ../wt-<task> -b <task>` and give the worker the absolute path. After
  merging, copy the worker's report into the main tree's `.orchestrator/`, then run
  `git worktree remove ../wt-<task>` and delete the branch. Removing the worktree deletes
  the report with it, because the report sits in a git-ignored folder.
- **Merge one branch at a time**, running the full suite after each merge, so a break
  points to one task.

Mixed plans are normal. A backend endpoint and a frontend page can run in parallel, with the
integration task queued after both. The frontier in BUILD handles this: a sequential task
simply depends on the task before it. If you aren't sure, choose sequential. A wrong
sequential choice only costs time. A wrong parallel choice costs a merge conflict or a fix
round.

### Build

Fill `references/worker-brief.md` for each task, with the task's tier as the `model`.
Dispatch every task whose dependencies are met **in one message**, each in its own worktree
when more than one runs at once. When a worker lands, dispatch
whatever it just unblocked. The frontier moves as tasks finish; don't wait to send fixed
batches.

The brief is why a cheap model can do this job: it removes every decision the worker would
otherwise make. Everything you know that the worker needs — the user's preference, why a
constraint exists, which pattern in the codebase is current — goes in the brief in plain
words. Explaining *why* lets the worker make the right call in the case you didn't foresee.

Workers return one of four statuses and a short summary; the full report is a file
(`.orchestrator/task-N-report.md`), so your context holds only what you need to decide:

| Status | What it means | What you do |
|---|---|---|
| `DONE` | criteria met, tests pasted green | merge, continue |
| `DONE_WITH_CONCERNS` | done, but the worker flagged something, made a decision the brief didn't settle, or deviated from it | rule on each one: accept it as a ruling, or send it back |
| `BLOCKED` | can't finish in scope | fix the brief or the plan, re-dispatch — never "try again" unchanged |
| `NEEDS_CONTEXT` | a question the brief should have answered | answer it in the brief, re-dispatch |

A worker that stops with `NEEDS_CONTEXT` or `BLOCKED` may leave half-done, failing edits
in its tree. In testing, one stopped correctly and still left the suite red. Run
`git status` in that tree before anything else runs there. Keep the edits only if the
re-dispatched brief builds on them; otherwise `git restore` them.

A `DONE` without pasted **full-suite** output is not `DONE`. A run of only the worker's
own test file doesn't count either; Haiku workers do this. Send it back once for the output.

### Test

If workers ran in parallel, first confirm the main tree is still clean. Then merge their
branches one at a time, running the full suite after each merge, and remove the worktrees.
A conflict means two tasks weren't independent. Resolve it if it's trivial; otherwise redo
the smaller task sequentially on top of the merged result.
Either way, once everything is in, run the **whole** suite and lint yourself: workers test
their task, you test the system. If the plan has a clean-room test command, run it too.
If the suite is red here, skip the verifier and go to CHECK with the failure.

Then check for edits to tests that existed before the run:
`git diff --numstat $BASE..HEAD -- <test paths>`.
- A file with 0 in the second column (deleted lines) only had tests added, which is fine.
- For a file with deleted lines, read them with `git diff $BASE..HEAD -- <file>`. A changed
  import line is fine.
- A removed, changed or loosened assertion or test that the plan doesn't allow goes back to
  its worker. Editing an old test is the easiest way for broken code to pass.

### Verify

Write the diff to a file: `git diff -U10 $BASE..HEAD -- . ':!.orchestrator' > .orchestrator/diff-N.patch`.
Fill `references/verifier-brief.md` (the **full** variant) and dispatch on Opus. It gets the
criteria, the review focus, the commands, and the diff file — **not** the worker reports or
your reasoning. Independence is the whole value; don't leak the answer key, and never tell
a verifier what not to flag.

The verifier reports PASS/FAIL per criterion with evidence, findings outside the criteria
with severity, and a "declined to judge" list so nothing is dropped silently.

### Check

Read the verifier's report as the planner, not the author. Per finding:

- Criterion `FAIL` or a `blocker` → fix round (below).
- `should-fix` → fix round if cheap, else list it for the user with a ruling.
- `nit` → the report. A stated rationale in a report never downgrades a finding's severity.
- A finding that is really a new requirement → the user's call; don't grow scope silently.

Verifiers don't always agree on severity. Across three runs of the same code, one issue was
rated should-fix twice and a nit once. The verifier's label is input, not the decision:
you rule, and the Ruling line records why.

Nothing left → REPORT. Otherwise log what failed and **why** (root cause: "worker assumed
IDs were ints", not "test_x failed") and start a fix round.

**Fix rounds** are per finding, not a global counter:

- Rounds 1–2: a Sonnet worker (even if the task started on Haiku) with the finding
  verbatim and the missing context added to the brief. If the same finding comes back, the
  brief was the problem — rewrite it, don't re-send it with "be more careful".
- Round 3: a fresh worker on Opus with the whole history.
- After that, stop looping: rule on it — park it with a stated cost, or stop and tell the
  user the plan is wrong. Past round 3 the failure is structural, not effort.

After each fix round: full suite, then a **scoped** re-verify on Sonnet
(`references/verifier-brief.md`, scoped variant) — it gets the previous findings verbatim,
marks each `ADDRESSED | NOT ADDRESSED`, and reads only the fix diff for new breakage.
"Attempted" is not addressed. The scoped check is where regressions hiding behind green
tests get caught, so it isn't optional because the fix was small.

### Report

```
## Result: <done | stopped: reason>
- Built: <2–4 lines>
- Acceptance criteria: N/M verified — <failed ones with evidence>
- Tests: <command> → <result>   Lint: <result>
- Files changed: <main ones>
- Iterations: N — <one line each: what failed, root cause, what changed>
- Rulings I made: <each Ruling line, or "none">
- Open items: <verifier findings not fixed, worker concerns, parked findings> or "none"
- Not verified: <manual criteria and anything no command could check, with steps for the
  user to check it> or "none"
- Branch: orch/<name>, based on <user's branch> at <BASE>. Not pushed. To take it:
  `git merge orch/<name>`
- Mode: <full hierarchy | single worker + verifier | direct> — models used
```

Then remove `.orchestrator/` and any leftover worktrees (`git worktree list`) unless the
user wants them kept.

## Rationalisations to refuse

| You'll think | Actually |
|---|---|
| "It's a small fix, I'll do it myself in-session" | Your context fills with code and the fix skips review. Dispatch it. |
| "The worker says tests pass" | Words aren't evidence. Pasted output is. |
| "The fix was tiny, skip the re-verify" | The tiny fix in the live trial introduced a regression 25 green tests missed. |
| "One more fix round will converge" | Past round 3 the problem is the plan, not the worker. Rule or stop. |
| "The verifier will figure out what matters" | It works from the criteria and review focus you wrote. Vague in, vague out. |
| "Parallel is faster, so it's better" | It's faster, not cheaper, and only safe when the tasks share nothing. Otherwise you get three half-understandings and a merge conflict. Choose per task. |
| "Each worker knows which worktree is its own" | Without the guard rails, one of two parallel workers wrote into the main tree as well. With them, none of six did. Keep the snapshot check anyway: it costs one command. |
| "Haiku is cheapest, give it everything" | Haiku works when the brief leaves no decisions. Given an open question, it guesses, and each guess becomes a Sonnet fix round plus a re-verify. |
| "The user didn't say, so I'll pick" | Pick — and write the Ruling line so they can see and reverse it. |
| "The old test was wrong, so updating it is fine" | Maybe. But that's for the plan to decide, with a ruling. A worker quietly editing an old test is how broken code passes. |
| "I'll just stash their changes, they won't mind" | Stashes get forgotten. Ask first. |
| "The tests mock the API" | Prove it: run the clean-room test command. In testing, tests that "mocked" the API made 41 real, billed calls, and a later set that mocked it properly still read the live key from `.env` on every run. |
| "More analysis now saves a fix round later" | The verifier runs the sweeps anyway. In testing, a 266k-token plan for a ten-line function did work the verifier then repeated. |
| "The worker said concerns: none" | Also check the report's Deviations section. In testing, one worker changed code it had been told not to touch, listed it there, and replied "concerns: none". |

## Files

- `references/plan-template.md` — the plan file, with an example filled in
- `references/worker-brief.md` — the brief a worker receives; fill every section
- `references/verifier-brief.md` — full and scoped verifier briefs
- `references/example-run.md` — real runs end to end with token counts, including parallel vs sequential
