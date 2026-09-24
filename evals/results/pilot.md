# Routing pilot: results

The design is in `../pilot/README.md`: 2 held-out tasks × 3 arms × 2 repeats = 12 real
`claude -p` sessions. The main session was Opus at `--effort high` in every arm, with a $12
cap per run. They ran on 2026-09-24 with Claude Code 2.1.281, the current skill at commit
29fe7f4, and the previous skill at commit 9192405. Every run's prompt, report, patch, usage,
grading, probes and agent replies are in `records/pilot/`.

**This is directional.** Two tasks, two repeats and one main-session model can expose a
wasteful route, but they can't show that one route is better in general.

## Outcome, delivery and cost

Each measure is reported on its own (`../pilot/summarize.py`; per run:
`records/pilot/delivery-summary.json`):

- **Hidden checks:** the functional, regression and safety checks written and self-tested
  before the runs. This is the original held-out score.
- **+ retrospective:** the hidden checks plus one check added after the second independent
  review. A Friday run missed until the weekend must not fire on Saturday or Sunday, because
  the task says "never on Saturday or Sunday". It is reported beside the original score and
  never replaces it.
- **Workflow completed:** the run finished Done. For the current skill, that means through its
  own gate. The previous skill has no gate, so its own "Done" is taken at its word.
- **Repo CI clean:** the repo's own CI checks pass (post-hoc probes).
- **Delivered:** all of the above. Cost per delivered success keeps every attempt's cost.
- **False Done claims:** the run said Done while a hidden or CI check fails.

| Arm | Hidden checks | + retrospective | Workflow completed | Repo CI clean | Delivered | Delivered (retro.) | False Done claims (retro.) | Est. cost total | Per delivered (retro.) | Mean wall |
|---|---|---|---|---|---|---|---|---|---|---|
| A `direct`: one builder | 4/4 | 2/4 | 3/4 | 4/4 | 3/4 | 2/4 | 0/4 (1/4) | $3.30 | $1.10 ($1.65) | 2.7 min |
| B `reviewed`: builder + reviewer | 4/4 | 3/4 | 2/4 | 3/4 | 2/4 | 2/4 | 0/4 (0/4) | $9.42 | $4.71 ($4.71) | 11.3 min |
| C `hierarchy`: previous skill | 4/4 | 3/4 | 4/4 | 4/4 | 4/4 | 3/4 | 0/4 (1/4) | $12.84 | $3.21 ($4.28) | 14.3 min |

| Task | A direct | B reviewed | C hierarchy |
|---|---|---|---|
| more-itertools `windowed(strict=)` | $0.66, $0.68; 3.0 min | $1.56, $2.03; 9.7 min | $2.57, $1.74; 11.8 min |
| schedule `every().weekday` | $1.02, $0.94; 2.5 min | $2.77, $3.06; 12.9 min | $4.61, $3.92; 16.9 min |

Costs are Claude Code's local estimates at list price, not bills.

- **Every candidate passed every original hidden check, final and first-pass alike.** Review
  and repair didn't change that score in any of the 12 runs.
- **Passing hidden checks isn't delivery.** On the schedule task, one Direct run and one
  Reviewed run finished Partial on correct code: a count flag that couldn't be approved,
  since fixed. The other Reviewed run lost its review and never finished. B's delivery rate
  mostly reflects helper problems that are fixed in the final revision, but not re-piloted.
- **By the literal reading of "never", 4 of 6 schedule candidates have a requirement
  defect:** both Direct runs, one Reviewed run and one old-skill run fire a missed Friday run
  on Saturday. Two of them reported Done anyway. The original grader polled every day, so it
  missed this.
- **Direct cost about a third as much as Reviewed and a quarter as much as the old hierarchy
  per run, and took a fifth to a quarter of the time.** Per delivered success it still costs
  least: $1.10 against $3.21 and $4.71 ($1.65 against $4.28 and $4.71 retrospectively).

## What the reviews found, adjudicated

