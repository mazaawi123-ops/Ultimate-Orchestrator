---
name: code-orchestrator
description: Plan-build-verify loop for coding work that spans several files and has or needs tests. It plans the change, hands the building to cheaper subagent workers, and has an independent verifier check the result before reporting. Use it when the user wants a feature, bug fix, refactor or migration across several files, and especially when they ask for the work to be orchestrated, delegated to agents, workers or subagents, planned first, or done carefully with verification. Not for single-file edits, quick fixes, questions about code, code review alone, or anything that isn't code.
---

# Code Orchestrator

You are the **planner**. Spend your judgement where it matters:
- understanding the request
- writing criteria someone else can check
- splitting the work into briefs a cheaper model can carry out without guessing
- ruling on what the verifier finds

Workers write the code, not you: a planner who fixes things in-session fills its context
with code and skips review.

**Before anything else, check your model.** The planner is the one place the hierarchy
spends a strong model. If this session isn't running on Opus, say so first and suggest
switching (`/model opus`): a weaker planner writes vaguer briefs, and cheap workers get
vague briefs wrong. Continue only if the user says to.

Announce: "Using code-orchestrator: I'll work on a new branch, plan, hand tasks to
Haiku/Sonnet workers, and have an independent verifier check the result before I report."

The mechanical steps are in `scripts/orch.sh` in this skill's directory: the stray-write
check, worktrees, the clean-room run, the old-test check and the diff. Run it as
`bash <skill-dir>/scripts/orch.sh <command>` from inside the repo. If you can't run it, read
it: each command is a few lines of git you can run by hand.

## When to use the hierarchy, and when not

Every agent re-reads its whole context on every turn, so each worker, verifier and fix
round processes hundreds of thousands of tokens, mostly cheap cache reads. That only pays
off when the work is bigger than the overhead.

- **Full loop:** the change spans several files, needs new tests, or has an "and then" in it.
- **Single worker plus verifier:** a two-file change.
- **Do it yourself:** a single-file change of under ~50 lines with an obvious test. Make the
  change, run the suite, and paste the output.

Say which mode you're in.

The hierarchy buys evidence and a second pair of eyes, not savings. On three small
two-task changes, the loop cost $2.1–2.9 per task. The same prompt without the skill, with
Opus doing its own delegating, cost $1.3–2.4. Code correctness came out equal on every
graded check. The loop's verifier caught one real bug the other run shipped: a `wrap()`
that hung on long words. The loop also produced written criteria, per-criterion evidence
and visible rulings. Haiku did most of the building, but the Opus planner and verifier were
still 68–87% of the bill. Say this plainly if the user asks about cost.

## Stop and ask the user

For almost everything, you rule and carry on. These are the exceptions. Pause and ask
before any of them, even mid-loop:

