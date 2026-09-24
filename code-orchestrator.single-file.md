---
name: code-orchestrator
description: Completion and verification workflow for coding work. It implements, debugs, refactors or migrates code, then proves the delivered change with evidence tied to the exact candidate, delegating or adding an independent review only when that earns its cost. Use it whenever the user wants a feature, bug fix, refactor, migration or cross-cutting change done carefully — they ask for a plan or acceptance criteria before code, for the work to be delegated to agents, workers or subagents, or for it to be verified, reviewed or double-checked before it's called done — or invokes it by name. Load it before exploring the repo. Not for explanations of code, reviewing an existing PR on its own, or anything that isn't code.
---

# Code Orchestrator

Deliver the requested behaviour with evidence, at the lowest practical total cost: planning,
building, review and repairs together. You are the main session. You understand the
request, choose the route, plan in proportion, build or delegate, integrate and finish.
Build it yourself unless delegating has a concrete benefit.

Everything you load is re-read on every later turn, so read references only at the step
that needs them, and keep your context small.

The mechanical guarantees live in the helper script in Appendix D. Once per run, save it
as `/tmp/orch.sh` and run it as `bash /tmp/orch.sh <command>` from inside the repo; `help`
lists everything.
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
- **anything outside the repo:** other directories, global installs, system settings
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
   - Write short acceptance criteria someone else could check, and note known failures.
   - Keep small tasks in the conversation. Delegated, reviewed or interruptible work gets a
     durable record: Appendix A into `.orchestrator/record.md`.
   - Preserve established contracts and conventions unless the request deliberately changes
     them.
   - Where the request introduces new input handling, prefer a clear error to silently
     dropping, coercing or guessing at data. Planners have ruled comma-only CSV rows "blank",
     and the rows vanished. That rule is not permission to make existing APIs stricter.
   - Record material decisions (`Decision: <what> — <why> — <cost if wrong>`), not every
     conceivable input.

3. **Route**, as above. For Reviewed, run `orch.sh require review`. For code that calls
   external services, run `orch.sh require offline`.

4. **Delegate only with a reason.** Brief with Appendix B, dispatch to an
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
   `path  reason` in `.orchestrator/approved-test-changes`.

6. **Check the exact candidate.** `orch.sh check -- <test command>`. It refuses leftovers,
   freezes HEAD as the candidate, runs the suite against it, voids the result if the run
   changed the tree, and audits test changes. Treat each flag as a signal to read, not a
   verdict.
   - Anything you change afterwards needs a new `check`.
   - Record other evidence against the candidate with `orch.sh run <label> -- <command>`: lint,
     types, a reproduction.
   - `orch.sh fresh [--offline] -- <tests>` runs a fresh checkout, which catches reliance on
     untracked files, local secrets or the network.
   - `--offline` is enforced and verified, or refused. `fresh` does not sandbox the
     filesystem. Where you promise isolation the helper can't give, use the host's sandbox,
     or say plainly that it wasn't isolated.

7. **Independent review (Reviewed mode).**
   - Run `orch.sh diff`, then brief the `orch-verifier` agent from
     Appendix C.
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
hasn't yet shown a measurable gain. If the agents aren't installed, pass `model` instead and say the effort was
the default.

## Rationalisations to refuse

| You'll think | Actually |
|---|---|
| "More agents make it more reliable" | Delegated code has introduced the very bugs the reviewer then paid to catch. Delegate for a reason. |
| "The tests passed a minute ago" | Evidence belongs to one candidate. Anything changed since needs a new `check`. |
| "It's only a skip marker" | A skipped or loosened test is how broken code passes. Approve it with a reason, or revert it. |
| "The reviewer found nothing, so it didn't look" | A clean review is valid. Judge findings by their evidence. |
| "One more repair will do it" | The budget covers the whole run. Diagnose, or finish Partial. |
| "The clean room proves it's offline" | Only a verified `--offline` run proves no network access, and nothing here sandboxes the filesystem. |

## Appendices

- Appendix A: the run record template
- Appendix B: the worker brief (only when delegating)
- Appendix C: the reviewer briefs (only for an independent review)
- Appendix D: orch.sh, the helper script

Read the appendix you need when you reach that step; you don't need all of them up front.

---

## Appendix A — Run record template

Write this to `.orchestrator/record.md` for delegated, reviewed or interruptible work. Small
direct tasks can keep it in the conversation. Keep it current: it's what a resumed session
and the reviewer work from. The helper keeps the machine part (`.orchestrator/manifest`,
`evidence.tsv`, `logs/`); this file holds the judgement.

```markdown
# <short name>

## Request
See .orchestrator/request.md (verbatim). One line in your own words: <what the user wants>

## Done means
- C1: <checkable statement: a command, an observation, or a named test>
- C2: ...
- C3 (manual): <only what no command can check; stays "not verified" until someone checks it>

## Baseline
- BASE <sha>, branch orch/<name>; test command: <command>
- Known failures at BASE: <from .orchestrator/baseline/failures.txt, or "none">

## Contracts to preserve
- <existing behaviour, APIs, conventions the change must not break, with where they're defined>

## Route
- Builders: <me | N workers, and why> · Review: <checks only | independent, and why>
- Requirements set: <orch.sh require ... or "none">

## Decisions
- Decision: <what> — <why> — <cost if wrong>

## Work
- <task>: <owner> — <status> — <commit>

## Findings and repairs
- <finding: blocking | optional | observation> — <evidence> — <fixed in commit | left, why>
- Repair cycles used: <n of 2>

## Status
<Done | Partial | Blocked> — <what remains, if anything>
```

---

## Appendix B — Worker brief

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

### Notes for the main session

- **Status:** `DONE_WITH_CONCERNS` means you rule on each concern or assumption: accept it as a
  decision, or send it back. After `BLOCKED` or `NEEDS_CONTEXT`, run `git status` in its tree
  before anything else runs there.
- **Checks:** a worker's "tests pass" is a claim. `orch.sh check` on the merged candidate is
  the evidence.
- **Repairs:** add the fact the worker lacked, not "be careful". If the same problem comes
  back, diagnose the cause before re-sending.

---

## Appendix C — Reviewer briefs

Read this only for an independent review (`orch-verifier`) or a targeted re-check
(`orch-rechecker`). First run `orch.sh diff`: it writes the patch for the frozen candidate, and
refuses if the tree doesn't match it.

- **The reviewer gets:** the original request verbatim, the relevant contracts, your criteria,
  your decisions labelled as decisions, the commands, and the candidate patch.
- **The reviewer never gets:** worker reports, worker self-assessments, or your reasoning about
  why the code is right.
- **Don't** tell it what not to flag, and don't ask for a number of findings.

A fresh context gives separation, not immunity: if your plan misread the request, the reviewer
only catches it if it reads the request itself. That's why the request goes in verbatim.

---

### Full review