The findings were checked by hand and by probes written after the reviews
(`../pilot/ci_probes.py`, results in each record's `probes.json`). The probes run the repos'
own CI checks and the behaviours reviewers raised against every arm's final code, including
code no one reviewed. They were written after seeing the reviews, so they're reported apart
from the hidden checks.

| Run | Review verdict | Adjudicated findings | Repair |
|---|---|---|---|
| B more-itertools 1 | PASS, no findings | — | none |
| B more-itertools 2 | PASS | one observation: ~4% slower default path. My timing couldn't separate it from noise: every candidate measured 0.97–1.06× base | 1 cycle + re-check; default path now identical to base |
| B schedule 1 | **lost** (see below) | — | none; its final code fails the repo's pinned `black` check |
| B schedule 2 | PASS | **2 confirmed:** fails the repo's CI format check (`black==20.8b1`); a job lingers past its `until()` deadline over a weekend (low impact). 1 cosmetic: an error message | 1 cycle + re-check; both fixed, nothing broken |
| C more-itertools 1 | PASS | **1 confirmed should-fix:** the delegated worker's strict path buffered `step` items (146 MB at step 2,000,000); 3 nits and one challenged ruling | fix round + re-check; fixed |
| C more-itertools 2 | PASS | 1 true nit: a duplicated test | none |
| C schedule 1 | PASS | nits only (a dead condition, no timezone test, a docs comment), a DST corner case, and whether a missed Friday run may fire on Saturday | fix round + re-check. It adopted "never on the weekend", and that change **introduced** the `until()` lingering defect. The re-check missed it |
| C schedule 2 | PASS | **2 confirmed:** fails the CI format check; accepts `every().hour.weekday` against its own "fail loudly" ruling | fix round + re-check; both fixed |

- **The defects the reviews confirmed were in the reviewed runs' own drafts.** The Direct
  candidates don't have those: they pass the pinned `black` check, have no `until()`
  lingering and use O(n) memory. The memory defect came from delegated code, as in the
  earlier real-repo runs. The Direct candidates do share the missed-Friday defect (below),
  which no review flagged as blocking.
- **One repair made things worse.** An old-skill fix round, acting on nits, introduced a
  defect that its re-check didn't catch.
- **A cheap deterministic check covers the most common finding.** 3 of 6 first drafts of the
  schedule task failed the repo's pinned formatting check. One shipped that way, because its
  review was lost. The skill now tells the builder to run the repo's own CI checks on the
  candidate.
- **A missed Friday run on Saturday is a defect by the literal reading.** The first version
  of this report called it an interpretation. The second independent review disagreed,
  because the request says "never", and I agree. Four candidates run it late on Saturday,
  as the library does for daily jobs, and two skip it. Two old-skill verifiers noticed it:
  one raised it as a nit needing a decision, and the other declined to judge it. The retrospective check now scores it, apart from the original
  score, and the skill now says to read absolute words literally. Rejecting a unit placed
  before `.weekday` remains a strictness choice: only one candidate does it.

## Reliability problems the pilot found, all fixed afterwards

1. **Two false "Partial" reports.** A new timezone test skips without `pytz`, like 41
   existing ones, so the skipped count rose. The count flag had no way to be approved. Both
   runs refused to hide the test and reported Partial on correct code. Fix: approvals
   `count:skipped` / `count:executed` with a reason.
2. **A lost review.** Claude Code moved a foreground reviewer to the background. The main
   session ended its turn, and `claude -p` stopped the reviewer after its 10-minute idle
   limit and dropped the result. The run ended "waiting" with no gate and no report. Fix: a
   skill note, a README note, and `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0` in the runner.
3. **An install into the shared environment.** A re-checker ran `pip install mypy` into the
   system Python mid-pilot. That's a confound for later runs, but no grader or probe depends
   on it. Fix: reviewers may use throwaway environments under /tmp only.
4. **Per-agent output tokens.** The stream reports only a start-of-message count, so
   `usage_by_agent` output counts were lower bounds. Fix: the field is now labelled
   `output_at_start`, and cost per agent is stated as an estimate.

## What this means for routing

- On these two tasks, well specified or mildly ambiguous with a decent test suite, **Direct
  passed the same hidden checks for a quarter to a third of the cost**, and had the lowest
  cost per delivered success. That supports Direct as a cost-conscious default. It doesn't
  show equal delivered quality, or that review is unnecessary on riskier work.
- **Review found real, low-severity issues:** CI formatting, a deadline edge case, and memory
  in delegated code. None changed task success here. It's worth its cost where consequences
  are serious or tests are weak, which is where the skill routes it.
- **The old hierarchy was the most expensive and slowest,** and its repair round introduced
  a defect.

## Limits

- 2 tasks, 2 repeats, one main-session model and one day. Library-sized changes only.
- The hidden checks cover the request, not everything that matters. The probes were written
  after seeing the reviews.
- Adjudication was done by the same system that built the skill, not blind. A stronger study
  would use independent, blinded raters.
- The runs shared one machine, six at a time. Wall times include that contention.
- The cost of lost or failed work stays in each arm's total.
- **The pilot ran commit 29fe7f4, not the final revision.** The helper and skill changes made
  since then are validated by unit tests and a small end-to-end release check
  (`release-validation.md`), not by re-running the pilot.