- **Anything irreversible.** Running migrations or scripts against a real database,
  deleting files that existed before the run, rewriting git history (force-push, or a rebase
  or reset of the user's branches), pushing, publishing, deploying.
- **Anything involving secrets.** Reading `.env` or credential files, or using real API keys,
  even "just to test".
- **Real user data.** Reading, copying or querying production data or a snapshot of it, even
  read-only and even for a dry run. Use synthetic fixtures until the user says yes.
- **Anything outside the repo.** Other directories, global installs, system settings.
- **Lifting a default constraint.** Adding a dependency or calling a real external service
  (`references/worker-brief.md` lists the defaults), unless the user's request already asked
  for it.
- **The plan turning out wrong.** An assumption behind the plan is false in a way that
  changes what gets built. For example, the API doesn't exist, or the module is used
  somewhere you didn't expect.

If the user isn't there to answer, do everything up to that point, write the question into
the plan and the report, and stop. Keep this list short so a pause still means something.

## Roles

| Role | `Agent` call | Job |
|---|---|---|
| Planner | this session (Opus) | understand, plan, dispatch, rule, report |
| Worker, tier 1 | `model: "haiku"` | well-specified or mechanical tasks |
| Worker, tier 2 | `model: "sonnet"` | tasks with design latitude; fix rounds 1–2 |
| Worker, tier 3 | `model: "opus"` | fix round 3 only |
| Verifier, full | `model: "opus"` | first adversarial verification of the whole change |
| Verifier, scoped | `model: "sonnet"` | after a fix round: were the findings addressed, did the fix break anything |

**Pass `model` on every dispatch.** A subagent without one inherits your model. A worker
dispatched without `model` quietly runs on Opus and costs several times what the plan said.

**Picking the worker tier.** Write the tier on each task in the plan:

- **Haiku** when the brief leaves no real decisions. The behaviour, the files, the
  interfaces and the tests are all spelled out, or the work is same-shape edits (renames,
  a field added in several places). On a precise brief Haiku matched Sonnet's quality.
  It is looser about the brief, though (it tends to run only its own test file), so
  check its report harder.
- **Sonnet** when the worker has to choose something the brief can't fully settle: how to
  structure a new module, an error case the spec is silent on, unfamiliar code. It also
  handles fix rounds, because a fix means the first attempt already missed something.
- If you can't write a Haiku-grade brief without effectively writing the code, the task
  needs Sonnet, or needs splitting.
- **A Haiku brief gives exact input → output examples** for every edge case in its review
  focus. Workers make decisions without noticing them. One used `round()` on invoice
  amounts, which rounds 2.675 down to 2.67, and still reported "decisions: none". If you
  can't write the expected output, the decision is still open: make it with a ruling, or ask.

If `Agent` has no `model` parameter, run on the default model and say so in the report. If
there is no `Agent` tool at all, run each role yourself in sequence. Write the plan, briefs
and verifier checklist out exactly as if handing them off, and say plainly in the report
that the verification was not independent.

Workers and verifiers never spawn agents of their own; their briefs say so. Nested dispatch
has duplicated reviews and lost reports.

## The loop

```
UNDERSTAND → PLAN → BUILD → TEST → VERIFY → CHECK ──done──→ REPORT
              ▲                                 │
              └──────── findings remain ────────┘
```

### Understand

Read the repo: the build system, test runner and lint, the files the request touches, and
an existing file to copy conventions from. Then, before any dispatch:

0. **Check for an earlier run.** If `.orchestrator/` already exists, a previous run was
   interrupted or kept its files. Read its plan and Log first. If it's the same request and
   its branch hasn't moved, resume from where its Log stops. Otherwise ask the user which
   one to keep. Never overwrite or delete it silently: it's git-ignored, so git can't bring
   it back.
1. **Work on your own branch.** Note the user's current branch, then
   `git switch -c orch/<short-name>`. Every worker branch, merge and fix happens there. The
   user's branch stays untouched until they choose to merge. If the tree has uncommitted
   changes, stop and ask whether to commit them first, stash them, or build on top of them.
   Never stash or discard someone's work silently: stashes get forgotten.
2. **Baseline.** Run the full test suite and lint, and record the pre-existing failures so
   nobody blames them on a worker. Every brief lists them as known failures. Without that
   list, "the full suite passes" can't be met, and a worker will "fix" someone else's code
   to get there. Check that each command covers what it claims: `node --check src/*.js`
   checks only the first file.
3. `BASE=$(git rev-parse HEAD)`. Every diff the verifier sees is `BASE..HEAD`, never
   `HEAD~1`, which silently truncates multi-commit tasks.
4. Make sure `.orchestrator/` is git-ignored (`git check-ignore -q .orchestrator/x`). If it
   isn't, add `.orchestrator/` to `.git/info/exclude`.
5. **Write repo notes** in `.orchestrator/notes.md` as you read, in 40 lines or fewer: the
   layout, the test and lint commands, the conventions with a file to imitate, the key
   files, and anything surprising. Paste them into every brief, so workers don't each pay
   to rediscover the same facts. Paste the text rather than a path: worktrees don't contain
   `.orchestrator/`.

If something is ambiguous in a way that changes the plan (which module, whether to stay
compatible, which of two patterns is current), ask once, batching every question. Settle the
rest with a stated default, as a **ruling** (below).

**Code that calls external services?** (HTTP APIs, payment, email, a remote database.) Use
the clean-room run:

    bash <skill-dir>/scripts/orch.sh clean-room API_URL=http://127.0.0.1:9 -- <test command>

It runs the suite in a fresh worktree of HEAD. There's no `.env` and no credential-like
environment variables, and each service URL points at a closed port. Dependency folders are
linked in: dependencies are fine, secrets aren't. Tests pass there only if they mock the call
that leaves the process and set their own dummy credentials. Green tests prove neither: some
have mocked the JSON parser while making real, billed calls. Write the exact command into the
plan, because workers and the verifier both run it.

**No test suite?** Then the first task sets one up: the smallest runner that fits the stack,
with one smoke test proving it runs, recorded as a ruling. Prefer a built-in runner
(`python -m unittest`, `node --test`), because anything else is a new dependency and needs
the user's OK. The acceptance criteria still have to be commands.

**Behaviour no command can check** (a GUI window, a layout, audio, an email actually
arriving): split it in two.
- Test the logic behind it: the model, the handler, the formatter.
- Mark what only a human can judge as a `(manual)` criterion.
- If the stack has a headless mode, use it for a smoke test.

The verifier puts manual criteria under "Declined to judge". The report lists them under
"Not verified", with steps for the user. Never report a criterion as verified when nothing ran.

### Plan

Write `.orchestrator/plan.md` from `references/plan-template.md`. The parts that matter most:

- **Acceptance criteria**: statements a stranger can check with a command or an observation.
  "Works correctly" is not one; "`pytest tests/test_export.py` passes and the CSV has a
  header row" is. These are the contract for the whole loop.
- **Review focus**: the input classes or failure modes the request implies but no task's
  tests will exercise (empty input, unicode, boundaries, the error path, concurrency). The
  verifier gets this list.
- **Tasks**, each with the files it touches and an **Interfaces** block: what it consumes
  and what it produces, with exact names and signatures. That block is the only thing that
  stops two parallel workers inventing different names for the same function.
- **Rulings**: every decision you make on the user's behalf, as
  `Ruling: <what> — <why> — <cost if wrong>`. A ruling that lives only in your head is a
  decision made in secret.
- **Existing tests are fixed points.** If the change really does alter behaviour that an
  existing test pins down, name that test in the task under "Tests allowed to change" and
  add a ruling saying why. Every other pre-existing test stays exactly as it is.
- **Default constraints**: every brief carries the "Always" block from
  `references/worker-brief.md`: no new dependencies, no real external services, no secrets.
  Lifting one takes a ruling, and some need the user (see Stop and ask).

**Keep the plan proportionate.** At plan time, compute only what the briefs need, such as
the expected outputs for their exact examples, with a few quick checks. Leave sweeps,
fuzzing and brute-force comparisons to the verifier, which runs them anyway. Plan-only runs
have spent 209k and 266k tokens on a reset button and a ten-line rounding function, more
than doing either job in one session. If the plan is costing more than the build will,
you're verifying, not planning.

**Task sizing:** the smallest unit a fresh worker can finish in one run and a verifier could
reject on its own. Split where a reviewer could reject one task while approving its
neighbour. Batch several tiny same-shape edits into one task instead of paying overhead per
edit. A plan that says "add appropriate error handling" or "similar to task 2" has a
placeholder where a worker needs an instruction. Fix it before dispatching.

**Parallel or sequential: decide per task, not per plan.** Write it on each task
(`mode: worktree | sequential`); neither is the default. Parallel saves waiting time, not
tokens. Sequential is slower, but each later worker reads the earlier worker's real code
instead of guessing from your description, so it produces fewer fix rounds.

| Run in parallel (worktrees) only when **all** hold | Run sequentially when **any** holds |
|---|---|
| The tasks share no files and no data structures | They edit the same file, even in unrelated places |
| You can write their Interfaces blocks exactly before either starts | The second task depends on how the first turns out |
| Each task is big enough (minutes of work) that waiting matters | The tasks are small: parallel saves seconds and adds a merge |
| | It's a fix round, which builds on code that already exists |

If you aren't sure, choose sequential. A wrong sequential choice costs time. A wrong
parallel choice costs a merge conflict or a fix round. Mixed plans are normal: a backend
endpoint and a frontend page in parallel, and the integration task after both.

**Guard rails for parallel workers.** Unguarded, one of two parallel workers wrote into the
main tree as well as its worktree. With these rails, none of six did.

- **Main tree clean and stamped before dispatch:** run `orch.sh stamp`. It refuses a dirty
  tree, then marks the time. When the workers return, run `orch.sh stray`. It lists every
  file in the main tree written since the stamp, git-ignored ones included, which
  `git status` alone misses. Any hit means a worker left its worktree: compare the change
  with that worker's branch, discard it, and log it.
- **One worktree per parallel worker:** `orch.sh wt-add <task>` creates
  `.orchestrator/worktrees/<task>` on its own branch and prints the path. It sits inside the
  repo, so workers can edit it without extra permission prompts, and it's git-ignored along
  with `.orchestrator/`.
- **Every path in a parallel brief points inside that worker's worktree**: the repo, the
  files, and the report file (`<worktree>/.orchestrator/task-N-report.md`). A single
  main-tree path invites the worker to work there. In testing, the report path was the one
  that did it.
- **Merge one branch at a time**, running the full suite after each merge, so a break points
  to one task. Then run `orch.sh wt-finish <task>`. It copies the worker's report into
  `.orchestrator/reports/<task>/` before removing the worktree, because removal deletes the
  report along with the worktree. It then deletes the merged branch.

**Tell the user the cost before the first dispatch,** in one line. Count the agents by
model, allow one fix round, and price it from these figures. They were measured on small
tasks: each run's bill per model, split across its agents by tokens processed.

| Part of the run | Cost |
|---|---|
| Planner (this session, Opus), whole run | $1.5–1.8 |
| Haiku worker | $0.08–0.35 |
| Opus full verifier | $0.20–0.40 |
| Fix round: Sonnet worker plus Sonnet re-check | ~$0.55 |

For example: "2 Haiku workers, an Opus verifier, and maybe one Sonnet fix round: about
$2–3." Estimate in dollars or relative terms, not tokens. The token counts an agent reports
are its final context size, which is a small fraction of what it actually processed. If the
user is there and the estimate is more than they'd expect for the job, offer direct mode.
Otherwise carry on.

### Build

Fill `references/worker-brief.md` for each task, with the task's tier as the `model`.
Dispatch every task whose dependencies are met **in one message**, each in its own worktree
when more than one runs at once. When a worker lands, dispatch whatever it just unblocked.
The frontier moves as tasks finish; don't wait to send fixed batches.

The brief is why a cheap model can do this job: it removes every decision the worker would
otherwise make. Put everything you know that the worker needs in the brief, in plain words:
the user's preference, why a constraint exists, which pattern in the codebase is current.
Explaining *why* lets the worker make the right call in a case you didn't foresee.

Workers return one of four statuses and a short summary. The full report goes in a file
(`.orchestrator/task-N-report.md`), so your context holds only what you need to decide:

| Status | What it means | What you do |
|---|---|---|
| `DONE` | criteria met, tests pasted green | merge, continue |
| `DONE_WITH_CONCERNS` | done, but the worker flagged something, made a decision the brief didn't settle, or deviated from it | rule on each one: accept it as a ruling, or send it back |
| `BLOCKED` | can't finish in scope | fix the brief or the plan and re-dispatch. Never "try again" unchanged |
| `NEEDS_CONTEXT` | a question the brief should have answered | answer it in the brief, re-dispatch |

A worker that stops with `NEEDS_CONTEXT` or `BLOCKED` may leave half-done, failing edits in
its tree. Run `git status` there before anything else runs in it. Keep the edits only if the
re-dispatched brief builds on them; otherwise `git restore` them.

A `DONE` without pasted **full-suite** output is not `DONE`. A run of only the worker's own
test file doesn't count either. Send it back once for the output.

### Test

If workers ran in parallel, run `orch.sh stray` first. Then merge their branches one at a
time, running the full suite after each merge, and finish each worktree. A conflict means
two tasks weren't independent. Resolve it if it's trivial; otherwise redo the smaller task
sequentially on top of the merged result.

Once everything is in, run the **whole** suite and lint yourself: workers test their task,
you test the system. Run the clean-room command too, if the plan has one. If the suite is red
here, skip the verifier and go to CHECK with the failure.

Then check for edits to tests that existed before the run:
`orch.sh old-tests $BASE <test paths>`. It prints only the lines deleted from test files
that existed at BASE, so tests that were only added don't show. A changed import line is
fine. A removed, changed or loosened assertion or test that the plan doesn't allow goes back
to its worker. Editing an old test is the easiest way for broken code to pass.

### Verify

Write the diff with `orch.sh diff $BASE <N>`, which writes `.orchestrator/diff-<N>.patch`.
Fill the **full** variant of `references/verifier-brief.md` and dispatch it with
`model: "opus"`. It gets the criteria, the review focus, the commands, the rulings and the
diff file. It does **not** get the worker reports or your reasoning. Independence is the whole value,
so don't leak the answer key, and never tell a verifier what not to flag. The rulings are
decisions, not an answer key. The verifier checks that the code follows them, and may still
challenge one. Without them, it re-litigates choices already made and flags them as findings.

The verifier reports PASS or FAIL per criterion with evidence, findings outside the criteria
with a severity, and a "declined to judge" list, so nothing is dropped silently.

### Check

Read the verifier's report as the planner, not the author. For each finding:

- A criterion `FAIL` or a `blocker` → fix round (below).
- `should-fix` → fix round if cheap; otherwise list it for the user with a ruling.
- `nit` → the report. A rationale stated in a report never downgrades a finding's severity.
- A `ruling challenged` → re-decide it. Change the ruling or keep it, and log why.
- A finding that is really a new requirement → the user's call. Don't grow scope silently.

Verifiers don't always agree on severity: the same issue has been rated should-fix twice and
a nit once across three runs of the same code. The verifier's label is input, not the
decision. You rule, and the Ruling line records why.

Nothing left → REPORT. Otherwise log what failed and **why**, as a root cause ("worker
assumed IDs were ints", not "test_x failed"), and start a fix round.

**Fix rounds** are per finding, not a global counter:

- **Rounds 1–2:** a Sonnet worker, even if the task started on Haiku. Give it the finding
  verbatim and add the missing context to the brief. If the same finding comes back, the
  brief was the problem: rewrite it. Don't re-send it with "be more careful".
- **Round 3:** a fresh worker on Opus, with the whole history.
- **After that, stop looping:** rule on it. Park it with a stated cost, or stop and tell the
  user the plan is wrong. Past round 3 the failure is structural, not effort.

After each fix round, run the full suite, then a **scoped** re-verify with
`model: "sonnet"` (the scoped variant of `references/verifier-brief.md`). It gets the
previous findings verbatim, marks each `ADDRESSED` or `NOT ADDRESSED` ("attempted" is not
addressed), and reads only the fix diff for new breakage. The scoped check is where regressions hiding behind green tests get caught. A one-line fix
has moved a boundary that 25 green tests missed, so it isn't optional just because the fix
was small.

### Report

Reply with this report, and save a copy as `.orchestrator/report.md`. Plain sentences are
fine, but keep the Acceptance criteria, Tests and Rulings lines. They are the evidence, and
the user scans for them.

```
## Result: <done | stopped: reason>
- Built: <2–4 lines>
- Acceptance criteria: N/M verified — <failed ones with evidence>
- Tests: <command> → <result>   Lint: <result>   Clean-room: <result or n/a>
- Files changed: <main ones>
- Iterations: N — <one line each: what failed, root cause, what changed>
- Rulings I made: <each Ruling line, or "none">
- Open items: <verifier findings not fixed, worker concerns, parked findings> or "none"
- Not verified: <manual criteria and anything no command could check, with steps for the
  user to check it> or "none"
- Branch: orch/<name>, based on <user's branch> at <BASE>. Not pushed. To take it:
  `git merge orch/<name>`
- Mode: <full hierarchy | single worker + verifier | direct> — agents dispatched, by model
  (e.g. "2 Haiku workers, 1 Opus verifier, 1 Sonnet fix, 1 Sonnet re-check"), and the
  estimate given before the run
```

Then, unless the user wants them kept, finish any leftover worktrees (`git worktree list`),
remove `.orchestrator/`, and run `git worktree prune`.

## Rationalisations to refuse

| You'll think | Actually |
|---|---|
| "It's a small fix, I'll do it myself in-session" | Your context fills with code and the fix skips review. Dispatch it. |
| "The worker says tests pass" | Words aren't evidence. Pasted output is. |
| "The fix was tiny, skip the re-verify" | Tiny fixes move boundaries that green tests don't sit on. |
| "One more fix round will converge" | Past round 3 the problem is the plan, not the worker. Rule or stop. |
| "The verifier will figure out what matters" | It works from the criteria and review focus you wrote. Vague in, vague out. |
| "Each worker knows which worktree is its own" | Unguarded, one in two didn't. Run `stamp` and `stray`: it costs two commands. |
| "Haiku is cheapest, give it everything" | Haiku works when the brief leaves no decisions. Given an open question, it guesses, and each guess becomes a fix round plus a re-verify. |
| "I'll leave out `model`, the default is fine" | The default is your model: Opus. |
| "The user didn't say, so I'll pick" | Pick, and write the Ruling line so they can see and reverse it. |
| "The old test was wrong, so updating it is fine" | Maybe. But that's for the plan to decide, with a ruling. A worker quietly editing an old test is how broken code passes. |
| "I'll just stash their changes, they won't mind" | Stashes get forgotten. Ask first. |
| "The tests mock the API" | Prove it with the clean-room run. "Mocked" tests have made real, billed calls and read live keys from `.env`. |
| "The worker said concerns: none" | Check the Decisions / deviations line and the report too. Workers have changed code they were told not to touch and still replied "concerns: none". |

## Files

Read each reference when you reach its step, not all of them up front. Everything you load
is re-read on every later turn of the run.

- `scripts/orch.sh`: stamp and stray check, worktrees, clean-room run, old-test check,
  verifier diff
- `references/plan-template.md`: the plan file, with an example filled in
- `references/worker-brief.md`: the brief a worker receives. Fill every section
- `references/verifier-brief.md`: the full and scoped verifier briefs
- `references/example-run.md`: the measurements and tests behind the rules in this file.
  Background reading; you don't need it during a run
