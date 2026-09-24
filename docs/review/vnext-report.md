# code-orchestrator vNext: report for independent review

**What to review:** the `code-orchestrator` Claude Code skill after the changes made in response
to the first independent review (`independent-review.md`) and its proposal (`vnext-proposal.md`).
This report says what changed, what was measured, what the measurements support, and what they
don't. Every claim names the file that backs it.

- **Repository:** `mazaawi123-ops/Ultimate-Orchestrator`, branch `claude/busy-cannon-bs6gm7`, draft PR #1.
- **Previously reviewed revision:** `9192405` (the review cites `919240501…`).
- **The skill:** `code-orchestrator/` (SKILL.md, `scripts/orch.sh`, three references) and
  `agents/` (four agent definitions). `code-orchestrator.single-file.md` is the same skill as
  one file, with the references and the helper as appendices.
- **Author disclosure:** the builder of the skill is the same AI system (Claude, in Claude Code)
  that designed, ran and adjudicated every evaluation below. No human or independent system has
  checked these results yet. That is the main reason for this review.
- **Money:** dollar figures are Claude Code's local estimates (`total_cost_usd`: token counts at
  list price), not bills.

---

## 1. Summary

1. **The four helper flaws the first review reproduced are fixed.** The reviewer's own
   scenarios reproduce 4 of 4 on `9192405`, and 0 of 4 on the current helper
   (`reproduction-before-after.json`; `tests/helper/review_reproductions.py`).
2. **The skill was restructured as the proposal asked.** Direct (one builder) is the default,
   and delegation and review are decided separately. The reviewer gets the original request,
   and there's no pressure on it to find issues. Repair is bounded, and the evidence record
   is durable.
3. **The evaluation machinery is now published and self-tested.** Tasks are pinned to
   commits, and the runner, graders and records are all in the repo. For each of 8 tasks, a
   correct reference passes every core check, and 37 deliberately broken variants each fail
   the check aimed at them.
4. **A 12-run pilot on 2 held-out tasks: every route passed every hidden check.**
   - Direct cost $0.82 per run and took 2.7 min; Reviewed cost $2.36 and 11.3 min; the
     previous always-delegate skill cost $3.21 and 14.3 min.
   - The confirmed review findings were real but low severity, and were all in the reviewed
     runs' own drafts.
   - The pilot exposed four reliability problems, all fixed since.
5. **Nothing here establishes general superiority.** Two tasks, one main-session model, and
   adjudication by the system under test.

---

## 2. The first review's handoff list, item by item

| # | The review asked for | What was done | Evidence |
|---|---|---|---|
| 1 | Tie testing, review and reporting to the exact same candidate | `orch.sh check` refuses uncommitted or untracked leftovers. It freezes HEAD as the candidate, and records every command against it: exit code, time, environment fingerprint, log. A command that changes the tree voids its own evidence. `diff` covers only BASE..candidate. `gate` and `finish done` refuse missing, stale, failing or mismatched evidence. | `tests/helper/test_orch.py` (`ReviewA_*`, `Lifecycle`); reproduction A: 0/1 |
| 2 | Label the environment check accurately; isolate for real where isolation is promised | `clean-room` was renamed `fresh`, and it states that it is **not** a filesystem sandbox. It uses an allowlisted environment and a temporary HOME. `--offline` uses `unshare -n` (Linux) or `sandbox-exec` (macOS), proves blocking with a loopback probe, and exits 5 where it can't. | `ReviewB_*` tests; reproduction B: 0/1 (remaining by design: absolute-path reads, tracked `.env`, and loopback without `--offline`, each labelled) |
| 3 | Detect or explicitly approve skipped or weakened tests | The audit covers deleted or changed lines, and added skip/only/xfail/`skipTest` markers in existing tests. It also covers runner and discovery configuration, fixtures and snapshots, and changes in skipped or executed counts against the baseline. Approvals go in `.orchestrator/approved-test-changes`, by path or as `count:skipped` / `count:executed`, each with a reason. | `ReviewD_*` tests; reproduction D: 0/1 |
| 4 | Prevent writes through shared dependency directories | Worker worktrees get copy-on-write copies of `node_modules` or the venv (`--deps copy`, the default), not links. | `ReviewC_*` tests; reproduction C: 0/1 |
| 5 | No pressure on reviewers to find issues; give them the original request | `references/reviewer-brief.md` passes on the request verbatim, the contracts and the criteria, with decisions labelled as decisions. It says a clean review is valid, and classes findings as blocking, optional or observation. No worker self-assessment is included. | `reviewer-brief.md`; pilot reviews returned clean verdicts (section 5) |
| 6 | Route directly by default | SKILL.md makes two separate decisions, the number of builders and the amount of review, and defaults to one builder with automated checks. | `SKILL.md` "Route" |
| 7 | Cap the whole repair process; keep a compact evidence record | 2 repair cycles per run (`orch.sh repair`), advisory. `.orchestrator/` keeps the manifest, evidence table, logs and record. | `SKILL.md` step 8; `references/run-record.md` |
| 8 | A reproducible runner and held-out evaluation before new cost claims | `evals/`: pinned tasks, runner, graders with self-test, records. The pilot uses 2 tasks written after the skill was frozen. | `evals/README.md`, `evals/pilot/`, `evals/results/pilot.md` |

