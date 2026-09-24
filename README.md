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
`tests/helper/` (50 tests, including both independent reviews' reproductions).

| Guarantee | How |
|---|---|
| Tests, review and report concern the same code | `check` refuses uncommitted or untracked leftovers, freezes HEAD as the candidate, and records every command against it with exit code, time, environment fingerprint and log. A command that changes the tree voids its own evidence. `diff` only covers BASE..candidate. |
| No "done" on bad evidence | One rule for every check (tests, CI commands, fresh runs, reviews, manual checks): only its latest result counts, and it must be for the current candidate and passing. A failed CI run, a later failing fresh run, or a manual check from an earlier candidate blocks `gate` and `finish done`. `require check <id>` names checks that must exist. Runs marked `--explore` never count; `waive` disposes of a check that no longer applies, with a reported reason, but never the tests or anything required. |
| Old failures aren't blamed on the change | `start -- <tests>` records the baseline. Later failures are split into pre-existing and new. |
| Weakened tests are noticed | The audit flags deleted lines and added `skip`/`only`/`xfail`/`skipTest` markers in existing tests, runner and discovery configuration, fixtures and snapshots, and changes in skipped or executed counts. `orch.sh approve` binds an approval, with its reason, to one version of a file or one exact count movement. |
| No network when promised | `--offline` uses `unshare -n` on Linux or `sandbox-exec` on macOS, and runs only if a loopback probe returns exactly "verified"; otherwise it exits 5 and runs nothing. Only such runs, recorded in a structured field and never inferred from a label, satisfy `require offline`. |
| Honest about the environment | `fresh` runs a fresh checkout with an allowlisted environment and a temporary HOME; it is **not** a filesystem sandbox. When git-ignored files the candidate doesn't contain were present during the check, the gate wants a passing `fresh` run (with any setup) or a reasoned waiver. The fingerprint covers OS, tool versions and lock metadata, and the gate notices dependency or ignored-input files modified after the check. None of this proves which files tests read. |
| Workers don't share mutable dependencies | Worktrees get a copy of `node_modules` or the venv (copy-on-write where supported). Links inside that lead back into the main checkout are re-pointed or copied, and venv launchers are re-pointed. Links to places outside the checkout stay shared and are reported. |
| Bounded repair | `repair` allows 2 whole cycles per run. It's advisory: it records and warns. |
| An auditable record | `.orchestrator/` keeps the manifest, evidence table and logs after the run; only finished worktrees are removed. |

## Evidence so far

- **Both independent reviews' reproduced helper flaws are fixed.** The first review's 4 cases
  reproduce 4/4 on revision 9192405 and 0/4 now. The second review's 7 cases reproduce 7/7 on
  77e8ff3 and 0/7 now. Every case is also a regression test, in both directions (`docs/review/`,
  `tests/helper/`).
- **The graders are self-tested.** For each of the 8 graded tasks, a correct reference passes
  every core check, and 38 deliberately broken variants each fail the checks aimed at them
  (`evals/README.md`).
- **Trigger description:** 20/20 on the development prompts. On 20 held-out prompts: 18/20
  with the strict first-call metric, and 17/20 on a second run with the revised metric (loaded
  within 3 calls, before any edit). No false triggers either time. Single prompts flipped
  between runs (`evals/results/trigger/`).
- **Routing pilot on 2 held-out tasks** (`evals/results/pilot.md`): 12 runs, 3 routes, 2
  repeats, on commit 29fe7f4.
  - Every run passed the original hidden checks. Delivery (Done, gate, repo CI and hidden
    checks) was 3/4 Direct, 2/4 Reviewed and 4/4 for the old always-delegate skill.
  - The Reviewed and Direct misses came from helper problems since fixed.
  - A retrospective check shows 4 of 6 schedule candidates break "never on the weekend".
  - Estimated cost per delivered success: Direct $1.10, old skill $3.21, Reviewed $4.71.
  - It's directional: two tasks can't settle the routing question.
- **Release validation** (`evals/results/release-validation.md`):
  - On 781715f, 3 real runs:
    - Direct finished Done.
    - Reviewed finished Done, after its headless review completed with a repair and a re-check.
    - A request needing production credentials finished Partial, without reading them.
    - Every gate passes and every candidate passes the repo's CI. The Reviewed run left the
      missed-Friday case open and reported it as a known limit.
  - On the final revision 3c0debc, after a two-sentence change to the skill text:
    - A Reviewed run finished Done and passed every check, including the missed-Friday one.
    - The same reviewer then rated the old run's flawed candidate twice. With the old wording
      it called the missed-Friday case an observation again. With the new wording it rated
      it blocking. That's one sample each.
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