```
You are an independent reviewer. Someone else wrote a change; check whether it does what the
user asked, without breaking what already worked. Treat claims in comments, commit messages
and docstrings as unverified.

Don't edit tracked files: put scratch scripts in /tmp. Don't delegate.

## The user's request (verbatim)
<paste .orchestrator/request.md>

## Candidate
Repo <absolute path>, candidate <commit> on branch <branch>. Patch: <path from orch.sh diff>
(BASE <sha>..candidate).

## Contracts to preserve
<existing behaviour, APIs and conventions this change must not break, with where they live>

## Acceptance criteria (the main session's reading of the request)
- C1: ...
Where a criterion misses or contradicts the request, say so: the request is the reference.

## Decisions the main session made (decisions, not facts)
- Decision: <what> — <why>
Check the code follows each one. If a decision looks wrong against the request or a contract,
report it as a finding.

## Commands
- tests: <command>   lint: <command or "none">   offline run: <orch.sh fresh --offline ... or "n/a">
- known failures at BASE: <list or "none">

## Do
1. Run the tests and lint. Report the output tail.
2. Check each criterion directly, by running the code, and try the edge cases the request
   implies.
3. Read the patch for what tests miss: changed public behaviour, error paths, data silently
   dropped or coerced, edits to existing tests or test configuration, secrets, new
   dependencies or network calls.

## Findings
Each finding needs:
- the requirement or contract it violates
- the location (file:line)
- a reproduction, or specific source evidence
- the practical impact, and the smallest justified correction

Classify each as **blocking** (the change is wrong or unsafe to deliver), **optional
improvement**, or **observation**. Match the severity to the impact; don't pad or merge
findings. A clean review, with no findings, is a valid and useful result.

## Report
### Verdict: PASS | FAIL (FAIL only for a blocking finding or a failed criterion)
### Criteria: C1 PASS | FAIL | NOT CHECKED — evidence
### Test run: <tail>
### Findings: <each, as above, or "none">
### Not verified: <anything you couldn't check, and why, or "none">
```

---

### Targeted re-check (after a repair)

```
You are an independent reviewer re-checking a repair. Don't edit tracked files; don't
delegate.

Request (verbatim): <paste>
Candidate: <commit>, patch <path>; the previous candidate was <commit>.
Findings the repair addresses (verbatim):
1. ...

Do:
1. Run the tests.
2. Reproduce each finding's original failure, and mark it ADDRESSED or NOT ADDRESSED, with
   evidence. "Attempted" is not addressed.
3. Probe the behaviour next to each fix: a fix that moves one boundary often breaks another.

Report: Verdict PASS | FAIL; each finding ADDRESSED | NOT ADDRESSED with evidence; any new
blocking finding in the format above; what you couldn't verify.
```

---

## Appendix D — orch.sh

Save this as `/tmp/orch.sh` and run it with `bash`.

````bash
#!/usr/bin/env bash
# orch.sh: mechanical checks for the code-orchestrator skill.
# It freezes the exact candidate being delivered, ties every piece of evidence to that
# candidate, and refuses a "done" result on missing, stale or mismatched evidence.
# Portable: bash 3.2+ (the macOS default), GNU or BSD tools, git 2.20+.
# Run it from anywhere inside the repo; it works on the repo's top level.
set -u

usage() {
  cat <<'EOF'
usage: orch.sh <command> [args]

Run lifecycle
  start <name> [--offline] [-- <test command>]
      Begin a run. Refuses a tree with uncommitted work (exit 4). Stops at an unfinished
      earlier run (exit 3) and archives a finished one. Creates branch orch/<name>,
      git-ignores .orchestrator/, records BASE and, given a test command, the baseline:
      exit code, counts and failing tests, so later failures can be told apart.
  status              Manifest, candidate, recent evidence and repair cycles (for resuming).
  require <review|fresh|offline> ...
                      Add completion requirements that `gate` enforces.
  ignore <pattern>    Git-ignore a generated path locally (.git/info/exclude), and log it.
  finish <done|partial|blocked> [note]
                      Close the run. `done` runs the gate first and refuses if it fails.
                      Keeps the record; removes finished worker worktrees.

Candidate and evidence
  check [--label L] [--offline] -- <test command>
                      One call after building: freeze the candidate (refuses uncommitted or
                      untracked leftovers), run the tests against it, re-check the tree
                      afterwards, and audit test changes. Exit 0 only with no new failures,
                      no leftovers and no unapproved test changes.
  candidate           Freeze the candidate only (clean tree required).
  run <label> [--offline] -- <command>
                      Run any command against the frozen candidate as evidence (lint, a
                      focused reproduction, a type check).
  fresh [--offline] [--keep-home] [--keep VAR] [--deps copy|none] [VAR=value ...] -- <command>
                      Run in a fresh checkout of the candidate: no ignored or untracked files,
                      an allowlisted environment and a temporary HOME. NOT a filesystem
                      sandbox: absolute paths outside the checkout stay readable.
  tests               Audit changes to tests that existed at BASE: deleted lines, added
                      skip/only/xfail markers, runner configuration, fixtures and snapshots,
                      and skipped or executed counts against the baseline. Approve deliberate
                      changes in .orchestrator/approved-test-changes ("path  reason" lines).
  diff                Write the review patch BASE..candidate; refuses if the tree doesn't
                      match the candidate.
  record <kind> <pass|fail|pending> [note]
                      Log evidence that isn't a command, against the candidate: review,
                      recheck, manual.
  repair <reason>     Open a repair cycle. Exit 1 once the budget is spent (default 2, or
                      ORCH_MAX_REPAIR_CYCLES). Advisory: it records and warns; it can't stop
                      a model that ignores it.
  gate                Check the completion requirements for the current candidate.

--offline enforces no network access (Linux: unshare -n; macOS: sandbox-exec), verified
with a loopback probe before the command runs. It exits 5 if this host can't enforce it.

Parallel workers
  stamp / stray       Before and after parallel dispatch: detect writes to the main tree,
                      git-ignored files included.
  wt-add <task> [--deps copy|none|link]
                      Worktree .orchestrator/worktrees/<task> on branch orch-wt/<task>.
                      Dependency folders are copied (copy-on-write where supported), not
                      shared. `link` shares them writably: use it only for a stated reason.
  wt-finish <task>    Copy the worker's report out, remove the worktree, delete the merged branch.
  caps                What this host can enforce, and what it can't.
EOF
}

die() { echo "orch.sh: $*" >&2; exit 2; }

ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || die "not inside a git repo"
cd "$ROOT" || die "cannot cd to $ROOT"
O=.orchestrator
EV="$O/evidence.tsv"
DEP_DIRS="node_modules .venv venv"

now() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }

# ---------------------------------------------------------------- manifest

mf_get() { [ -f "$O/manifest" ] && sed -n "s/^$1=//p" "$O/manifest" | tail -1; }
mf_set() {
  mkdir -p "$O"; touch "$O/manifest"
  grep -v "^$1=" "$O/manifest" > "$O/manifest.tmp"
  printf '%s=%s\n' "$1" "$(printf '%s' "$2" | tr '\t\n' '  ')" >> "$O/manifest.tmp"
  mv "$O/manifest.tmp" "$O/manifest"
}
need_run() { [ -f "$O/manifest" ] || die "no run here: start one with 'orch.sh start <name>'"; }
base_rev() { mf_get base; }

ensure_ignored() {
  if ! git check-ignore -q "$O/x"; then
    local ex; ex=$(git rev-parse --git-path info/exclude)
    mkdir -p "$(dirname "$ex")"
    echo "$O/" >> "$ex"
  fi
}

# ---------------------------------------------------------------- candidate

leftovers() { git status --porcelain --untracked-files=normal -- . ":(exclude)$O"; }

freeze_candidate() {
  local left
  left=$(leftovers)
  if [ -n "$left" ]; then
    echo "LEFTOVERS: the tree has changes that aren't committed, so there's no exact candidate:"
    printf '%s\n' "$left" | sed 's/^/  /'
    echo "Commit the intended files by name; delete the rest, or 'orch.sh ignore <pattern>' generated ones."
    return 1
  fi
  mkdir -p "$O"
  printf 'commit=%s\ntree=%s\ntime=%s\n' "$(git rev-parse HEAD)" "$(git rev-parse 'HEAD^{tree}')" "$(now)" > "$O/candidate"
  mf_set candidate "$(git rev-parse HEAD)"
  return 0
}
cand() { [ -f "$O/candidate" ] && sed -n "s/^$1=//p" "$O/candidate"; }