The review's other points:
- **Costs:** labelled as estimates throughout.
- **"Opus alone" label:** the no-skill runs are now labelled "prompted to delegate".
- **Checks:** process and reporting checks are separated from functional ones.
- **Graders:** self-tested with mutants that must fail.
- **Commits:** pinned.
- **Access-time evidence:** stated as conditional (`evals/results/measurements.md`).
- **Reviewer effort:** the review also suggested comparing reviewer effort levels on
  identical frozen patches. That **has not been done** (section 8).

---

## 3. The skill as it stands

- **Size:** SKILL.md is 2,081 words. The helper is 798 lines of bash 3.2-compatible shell.
- **The loop:**
  1. `start`: records the baseline and saves the request.
  2. Define done: criteria, contracts, the repo's CI checks, decisions.
  3. Route.
  4. Delegate only with a reason.
  5. Build, with no test weakening; approvals only with a reason.
  6. `check` the exact candidate, and run the repo's CI checks against it.
  7. Independent review (Reviewed mode).
  8. Bounded repair.
  9. `gate`, then `finish`.
- **Stop-and-ask rules:** irreversible actions, secrets, real user data, anything outside the
  repo, new dependencies or services, and material scope changes.
- **Agents:**

| Agent | Model, effort | Limits (runtime-enforced) |
|---|---|---|
| `orch-worker-haiku` | Haiku | no nested agents, 120 turns |
| `orch-worker-sonnet` | Sonnet, medium | no nested agents, 150 turns |
| `orch-verifier` | Opus, extra high | no Edit, Write or Agent tools; 80 turns |
| `orch-rechecker` | Sonnet, high | no Edit, Write or Agent tools; 60 turns |

Bash can still write, so reviewers aren't strictly read-only. The gate detects any change to the
tree. Reviewers must not install into the shared environment; a throwaway environment under
`/tmp` is allowed.

---

## 4. Validation of the tooling

| Check | Result | Where |
|---|---|---|
| skill-creator `quick_validate`, on the folder and on the single file | valid, valid | — |
| Helper round-trip in the single file | byte-identical | `tools/build_single_file.py` |
| Helper regression tests | 32/32 | `tests/helper/test_orch.py` |
| The first review's four reproductions | 0/4 reproduced | `tests/helper/review_reproductions.py` |
| Grader self-test | 8 references pass all core checks; 37/37 mutants caught; 3 harmless test edits not flagged | `evals/graders/selftest.py`, `evals/results/grader-selftest.log` |

**What the self-test found, all fixed before any new measurement:**
- **False positive:** the "no existing test weakened" check counted any changed line. An edited
  import failed every inventory run. Now only removed assertions or test definitions count.
- **Blind spot:** a test skipped with `self.skipTest(...)` passed both the graders and the
  helper's audit.
- **Lax check:** the stub check accepted a stub where only one of two overloads was updated.
- **Bad mutant:** one mutant edited the wrong function.

**Historical runs re-graded.** 28 earlier runs (v2–v5 and real repos) were exported, sanitized
and re-graded with the current graders (`evals/results/records/`, `summary.tsv`). At task level,
the earlier configurations barely differ. Every task failure is the same inventory edge case:
a comma-only CSV row skipped instead of rejected. The larger differences in older tables
came mostly from reporting checks.

**Trigger description.** Each prompt was run 3 times with a Sonnet session and `--max-turns 2`.
A prompt counts as triggered when the session's first tool call loads the skill.

| Set | Description | Score |
|---|---|---|
| Development (20; 10 should, 10 near-misses) | first vNext wording | 18/20: missed "orchestrate this…" and "hire a team of agents…" |
| Development | final wording, tuned on those two misses only | 20/20 |
| Held out (20, written before the final wording, run once) | final wording | 18/20: no false triggers; missed "implement the feature described in ISSUE.md…" (0/3, it reads the file first) and a CSV-importer bug fix asking for evidence (1/3) |