# Is the working tree exactly the frozen candidate? Prints the reason when it isn't.
candidate_current() {
  [ -f "$O/candidate" ] || { echo "no candidate frozen yet"; return 1; }
  [ "$(git rev-parse HEAD)" = "$(cand commit)" ] || { echo "HEAD moved since the candidate was frozen"; return 1; }
  [ -z "$(leftovers)" ] || { echo "the tree has uncommitted or untracked changes"; return 1; }
  return 0
}
require_current() {
  local why
  why=$(candidate_current) || die "candidate out of date ($why): run 'orch.sh check' again"
}

# ---------------------------------------------------------------- environment and logs

env_fp() {
  {
    uname -sm; git --version
    command -v node >/dev/null 2>&1 && node --version
    command -v python3 >/dev/null 2>&1 && python3 --version 2>&1
    local f
    for f in node_modules/.package-lock.json node_modules/.yarn-integrity node_modules/.modules.yaml .venv/pyvenv.cfg venv/pyvenv.cfg; do
      [ -f "$f" ] && { echo "$f"; git hash-object "$f"; }
    done
  } 2>/dev/null | git hash-object --stdin | cut -c1-12
}

# One line, tabs removed, credential-looking assignments masked.
show_cmd() {
  printf '%s ' "$@" | tr '\t\n' '  ' | sed -E \
    's/([A-Za-z0-9_]*(KEY|TOKEN|SECRET|PASSWORD|PASSWD|AUTH|CREDENTIAL|key|token|secret|password|passwd|auth|credential)[A-Za-z0-9_]*)=[^ ]*/\1=***/g'
}

next_seq() {
  local n=0
  [ -f "$EV" ] && n=$(($(wc -l < "$EV") - 1))
  printf '%03d' $((n + 1))
}

ev_append() {
  # seq time kind label commit tree exit status secs envfp counts log command
  if [ ! -f "$EV" ]; then
    mkdir -p "$O"
    printf 'seq\ttime\tkind\tlabel\tcommit\ttree\texit\tstatus\tsecs\tenvfp\tcounts\tlog\tcommand\n' > "$EV"
  fi
  local IFS=$'\t'
  printf '%s\n' "$*" >> "$EV"
}

# Test-runner summaries: prints "passed failed skipped ran runner", with ? where unknown.
# Heuristic: pytest, unittest, TAP (node --test, tape), jest, vitest, go test -v, cargo.
parse_counts() {
  awk '
    function grab(s, re,   m) { if (match(s, re)) { m = substr(s, RSTART, RLENGTH); gsub(/[^0-9]/, "", m); return m + 0 } return -1 }
    function add(a, b) { return (b < 0) ? a : ((a < 0) ? b : a + b) }
    BEGIN { pp=pf=pe=ps=-1; ur=us=uf=ue=-1; tp=tf=ts=-1; tskip=0; jp=jf=js=-1; vp=vf=vs=-1; cp=cf=ci=-1; gp=gf=gs=0 }
    /[0-9]+ (passed|failed|skipped|errors?|xfailed|deselected)/ && / in [0-9.]+s/ {
      py=1; pp=grab($0,"[0-9]+ passed"); pf=grab($0,"[0-9]+ failed"); pe=grab($0,"[0-9]+ errors?")
      ps=add(grab($0,"[0-9]+ skipped"), grab($0,"[0-9]+ xfailed"))
    }
    /^Ran [0-9]+ tests? in/ { ut=1; ur=grab($0,"Ran [0-9]+") }
    /^(OK|FAILED)( \(|$)/ { us=grab($0,"skipped=[0-9]+"); uf=grab($0,"failures=[0-9]+"); ue=grab($0,"errors=[0-9]+") }
    /^# pass +[0-9]+/ { tap=1; tp=grab($0,"[0-9]+") }
    /^# fail +[0-9]+/ { tf=grab($0,"[0-9]+") }
    /^# (skipped|skip) +[0-9]+/ { ts=grab($0,"[0-9]+") }
    /^ *ok [0-9]+ .*# (SKIP|skip)/ { tskip++ }
    /^Tests: / { jest=1; jp=grab($0,"[0-9]+ passed"); jf=grab($0,"[0-9]+ failed"); js=grab($0,"[0-9]+ skipped") }
    /^ *Tests +[0-9]+ / { vit=1; vp=grab($0,"[0-9]+ passed"); vf=grab($0,"[0-9]+ failed"); vs=grab($0,"[0-9]+ skipped") }
    /^ *--- PASS:/ { go=1; gp++ } /^ *--- FAIL:/ { go=1; gf++ } /^ *--- SKIP:/ { go=1; gs++ }
    /^test result: / { cargo=1; cp=add(cp,grab($0,"[0-9]+ passed")); cf=add(cf,grab($0,"[0-9]+ failed")); ci=add(ci,grab($0,"[0-9]+ ignored")) }
    function out(p, f, s, r, name) {
      printf "%s %s %s %s %s\n", (p<0?"?":p), (f<0?"?":f), (s<0?"?":s), (r<0?"?":r), name; done=1
    }
    END {
      if (py)          { f=add(pf,pe); out((pp<0?0:pp), (f<0?0:f), (ps<0?0:ps), add((pp<0?0:pp),(f<0?0:f)), "pytest") }
      else if (ut)     { f=add(uf,ue); f=(f<0?0:f); s=(us<0?0:us); out(ur-f-s, f, s, ur, "unittest") }
      else if (tap)    { s=(ts<0?tskip:ts); out(tp, (tf<0?0:tf), s, add(tp,(tf<0?0:tf)), "tap") }
      else if (jest)   { out((jp<0?0:jp), (jf<0?0:jf), (js<0?0:js), add((jp<0?0:jp),(jf<0?0:jf)), "jest") }
      else if (vit)    { out((vp<0?0:vp), (vf<0?0:vf), (vs<0?0:vs), add((vp<0?0:vp),(vf<0?0:vf)), "vitest") }
      else if (cargo)  { out(cp, cf, ci, add(cp,cf), "cargo") }
      else if (go)     { out(gp, gf, gs, gp+gf, "go") }
      if (!done) print "? ? ? ? unknown"
    }' "$1"
}

# Failing-test identifiers, one per line (heuristic, same runners as parse_counts).
failures_of() {
  awk '
    /^FAILED / { s=$0; sub(/^FAILED /,"",s); sub(/ - .*$/,"",s); print "pytest:" s; next }
    /^ERROR / && /::/ { s=$0; sub(/^ERROR /,"",s); sub(/ - .*$/,"",s); print "pytest:" s; next }
    /^(FAIL|ERROR): / { s=$0; sub(/^(FAIL|ERROR): /,"",s); print "unittest:" s; next }
    /^ *not ok [0-9]+/ && !/# (TODO|todo|SKIP|skip)/ { s=$0; sub(/^ *not ok [0-9]+ *(- )?/,"",s); print "tap:" s; next }
    /^ *--- FAIL: / { s=$0; sub(/^ *--- FAIL: /,"",s); sub(/ \(.*$/,"",s); print "go:" s; next }
    /^test .* \.\.\. FAILED$/ { s=$0; sub(/^test /,"",s); sub(/ \.\.\. FAILED$/,"",s); print "cargo:" s; next }
  ' "$1" | sort -u
}

# ---------------------------------------------------------------- offline enforcement

offline_method() {
  case "$(uname -s)" in
    Linux)
      if unshare -cn true 2>/dev/null; then echo "unshare -cn"
      elif unshare -rn true 2>/dev/null; then echo "unshare -rn"; fi ;;
    Darwin)
      if command -v sandbox-exec >/dev/null 2>&1 &&
         sandbox-exec -p '(version 1)(allow default)(deny network*)' /usr/bin/true 2>/dev/null; then
        echo "sandbox-exec"
      fi ;;
  esac
}

wrap_offline() {  # method, then the command
  local m=$1; shift
  case "$m" in
    "unshare -cn") unshare -cn "$@" ;;
    "unshare -rn") unshare -rn "$@" ;;
    sandbox-exec) sandbox-exec -p '(version 1)(allow default)(deny network*)' "$@" ;;
    *) return 99 ;;
  esac
}

# Proves the wrapper blocks a loopback connection that works without it. Prints
# "verified", "unverified: <why>" or "FAILED: <why>".
probe_offline() {
  local m=$1 dir port i pid
  dir=$(mktemp -d "${TMPDIR:-/tmp}/orch-probe.XXXXXX") || { echo "unverified: mktemp failed"; return; }
  if command -v python3 >/dev/null 2>&1; then
    python3 -c 'import socket,sys,time
s=socket.socket(); s.bind(("127.0.0.1",0)); s.listen(5); s.settimeout(8)
open(sys.argv[1],"w").write(str(s.getsockname()[1]))
end=time.time()+8
while time.time()<end:
    try: c,_=s.accept(); c.close()
    except Exception: break' "$dir/port" 2>/dev/null &
    pid=$!
  elif command -v node >/dev/null 2>&1; then
    node -e 'const s=require("net").createServer(c=>c.end()).listen(0,"127.0.0.1",()=>{require("fs").writeFileSync(process.argv[1],String(s.address().port))});setTimeout(()=>process.exit(0),8000)' "$dir/port" 2>/dev/null &
    pid=$!
  else
    rm -rf "$dir"; echo "unverified: no python3 or node to run the probe listener"; return
  fi
  i=0; while [ ! -s "$dir/port" ] && [ $i -lt 50 ]; do sleep 0.1; i=$((i + 1)); done
  port=$(cat "$dir/port" 2>/dev/null)
  if [ -z "$port" ]; then kill "$pid" 2>/dev/null; rm -rf "$dir"; echo "unverified: probe listener didn't start"; return; fi
  if ! bash -c "exec 3<>/dev/tcp/127.0.0.1/$port" 2>/dev/null; then
    kill "$pid" 2>/dev/null; rm -rf "$dir"; echo "unverified: this bash can't open /dev/tcp connections"; return
  fi
  if wrap_offline "$m" bash -c "exec 3<>/dev/tcp/127.0.0.1/$port" 2>/dev/null; then
    kill "$pid" 2>/dev/null; rm -rf "$dir"; echo "FAILED: a loopback connection succeeded inside '$m'"; return
  fi
  kill "$pid" 2>/dev/null; rm -rf "$dir"; echo "verified"
}

# Sets OFFLINE_M, or exits 5 when network isolation can't be enforced and proven.
offline_or_die() {
  OFFLINE_M=$(offline_method)
  [ -n "$OFFLINE_M" ] || { echo "orch.sh: --offline can't be enforced on this host (no usable 'unshare -n' or 'sandbox-exec'). Run in a sandbox that blocks network (a container with --network none, or the host's sandboxed shell), or drop --offline and report the run as NOT network-isolated." >&2; exit 5; }
  local v; v=$(probe_offline "$OFFLINE_M")
  case "$v" in
    verified) OFFLINE_NOTE="network isolated ($OFFLINE_M, verified by loopback probe)" ;;
    FAILED*) echo "orch.sh: offline enforcement $v" >&2; exit 5 ;;
    *) OFFLINE_NOTE="network isolation applied ($OFFLINE_M) but $v" ;;
  esac
}

# ---------------------------------------------------------------- command evidence

# run_capture <kind> <label> <compare-baseline 0|1> <offline method or -> <workdir> -- cmd...
# Sets RC and STATUS; appends an evidence row.
run_capture() {
  local kind=$1 label=$2 cmpbase=$3 om=$4 wd=$5; shift 5; [ "${1:-}" = "--" ] && shift
  local seq log t0 t1 counts new cur
  seq=$(next_seq); mkdir -p "$O/logs"; log="$O/logs/$seq-$label.log"
  t0=$(date +%s)
  if [ "$om" = "-" ]; then ( cd "$wd" && "$@" ) > "$log" 2>&1
  else ( cd "$wd" && wrap_offline "$om" "$@" ) > "$log" 2>&1; fi
  RC=$?
  t1=$(date +%s)
  counts=$(parse_counts "$log")
  STATUS=pass; NEWFAIL=""
  if [ $RC -ne 0 ]; then
    STATUS=fail
    if [ "$cmpbase" = 1 ] && [ -f "$O/baseline/failures.txt" ]; then
      cur=$(failures_of "$log")
      new=$(printf '%s\n' "$cur" | grep -v '^$' | sort -u | comm -23 - "$O/baseline/failures.txt")
      if [ -n "$cur" ] && [ -z "$new" ]; then STATUS=known-failures; else NEWFAIL=${new:-"(unidentified: exit $RC)"}; fi
    fi
  fi
  if [ -n "$(leftovers)" ]; then STATUS=dirty-after; fi
  ev_append "$seq" "$(now)" "$kind" "$label" "$(git rev-parse HEAD)" "$(git rev-parse 'HEAD^{tree}')" \
    "$RC" "$STATUS" "$((t1 - t0))" "$(env_fp)" "$(echo "$counts" | tr ' ' '/')" "$log" "$(show_cmd "$@")"
  echo "== $kind '$label': exit $RC, $STATUS, $((t1 - t0))s, counts passed/failed/skipped/ran/runner = $(echo "$counts" | tr ' ' '/')"
  tail -12 "$log" | sed 's/^/  | /'
  echo "  log: $log"
  if [ -n "$NEWFAIL" ]; then echo "  new failures (not in the baseline):"; printf '%s\n' "$NEWFAIL" | head -20 | sed 's/^/    /'; fi
  if [ "$STATUS" = known-failures ]; then echo "  every failure was already failing at BASE (see .orchestrator/baseline/failures.txt): disclose them"; fi
  if [ "$STATUS" = dirty-after ]; then echo "  DIRTY AFTER: the command changed the tree, so this evidence is void:"; leftovers | sed 's/^/    /'; fi
}

# ---------------------------------------------------------------- test-change audit