---

## 5. The routing pilot

**Design** (the review's section 6, at its size): 2 held-out tasks × 3 arms × 2 repeats = 12
real `claude -p` sessions (`evals/pilot/README.md`).

| | |
|---|---|
| Tasks | p1: more-itertools `windowed(strict=)`, well specified, mature repo with 930 tests. p2: schedule `every().weekday`, API shape and edge cases left open; 41 of 81 tests skip without pytz |
| Arm A `direct` | current skill (commit `29fe7f4`) + agents; the prompt says to use Direct mode |
| Arm B `reviewed` | same skill; the prompt says to use Reviewed mode |
| Arm C `hierarchy` | previous skill (`9192405`) + its agents, routing itself (always delegates) |
| Same in every arm | prompt, starting commit, main-session model (Opus, `--effort high`), $12 cap, tools, and the reviewer (`orch-verifier`, Opus extra high) |
| Order | seeded random, 6 at a time on one machine |
| Measures | task success by hidden checks written and self-tested beforehand; first-pass success (the code the first review saw); estimated cost; wall time; reported status; review findings adjudicated |

### Results

| Arm | Task success | First-pass | Est. cost total | Per success | Mean wall |
|---|---|---|---|---|---|
| A direct | 4/4 | 4/4 | $3.30 | $0.82 | 2.7 min |
| B reviewed | 4/4 | 4/4 | $9.42 | $2.36 | 11.3 min |
| C hierarchy | 4/4 | 4/4 | $12.84 | $3.21 | 14.3 min |

Every final candidate and every first-pass candidate passed every hidden functional,
regression and safety check. **The tasks didn't discriminate between routes on outcome**, only
on cost and time.

### Review findings, adjudicated

The adjudication used post-hoc probes (`evals/pilot/ci_probes.py`) run against **every** arm's
final code, the unreviewed Direct runs included. The probes cover:
- the repos' own CI checks: pinned `black==20.8b1`, ruff, stubtest, and no new mypy errors;
- the behaviours reviewers raised.

The probes were written after seeing the reviews, so they're reported apart from the hidden
checks. Details: `evals/results/pilot.md`; raw replies: `records/pilot/*/agents.md`.

| Run | Verdict | Confirmed | Other | Repair |
|---|---|---|---|---|
| B p1-1 | PASS | none | none | none |
| B p1-2 | PASS | none. A ~4% slowdown observation couldn't be separated from noise (0.97–1.06× on every candidate) | — | 1 cycle + re-check |
| B p2-1 | **lost** | — | — | none; its final code fails the CI format check |
| B p2-2 | PASS | fails CI format check; job lingers past `until()` over a weekend (low impact) | error-message wording | 1 cycle + re-check, both fixed |
| C p1-1 | PASS | delegated worker's strict path buffered `step` items (146 MB at step 2,000,000) | 3 nits, 1 ruling challenged | fix round + re-check, fixed |
| C p1-2 | PASS | none | 1 true nit (duplicate test) | none |
| C p2-1 | PASS | none | nits; late-Saturday question | fix round **introduced** the `until()` lingering defect; re-check missed it |
| C p2-2 | PASS | fails CI format check; silently accepts `every().hour.weekday` against its own ruling | 1 nit | fix round + re-check, both fixed |

**Observations:**
- **The confirmed defects were all in the reviewed runs' own drafts.** The Direct candidates
  have none of them.
- **The format check was the most frequent finding.** 3 of 6 first drafts of p2 failed it, which
  a deterministic check catches. The skill now tells the builder to run the repo's own CI
  checks.
- **Interpretation splits,** because the request didn't settle these: whether a missed Friday
  run may fire on Saturday (4 candidates yes, 2 no), and whether a unit before `.weekday` is
  rejected (1 candidate).

### Reliability problems the pilot exposed, all fixed afterwards

1. **Count flags couldn't be approved.** Two correct runs reported Partial after a new test that
   needs `pytz` raised the skipped count. Fix: `count:skipped` / `count:executed` approvals,
   plus a unit test.
2. **A review was lost in headless mode.** Claude Code moved a foreground reviewer to the
   background. After the main session's last turn, `claude -p` stopped it at its 10-minute idle
   limit and dropped the result (documented in Claude Code's headless docs). Fix: a skill note,
   a README note, and `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0` in the runner.
3. **A reviewer ran `pip install mypy` into the shared system Python.** Fix: no installs into
   the shared environment; a throwaway one under /tmp is allowed.
4. **The stream reports only a start-of-message output count per request.** Per-agent output
   tokens were lower bounds. Fix: relabelled `output_at_start`; per-agent cost is stated as an
   estimate.

**Changes made after the pilot haven't been re-piloted end to end:**
- count approvals (unit-tested only)
- the reviewer install rule
- the CI-check step
- the background-agent note
- the routing-evidence line

---

## 6. What the evidence supports

- **Supported:** the helper's guarantees as tested (32 tests, 4 reproductions); graders that
  pass correct code and fail the broken variants tried; the trigger scores on the stated
  prompts; and, **on these two tasks**, Direct matching the other routes on hidden checks at
  about a third to a quarter of the estimated cost.
- **Not supported:**
  - that Direct is better in general;
  - that review never pays (these tasks were too easy to fail);
  - that extra-high review effort is worth its cost;
  - any billed-cost claim;
  - behaviour on other models, languages or much larger changes.

---

## 7. Threats to validity

- **Ceiling effect:** all 12 runs succeeded, so the pilot can't measure where review or
  delegation earns its cost.
- **Author bias:** the system that built the skill also wrote the tasks, graders and probes, and
  adjudicated findings. Not blind; no inter-rater check.
- **Post-hoc probes:** written after reading the reviews.
- **Sample:** 2 tasks, 2 repeats, one main-session model, one day, library-sized changes.
- **Environment:** runs shared a machine, 6 at a time. One re-checker installed `mypy` into the
  system Python mid-pilot; no grader or probe depends on it.
- **Tuning:** the trigger description was tuned on the development prompts. The held-out set
  was run once, after tuning.

---

## 8. Not resolved

- The helper does not sandbox the filesystem. Use Claude Code's own sandbox where isolation
  matters.
- The macOS paths (`sandbox-exec`, `cp -c`) and Windows are untested.
- The repair cap is advisory. Reviewer writes through Bash are detected, not prevented.
- No reviewer-effort comparison on identical frozen patches, and no false-alarm rate on
  known-correct patches.
- No task where Direct fails, so the value of review on risky or weakly tested work is
  unmeasured.
- 2 of 20 held-out trigger prompts read a file before loading the skill.

---

## 9. Questions for the reviewer

1. Do the helper fixes close the four original flaws without opening new ones? Worth
   checking: `approved count:*` could hide a real weakening; the `leftovers` / `ignore`
   interaction; environment fingerprinting.
2. Is the Direct default justified by this evidence, or does the skill now under-use review for
   risky work? What task would you use to find review's break-even point?
3. Are the pilot's adjudications sound? The records hold every reviewer reply, patch and probe.
4. Is anything in SKILL.md unnecessary cost, such as instructions the model re-reads each turn
   without changing behaviour, or missing?
5. Are the post-pilot changes (section 5) safe to ship without re-running the pilot?

---

## 10. How to reproduce

```
python3 -m unittest discover -s tests/helper                   # 32 tests
python3 tests/helper/review_reproductions.py                    # the first review's scenarios
python3 evals/make_fixtures.py
bash evals/runner/prepare_repos.sh evals/real-repos.json /tmp/repos
bash evals/runner/prepare_repos.sh evals/pilot/tasks.json /tmp/pilot
python3 evals/graders/selftest.py --fixtures evals/fixtures --repos /tmp/repos --pilot /tmp/pilot
python3 evals/runner/trigger_eval.py --skill code-orchestrator --evals evals/trigger/heldout.json --runs 3
mkdir -p /tmp/old && git archive 9192405 code-orchestrator agents | tar -x -C /tmp/old
bash evals/pilot/run_pilot.sh /tmp/pilot /tmp/pilot-results /tmp/old 2 6   # about $25, estimated
```

Grading, probes and the summary: `evals/pilot/README.md`.

## 11. File index

| Path | What |
|---|---|
| `code-orchestrator/SKILL.md` | the skill |
| `code-orchestrator/scripts/orch.sh` | the helper |
| `code-orchestrator/references/` | `run-record.md`, `worker-brief.md`, `reviewer-brief.md` |
| `agents/` | the four agent definitions |
| `code-orchestrator.single-file.md` | the whole skill in one file |
| `tests/helper/` | helper tests and the first review's reproductions |
| `docs/review/` | the first review, the proposal, before/after results, this report |
| `evals/README.md` | how the evaluation works |
| `evals/results/pilot.md` | pilot results |
| `evals/results/records/` | 28 historical runs and 12 pilot runs, sanitized |
| `evals/results/measurements.md` | historical measurements, with their limits |
| `evals/results/trigger/` | trigger results |