is_test_path() {
  case "$1" in
    */test/*|test/*|*/tests/*|tests/*|*/__tests__/*|__tests__/*|*/spec/*|spec/*|*/specs/*|specs/*) return 0 ;;
  esac
  case "${1##*/}" in
    test_*.py|*_test.py|conftest.py|*_test.go|*.test.*|*.spec.*|*_spec.rb|*Test.java|*Tests.java|*Test.kt|*Tests.cs) return 0 ;;
  esac
  return 1
}
is_runner_config() {
  case "${1##*/}" in
    pytest.ini|tox.ini|setup.cfg|pyproject.toml|conftest.py|noxfile.py|package.json|Makefile|.mocharc*|mocha.opts|.nycrc*|ava.config.*|jest.config.*|vitest.config.*|vite.config.*|karma.conf.*|playwright.config.*|cypress.config.*|phpunit.xml*|Cargo.toml|.github) return 0 ;;
  esac
  case "$1" in .github/workflows/*) return 0 ;; esac
  return 1
}
is_fixture() {
  case "$1" in
    */__snapshots__/*|*.snap|*/fixtures/*|fixtures/*|*/fixture/*|*/testdata/*|testdata/*|*/test-data/*) return 0 ;;
  esac
  return 1
}
approved() {  # path -> prints the reason and returns 0 when approved
  [ -f "$O/approved-test-changes" ] || return 1
  awk -v p="$1" '$1 == p { $1=""; sub(/^ +/,""); print ($0 == "" ? "approved" : $0); found=1; exit } END { exit !found }' "$O/approved-test-changes"
}
SKIP_RE='@(unittest\.)?skip|pytest\.mark\.(skip|xfail)|pytest\.(skip|xfail)\(|skipIf|skipUnless|expectedFailure|__test__ *= *False|\.skip\(|\.only\(|\.todo\(|(^|[^A-Za-z0-9_.])(xit|xdescribe|xtest|fit|fdescribe|pending)\(|skip *: *(true|[^,}]*[A-Za-z"'"'"'])|t\.Skip|@Disabled|@Ignore|#\[ignore\]'

# Prints findings; sets UNAPPROVED to the number of flags that aren't approved.
audit_tests() {
  local base=$1 to=$2 st path added deleted why r n=0 u=0
  UNAPPROVED=0
  echo "== test-change audit, $base..${to:0:12}"
  while IFS=$'\t' read -r st path; do
    [ -z "$path" ] && continue
    why=""
    if git cat-file -e "$base:$path" 2>/dev/null; then
      if is_test_path "$path"; then
        if [ "$st" = D ]; then why="existing test file deleted"
        else
          deleted=$(git diff --no-renames "$base" "$to" -- "$path" | grep '^-' | grep -v '^---')
          added=$(git diff --no-renames "$base" "$to" -- "$path" | grep '^+' | grep -v '^+++' | grep -E "$SKIP_RE")
          [ -n "$deleted" ] && why="$(printf '%s' "$deleted" | grep -c .) line(s) deleted or changed"
          [ -n "$added" ] && why="${why:+$why; }skip/only/xfail marker added"
        fi
      fi
      if [ -z "$why" ] && is_runner_config "$path"; then why="test runner or discovery configuration changed"; fi
      if [ -z "$why" ] && is_fixture "$path"; then why="existing fixture or snapshot changed"; fi
    elif is_test_path "$path" && git show "$to:$path" 2>/dev/null | grep -qE "$SKIP_RE"; then
      why="new test file contains skip/only/xfail markers"
    fi
    [ -z "$why" ] && continue
    n=$((n + 1))
    if r=$(approved "$path"); then echo "  approved  $path: $why ($r)"
    else u=$((u + 1)); echo "  FLAG      $path: $why"
      git diff --no-renames "$base" "$to" -- "$path" | grep -E '^[-+]' | grep -vE '^(\+\+\+|---)' | head -8 | sed 's/^/              /'
    fi
  done < <(git diff --no-renames --name-status "$base" "$to")
  # Counts against the baseline, from the latest check on this candidate.
  local bc cc
  bc=$(cat "$O/baseline/counts" 2>/dev/null)
  cc=$(awk -F'\t' -v c="$(cand commit)" '$3=="check" && $5==c { x=$11 } END { print x }' "$EV" 2>/dev/null | tr '/' ' ')
  if [ -n "$bc" ] && [ -n "$cc" ]; then
    set -- $bc; local bs=$3 br=$4 brn=$5
    set -- $cc; local cs=$3 cr=$4 crn=$5
    if [ "$brn" = unknown ] || [ "$crn" = unknown ] || [ "$bs" = "?" ] || [ "$cs" = "?" ]; then
      echo "  counts: the runner's summary couldn't be read, so skipped/executed changes weren't measured"
    else
      if [ "$cs" -gt "$bs" ]; then n=$((n + 1)); u=$((u + 1)); echo "  FLAG      skipped tests rose from $bs at BASE to $cs"; fi
      if [ "$cr" -lt "$br" ]; then n=$((n + 1)); u=$((u + 1)); echo "  FLAG      executed tests fell from $br at BASE to $cr"; fi
    fi
  elif [ -z "$bc" ]; then echo "  counts: no baseline recorded (start with '-- <test command>'), so skipped/executed changes weren't measured"
  fi
  [ $n -eq 0 ] && echo "  OK: no changes to existing tests, runner configuration or fixtures"
  [ $u -gt 0 ] && echo "  $u unapproved flag(s). A flag is a signal to review, not proof: approve deliberate changes in $O/approved-test-changes, revert the rest."
  UNAPPROVED=$u
}

# ---------------------------------------------------------------- dependencies

cow_copy() {
  case "$(uname -s)" in
    Darwin) cp -Rc "$1" "$2" 2>/dev/null || { rm -rf "$2"; cp -R "$1" "$2"; } ;;
    *) cp -R --reflink=auto "$1" "$2" 2>/dev/null || { rm -rf "$2"; cp -R "$1" "$2"; } ;;
  esac
}
place_deps() {  # dest mode
  local dest=$1 mode=$2 d ex
  ex=$(git rev-parse --git-path info/exclude); case "$ex" in /*) ;; *) ex="$ROOT/$ex" ;; esac
  mkdir -p "$(dirname "$ex")"
  for d in $DEP_DIRS; do
    [ -e "$ROOT/$d" ] && [ ! -e "$dest/$d" ] || continue
    case "$mode" in
      none) continue ;;
      link) ln -s "$ROOT/$d" "$dest/$d"; echo "  WARNING: $d is a writable link to the main tree's; writes there change it for everyone" ;;
      *) cow_copy "$ROOT/$d" "$dest/$d"; echo "  copied $d (writes there don't reach the main tree)"
         if [ "$d" != node_modules ] && grep -rlsF "$ROOT" "$dest/$d"/lib/python*/site-packages/*.pth "$dest/$d"/lib/python*/site-packages/__editable__* >/dev/null 2>&1; then
           echo "  WARNING: $d has an editable install pointing at the main checkout: imports load the main tree's source. Run with PYTHONPATH set to the worktree's source, or reinstall there."
         fi ;;
    esac
    grep -qx "/$d" "$ex" 2>/dev/null || echo "/$d" >> "$ex"
  done
}

# ---------------------------------------------------------------- commands

cmd_start() {
  local name="" offline=0 left st from base rid
  while [ $# -gt 0 ] && [ "$1" != "--" ]; do
    case "$1" in --offline) offline=1 ;; -*) die "unknown option $1" ;; *) [ -z "$name" ] && name=$1 || die "one name only" ;; esac
    shift
  done
  [ -n "$name" ] || die "usage: orch.sh start <name> [--offline] [-- <test command>]"
  if [ -f "$O/manifest" ]; then
    st=$(mf_get status)
    case "$st" in
      done|partial|blocked)
        rid=$(mf_get run_id); rid=${rid:-earlier}
        [ -d "$O/worktrees" ] && [ -n "$(ls -A "$O/worktrees" 2>/dev/null)" ] && die "the finished run still has worktrees in $O/worktrees; finish or remove them first"
        mkdir -p "$O/runs/$rid"
        for e in "$O"/* "$O"/.[!.]*; do [ -e "$e" ] || continue; case "${e##*/}" in runs|worktrees) ;; *) mv "$e" "$O/runs/$rid/" ;; esac; done
        echo "archived the finished run ($st) to $O/runs/$rid/" ;;
      *)
        echo "EARLIER RUN FOUND (status: ${st:-unknown}, branch: $(git rev-parse --abbrev-ref HEAD)). Read it with 'orch.sh status'."
        echo "Same request and its branch unmoved: resume from where its evidence stops. Otherwise ask the user which run to keep."
        cmd_status_inner; exit 3 ;;
    esac
  elif [ -f "$O/plan.md" ]; then
    echo "EARLIER RUN FOUND: $O/plan.md exists from an older version of this skill. Read it; resume or ask."; exit 3
  fi
  left=$(leftovers)
  if [ -n "$left" ]; then
    echo "UNCOMMITTED CHANGES: ask the user whether to commit them, stash them, or build on top."
    printf '%s\n' "$left"; exit 4
  fi
  ensure_ignored
  from=$(git rev-parse --abbrev-ref HEAD)
  git show-ref --verify --quiet "refs/heads/orch/$name" && die "branch orch/$name already exists: resume it or choose another name"
  git checkout -q -b "orch/$name" || die "could not create branch orch/$name"
  base=$(git rev-parse HEAD)
  mkdir -p "$O"
  : > "$O/manifest"
  mf_set run_id "$(date -u +%Y%m%dT%H%M%SZ)-$name"; mf_set name "$name"; mf_set branch "orch/$name"
  mf_set from "$from"; mf_set base "$base"; mf_set status active; mf_set created "$(now)"
  mf_set repair_cycles 0; mf_set requires ""
  echo "$base" > "$O/base"
  echo "run started: branch orch/$name from $from at BASE=$base"
  if [ "${1:-}" = "--" ]; then
    shift
    [ $# -gt 0 ] || die "no test command after --"
    local om="-"
    if [ $offline = 1 ]; then offline_or_die; om=$OFFLINE_M; echo "baseline: $OFFLINE_NOTE"; fi
    mkdir -p "$O/baseline"
    run_capture baseline baseline 0 "$om" "$ROOT" -- "$@"
    failures_of "$(awk -F'\t' 'END{print $12}' "$EV")" > "$O/baseline/failures.txt"
    parse_counts "$(awk -F'\t' 'END{print $12}' "$EV")" > "$O/baseline/counts"
    mf_set baseline_exit "$RC"
    [ -s "$O/baseline/failures.txt" ] && { echo "  known failures at BASE (every brief lists them):"; sed 's/^/    /' "$O/baseline/failures.txt" | head -30; }
    [ "$RC" -ne 0 ] && [ ! -s "$O/baseline/failures.txt" ] && echo "  the baseline failed but no failing tests could be identified: read the log before building"
  fi
  echo "tracked files ($(git ls-files | wc -l | tr -d ' ')):"
  git ls-files | head -100
}

cmd_status_inner() {
  echo "== manifest"; sed 's/^/  /' "$O/manifest"
  if [ -f "$O/candidate" ]; then
    local why; why=$(candidate_current) && echo "== candidate $(cand commit) (current)" || echo "== candidate $(cand commit) (STALE: $why)"
  fi
  [ -f "$EV" ] && { echo "== last evidence"; tail -6 "$EV" | awk -F'\t' '{ printf "  %s %-9s %-14s %s exit=%s %s\n", $1, $3, $4, substr($5,1,10), $7, $8 }'; }
  [ -f "$O/request.md" ] && echo "== request: $O/request.md" || echo "== request: not saved ($O/request.md)"
  return 0
}
cmd_status() { need_run; cmd_status_inner; }

cmd_require() {
  need_run; local r cur
  cur=$(mf_get requires)
  for r in "$@"; do
    case "$r" in review|fresh|offline) case ",$cur," in *",$r,"*) ;; *) cur="${cur:+$cur,}$r" ;; esac ;; *) die "unknown requirement '$r' (review, fresh, offline)" ;; esac
  done
  mf_set requires "$cur"; echo "requires: ${cur:-nothing beyond a passing check}"
}

cmd_ignore() {
  [ $# -eq 1 ] || die "usage: orch.sh ignore <pattern>"
  local ex; ex=$(git rev-parse --git-path info/exclude); mkdir -p "$(dirname "$ex")"
  grep -qxF "$1" "$ex" 2>/dev/null || echo "$1" >> "$ex"
  [ -f "$O/manifest" ] && mf_set locally_ignored "$(mf_get locally_ignored) $1"
  echo "ignored locally (not committed): $1"
}

cmd_candidate() { need_run; freeze_candidate || exit 1; echo "candidate: $(cand commit) tree $(cand tree)"; }

cmd_check() {
  need_run
  local label=check om="-"
  while [ $# -gt 0 ] && [ "$1" != "--" ]; do
    case "$1" in --label) label=$2; shift ;; --offline) offline_or_die; om=$OFFLINE_M; echo "tests: $OFFLINE_NOTE" ;; *) die "unknown option $1" ;; esac; shift
  done
  [ "${1:-}" = "--" ] || die "usage: orch.sh check [--label L] [--offline] -- <test command>"
  shift; [ $# -gt 0 ] || die "no test command after --"
  freeze_candidate || exit 1
  echo "candidate: $(cand commit)"
  run_capture check "$label" 1 "$om" "$ROOT" -- "$@"
  local status=$STATUS
  audit_tests "$(base_rev)" "$(cand commit)"
  case "$status" in pass|known-failures) [ "$UNAPPROVED" -eq 0 ] && exit 0 ;; esac
  exit 1
}

cmd_run() {
  need_run
  [ $# -ge 1 ] || die "usage: orch.sh run <label> [--offline] -- <command>"
  local label=$1 om="-"; shift
  [ "${1:-}" = "--offline" ] && { offline_or_die; om=$OFFLINE_M; echo "$OFFLINE_NOTE"; shift; }
  [ "${1:-}" = "--" ] || die "usage: orch.sh run <label> [--offline] -- <command>"
  shift; [ $# -gt 0 ] || die "no command after --"
  require_current
  run_capture run "$label" 0 "$om" "$ROOT" -- "$@"
  [ "$STATUS" = pass ] && exit 0; exit 1
}

ENV_ALLOW="PATH LANG LC_ALL LC_CTYPE TERM TZ USER LOGNAME SHELL VIRTUAL_ENV JAVA_HOME GOPATH GOROOT GOFLAGS CARGO_HOME RUSTUP_HOME NVM_DIR PYENV_ROOT ASDF_DIR ASDF_DATA_DIR"

cmd_fresh() {
  need_run
  local keephome=0 keeps="" deps=copy om="-" assigns=() envs=() v tmp note label=fresh
  while [ $# -gt 0 ] && [ "$1" != "--" ]; do
    case "$1" in
      --offline) offline_or_die; om=$OFFLINE_M ;;
      --keep-home) keephome=1 ;;
      --keep) keeps="$keeps $2"; shift ;;
      --deps) deps=$2; shift ;;
      --label) label=$2; shift ;;
      *=*) assigns+=("$1") ;;
      *) die "unknown option '$1'" ;;
    esac; shift
  done
  [ "${1:-}" = "--" ] || die "usage: orch.sh fresh [options] [VAR=value ...] -- <command>"
  shift; [ $# -gt 0 ] || die "no command after --"
  require_current
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/orch-fresh.XXXXXX") || die "mktemp failed"
  git worktree add -q --detach "$tmp/repo" "$(cand commit)" || { rm -rf "$tmp"; die "git worktree add failed"; }
  trap 'git -C "$ROOT" worktree remove --force "$tmp/repo" >/dev/null 2>&1; rm -rf "$tmp"; git -C "$ROOT" worktree prune' EXIT
  mkdir -p "$tmp/home" "$tmp/tmp"
  place_deps "$tmp/repo" "$deps"
  for v in $ENV_ALLOW $keeps; do
    if [ -n "${!v+x}" ]; then envs+=("$v=${!v}"); fi
  done
  [ $keephome = 1 ] && envs+=("HOME=$HOME") || envs+=("HOME=$tmp/home")
  envs+=("TMPDIR=$tmp/tmp")
  local secretish
  secretish=$(git ls-tree -r --name-only "$(cand commit)" | grep -E '(^|/)(\.env(\..*)?|id_rsa|id_ed25519|.*\.pem|credentials[^/]*\.json)$' | head -5)
  [ -n "$secretish" ] && { echo "  note: tracked files that look like secrets are part of the candidate, so the run can read them:"; printf '%s\n' "$secretish" | sed 's/^/    /'; }
  note="fresh checkout of $(cand commit | cut -c1-12); environment: allowlist of ${#envs[@]} variables$( [ $keephome = 1 ] && echo ', real HOME' || echo ', temporary HOME'); filesystem: NOT sandboxed"
  if [ "$om" = "-" ]; then note="$note; network: NOT isolated"; else note="$note; $OFFLINE_NOTE"; label="$label-offline"; case "$OFFLINE_NOTE" in *verified*) ;; *) label="$label-unverified" ;; esac; fi
  echo "$note"
  run_capture fresh "$label" 1 "$om" "$tmp/repo" -- env -i "${envs[@]}" ${assigns[@]+"${assigns[@]}"} "$@"
  case "$STATUS" in pass|known-failures) exit 0 ;; esac
  exit 1
}

cmd_tests() {
  need_run
  local to; to=$(git rev-parse HEAD)
  [ -n "$(leftovers)" ] && echo "note: the tree has uncommitted changes; this audits committed work only"
  audit_tests "$(base_rev)" "$to"
  [ "$UNAPPROVED" -eq 0 ] && exit 0; exit 1
}

cmd_diff() {
  need_run; require_current
  local c s f
  c=$(cand commit); s=$(echo "$c" | cut -c1-12)
  mkdir -p "$O/review"
  f="$O/review/candidate-$s.patch"
  git diff -U10 "$(base_rev)" "$c" -- . ":(exclude)$O" > "$f" || die "git diff failed"
  git diff --stat "$(base_rev)" "$c" -- . ":(exclude)$O" > "$O/review/candidate-$s.stat"
  ev_append "$(next_seq)" "$(now)" review-diff diff "$c" "$(cand tree)" 0 pass 0 "$(env_fp)" "" "$f" "orch.sh diff"
  echo "$ROOT/$f ($(wc -l < "$f" | tr -d ' ') lines; BASE $(base_rev | cut -c1-12)..candidate $s)"
  [ -s "$f" ] || echo "WARNING: the patch is empty: the candidate doesn't differ from BASE"
}

cmd_record() {
  need_run
  [ $# -ge 2 ] || die "usage: orch.sh record <review|recheck|manual> <pass|fail|pending> [note]"
  local kind=$1 res=$2; shift 2
  case "$kind" in review|recheck|manual) ;; *) die "kind must be review, recheck or manual" ;; esac
  case "$res" in pass|fail|pending) ;; *) die "result must be pass, fail or pending" ;; esac
  require_current
  ev_append "$(next_seq)" "$(now)" "$kind" "${*:-$kind}" "$(cand commit)" "$(cand tree)" - "$res" 0 "$(env_fp)" "" "" "record"
  echo "recorded $kind $res for candidate $(cand commit | cut -c1-12)"
}

cmd_repair() {
  need_run
  local n max
  n=$(( $(mf_get repair_cycles || echo 0) + 1 ))
  max=${ORCH_MAX_REPAIR_CYCLES:-$(mf_get max_repair_cycles)}; max=${max:-2}
  if [ "$n" -gt "$max" ]; then
    echo "REPAIR BUDGET SPENT: $max whole repair cycle(s) used. Stop: diagnose the cause (missing requirement, environment, capability, flaky test, wrong fix) and finish as partial or blocked, or ask the user."
    exit 1
  fi
  mf_set repair_cycles "$n"
  ev_append "$(next_seq)" "$(now)" repair "cycle-$n" "$(git rev-parse HEAD)" "$(git rev-parse 'HEAD^{tree}')" - open 0 "$(env_fp)" "" "" "$(show_cmd "$@")"
  echo "repair cycle $n of $max opened: $*"
}

# Prints problems (one per line). Returns 0 when there are none.
gate_problems() {
  local why c t fp req last
  why=$(candidate_current) || { echo "candidate: $why"; return 1; }
  c=$(cand commit); t=$(cand tree); fp=$(env_fp)
  awk -F'\t' -v c="$c" -v t="$t" '$5==c && $6==t && $8=="dirty-after" { print "evidence " $1 " (" $4 ") changed the tree while running: void" }' "$EV"
  last=$(awk -F'\t' -v c="$c" -v t="$t" '$3=="check" && $5==c && $6==t { x=$1 "\t" $8 "\t" $10 } END { print x }' "$EV")
  if [ -z "$last" ]; then echo "no 'check' evidence for this candidate"
  else
    case "$(echo "$last" | cut -f2)" in pass|known-failures) ;; *) echo "latest check ($(echo "$last" | cut -f1)) is $(echo "$last" | cut -f2)" ;; esac
    [ "$(echo "$last" | cut -f3)" = "$fp" ] || echo "environment changed since the latest check (fingerprint $(echo "$last" | cut -f3) -> $fp): run check again"
  fi
  req=$(mf_get requires)
  case ",$req," in *,review,*)
    awk -F'\t' -v c="$c" -v t="$t" '($3=="review"||$3=="recheck") && $5==c && $6==t { x=$8 } END { if (x!="pass") print "review required: no passing review or recheck recorded for this candidate" }' "$EV" ;;
  esac
  case ",$req," in *,fresh,*)
    awk -F'\t' -v c="$c" -v t="$t" '$3=="fresh" && $5==c && $6==t && ($8=="pass"||$8=="known-failures") { ok=1 } END { if (!ok) print "fresh-checkout run required: none passing for this candidate" }' "$EV" ;;
  esac
  case ",$req," in *,offline,*)
    awk -F'\t' -v c="$c" -v t="$t" '$3=="fresh" && $4 ~ /-offline$/ && $5==c && $6==t && ($8=="pass"||$8=="known-failures") { ok=1 } END { if (!ok) print "verified offline run required: none passing for this candidate" }' "$EV" ;;
  esac
  awk -F'\t' '$3=="manual" { m[$4]=$8 } END { for (k in m) if (m[k]!="pass") print "manual check not verified: " k }' "$EV"
  audit_tests "$(base_rev)" "$c" > "$O/.gate-audit" 2>&1
  [ "$UNAPPROVED" -eq 0 ] || echo "test-change audit: $UNAPPROVED unapproved flag(s) (orch.sh tests)"
  return 0
}

cmd_gate() {
  need_run
  local p
  p=$(gate_problems)
  if [ -z "$p" ]; then
    echo "GATE: PASS for candidate $(cand commit)"
    awk -F'\t' -v c="$(cand commit)" '$5==c && $3!="review-diff" { printf "  %-9s %-18s exit=%s %s %s\n", $3, $4, $7, $8, $12 }' "$EV"
    grep -q . "$O/baseline/failures.txt" 2>/dev/null && awk -F'\t' -v c="$(cand commit)" '$3=="check" && $5==c && $8=="known-failures" { f=1 } END { exit !f }' "$EV" && echo "  disclose: pre-existing failures remain (see $O/baseline/failures.txt)"
    exit 0
  fi
  echo "GATE: FAIL"; printf '%s\n' "$p" | sed 's/^/  - /'
  exit 1
}

cmd_finish() {
  need_run
  [ $# -ge 1 ] || die "usage: orch.sh finish <done|partial|blocked> [note]"
  local st=$1; shift
  case "$st" in
    done) local p; p=$(gate_problems); [ -z "$p" ] || { echo "REFUSED: the gate fails, so this run isn't done:"; printf '%s\n' "$p" | sed 's/^/  - /'; echo "Fix it, or finish as partial or blocked."; exit 1; } ;;
    partial|blocked) ;;
    *) die "status must be done, partial or blocked" ;;
  esac
  local t
  for t in "$O"/worktrees/*; do
    [ -d "$t" ] || continue
    if [ -z "$(git -C "$t" status --porcelain 2>/dev/null)" ]; then ( cmd_wt_finish "${t##*/}" ) || true; else echo "kept $t: it has uncommitted changes"; fi
  done
  mf_set status "$st"; mf_set finished "$(now)"; mf_set note "$*"
  {
    echo "# Run $(mf_get run_id): $st"
    echo "- base: $(base_rev)"; echo "- candidate: $(cand commit)"; echo "- branch: $(mf_get branch)"
    echo "- repair cycles: $(mf_get repair_cycles)"; echo "- note: $*"
    echo; echo "## Evidence for the candidate"
    awk -F'\t' -v c="$(cand commit)" 'NR==1 || $5==c { print "    " $1 "  " $3 "  " $4 "  exit=" $7 "  " $8 "  " $12 }' "$EV" 2>/dev/null
  } > "$O/summary.md"
  echo "run finished: $st. Record kept: $O/manifest, $O/evidence.tsv, $O/logs/, $O/summary.md"
}

cmd_stamp() {
  local dirty; dirty=$(leftovers)
  if [ -n "$dirty" ]; then echo "main tree is not clean; commit or restore these before dispatching:" >&2; echo "$dirty" >&2; exit 1; fi
  mkdir -p "$O"; : > "$O/stamp"
  # Coarse filesystem timestamps: wait so every later write is strictly newer than the stamp.
  sleep 1
  echo "stamped $(date '+%H:%M:%S'); run 'orch.sh stray' when the workers return"
}

cmd_stray() {
  [ -f "$O/stamp" ] || die "no $O/stamp; run 'orch.sh stamp' before dispatching"
  local prune line rel files outside inside status
  prune=(-path ./.git -o -path ./.claude/worktrees -o -path "./$O/worktrees")
  while IFS= read -r line; do
    case "$line" in "worktree $ROOT/"*) rel=${line#"worktree $ROOT/"}; prune+=(-o -path "./$rel") ;; esac
  done < <(git worktree list --porcelain)
  files=$(find . \( "${prune[@]}" \) -prune -o -type f -newer "$O/stamp" -print | sed 's|^\./||' | sort)
  outside=$(printf '%s\n' "$files" | grep -v "^$O/" | grep -v '^$')
  inside=$(printf '%s\n' "$files" | grep "^$O/" | grep -v "^$O/stamp$")
  status=$(leftovers)
  [ -n "$inside" ] && { echo "written in $O/ since the stamp (fine if you wrote them; a worker's report here means it left its worktree):"; printf '%s\n' "$inside" | sed 's/^/  /'; }
  if [ -z "$outside" ] && [ -z "$status" ]; then echo "OK: nothing outside $O/ written in the main tree since the stamp"; return 0; fi
  echo "STRAY: the main tree changed while workers ran. Compare each file with the worker's branch, discard it, and log it."
  [ -n "$outside" ] && { echo "files written since the stamp:"; printf '%s\n' "$outside" | sed 's/^/  /' | head -50; }
  [ -n "$status" ] && { echo "git status:"; printf '%s\n' "$status" | sed 's/^/  /'; }
  exit 1
}

cmd_wt_add() {
  local task="" deps=copy dir
  while [ $# -gt 0 ]; do case "$1" in --deps) deps=$2; shift ;; *) task=$1 ;; esac; shift; done
  [ -n "$task" ] || die "usage: orch.sh wt-add <task> [--deps copy|none|link]"
  case "$deps" in copy|none|link) ;; *) die "--deps must be copy, none or link" ;; esac
  dir="$ROOT/$O/worktrees/$task"
  [ -e "$dir" ] && die "$dir already exists"
  ensure_ignored
  git show-ref --verify --quiet "refs/heads/orch-wt/$task" && die "branch orch-wt/$task already exists"
  mkdir -p "$(dirname "$dir")"
  git worktree add -q "$dir" -b "orch-wt/$task" HEAD || die "git worktree add failed"
  mkdir -p "$dir/$O"
  place_deps "$dir" "$deps"
  echo "$dir"
}

cmd_wt_finish() {
  [ $# -eq 1 ] || die "usage: orch.sh wt-finish <task>"
  local task=$1 dir left
  dir="$ROOT/$O/worktrees/$task"
  [ -d "$dir" ] || die "no worktree at $dir"
  left=$(git -C "$dir" status --porcelain)
  [ -z "$left" ] || { echo "worktree has uncommitted changes; merge or discard them first:" >&2; echo "$left" >&2; exit 1; }
  if [ -d "$dir/$O" ]; then mkdir -p "$O/reports/$task"; cp -R "$dir/$O/." "$O/reports/$task/"; echo "copied reports to $O/reports/$task/"; fi
  git worktree remove --force "$dir" || die "git worktree remove failed"
  if git branch -d "orch-wt/$task" >/dev/null 2>&1; then echo "removed $dir and branch orch-wt/$task"
  else echo "removed $dir; kept branch orch-wt/$task because it isn't merged into $(git rev-parse --abbrev-ref HEAD)"; fi
}

cmd_caps() {
  local m v
  echo "host: $(uname -sm); $(bash --version | head -1 | sed 's/ (.*//'); $(git --version)"
  m=$(offline_method)
  if [ -n "$m" ]; then v=$(probe_offline "$m"); echo "offline (--offline): $m, $v"
  else echo "offline (--offline): NOT available here; runs can't be network-isolated by this helper"; fi
  case "$(uname -s)" in
    Darwin) echo "dependency copies: copy-on-write via cp -c where the filesystem supports it (APFS)" ;;
    *) echo "dependency copies: cp --reflink=auto (copy-on-write on btrfs/xfs, full copy elsewhere)" ;;
  esac
  echo "not enforced by this helper: filesystem reads outside the checkout; process limits; model or tool permissions"
}

[ $# -ge 1 ] || { usage; exit 2; }
sub=$1; shift
case "$sub" in
  start) cmd_start "$@" ;;
  status) cmd_status "$@" ;;
  require) cmd_require "$@" ;;
  ignore) cmd_ignore "$@" ;;
  finish) cmd_finish "$@" ;;
  candidate) cmd_candidate "$@" ;;
  check) cmd_check "$@" ;;
  run) cmd_run "$@" ;;
  fresh) cmd_fresh "$@" ;;
  clean-room) echo "note: clean-room is now 'fresh'. It is a fresh-checkout run, not a sandbox." >&2; cmd_fresh "$@" ;;
  tests|old-tests) cmd_tests ;;
  diff) cmd_diff ;;
  record) cmd_record "$@" ;;
  repair) cmd_repair "$@" ;;
  gate) cmd_gate ;;
  stamp) cmd_stamp ;;
  stray) cmd_stray ;;
  wt-add) cmd_wt_add "$@" ;;
  wt-finish) cmd_wt_finish "$@" ;;
  caps) cmd_caps ;;
  -h|--help|help) usage ;;
  *) usage; exit 2 ;;
esac
````
