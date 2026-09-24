# Response to the second independent review

**Reviewed revision:** 77e8ff3. **This response covers:** c640ceb (helper), 781715f
(evaluation and the first release validation), 3c0debc (the final skill revision, also
release-validated) and later commits on `claude/busy-cannon-bs6gm7`. The review itself is in
`second-review.md`.

**Summary:** all seven reproduced helper failures are fixed. Each one is now a regression
test in both directions: the bad evidence blocks completion, and a valid rerun or an explicit
disposition lets the run finish. The benchmark now reports hidden checks, workflow
completion, repo CI, delivery and false completion claims separately, and the missed-Friday
case is scored as a retrospective check. A small release validation ran on 781715f and
again on the final revision, 3c0debc. The architecture is unchanged, as the review recommended.

The same AI system that built the skill made these changes and ran these checks. They
still need independent confirmation.

## The seven reproduced cases

The review's own script (`tests/helper/second_review_reproductions.py`, verbatim apart from
default paths) reproduces **7/7 on 77e8ff3** and **0/7 now**. Results are in
`second-review-before.json` and `second-review-after.json`. Each case also has tests in
`tests/helper/test_orch.py`, class `SecondReview`, covering both directions.

| # | Finding | Change | The fixed behaviour |
|---|---|---|---|
| 1 | A failed CI command didn't block Done | One eligibility rule for every piece of evidence. A check's identity is its kind and a stable label, and only its latest result counts. That result must be for the current candidate and passing. `require check <id>` names checks that must exist. `run --explore` marks runs that never count, such as a reproduction expected to fail. `waive <id> <reason>` disposes of an unrequired check, and the reason is reported. | `run:ci-format latest result (003) is fail` blocks `gate` and `finish done`; a later passing run of the same label clears it |
| 2a | An earlier fresh pass outweighed a later failure | Same rule: the latest fresh result counts | `fresh:fresh latest result (004) is fail` |
| 2b | A manual pass was reused after the candidate changed | `record manual <result> --id <id>` gives manual checks a stable identity, separate from the note. Evidence from an earlier candidate is stale. | `manual:... was last recorded for an earlier candidate` |
| 3 | A label ending in `-offline` satisfied the offline requirement, and `*verified*` matched `unverified` | Isolation is a structured evidence column (`net`), set only when the probe returns exactly `verified`. Any other probe result exits 5 and runs nothing. Labels no longer carry meaning. The test hook can only force a non-verified result. The tests' own capability check was fixed too. | `offline run required: no passing check --offline or fresh --offline with verified isolation` |
| 4 | Copied dependencies kept a writable link into the main checkout | After copying, links that resolve into the main checkout are re-pointed to the copy's own path, or the target is copied. Venv launchers and `activate` scripts naming the original venv are rewritten. Links to places outside the checkout stay shared and are reported. | `re-pointed or copied 1 link(s) in node_modules that led back into the main checkout`; the main file is unchanged |
| 5a | An ignored generated module made the check pass while a fresh checkout failed | `check` records git-ignored inputs the candidate doesn't contain, excluding dependency folders and known caches. The gate then wants a passing `fresh` run, whose setup can generate them, or a waiver saying they aren't inputs. | `git-ignored files the candidate does not contain were present during the check (generated_settings.py)` |
| 5b | A changed dependency file left the fingerprint and gate unchanged | The gate notices files in dependency folders or ignored inputs added or modified after the latest check (by modification time, caches excluded). The fingerprint's claim is narrowed in the help text and the README. | `files in dependency folders or ignored inputs changed after the latest check (e.g. node_modules/package/marker.txt)` |

**Also from the handoff:**
- Test-change approvals are bound: `orch.sh approve <path>` records the approved blob, and
  `approve count:skipped` records the exact movement (`41->42`). A later, different change
  needs a new approval. A hand-written, unbound line isn't accepted.
- Writing the tests found one bug in the new `approve`: the reason for a count approval was
  overwritten by the counts. It's fixed.

**Checks:**
- Helper tests: 50/50. They were 32 at 77e8ff3; the offline tests run where `unshare -n`
  works.
- First review's four cases: still 0/4.
- False-positive check on three real repos (schedule, more-itertools, qs): each gate passes
  after a normal check. Caches and dependency folders don't trigger the ignored-input rule.

## Evaluation corrections

- **Metric names:** `task_success` is now `hidden_checks_passed` everywhere new. The older
  gradings are kept as `grading.at-the-time.json`.
- **Missed-Friday check:** "A missed Friday run doesn't fire on Saturday or Sunday; it runs
  on Monday" is marked retrospective. It counts only in `hidden_checks_passed_retrospective`,
  reported beside the original held-out score. The self-test's reference now honours it, and
  a new mutant that makes the run up at the weekend is caught: 8 references, 38 mutants and
  3 harmless edits, all passing.
- **Separate measures:** `evals/pilot/summarize.py` reports workflow completion, repo CI,
  delivery and false completion claims separately. Cost per delivered success keeps every
  attempt's cost.
- **Pilot, re-scored** (`evals/results/pilot.md`):

| Arm | Hidden | + retro. | Workflow completed | Repo CI | Delivered (retro.) | False Done claims (retro.) | Est. cost per delivered (retro.) |
|---|---|---|---|---|---|---|---|
| Direct | 4/4 | 2/4 | 3/4 | 4/4 | 3/4 (2/4) | 0 (1) | $1.10 ($1.65) |
| Reviewed | 4/4 | 3/4 | 2/4 | 3/4 | 2/4 (2/4) | 0 (0) | $4.71 ($4.71) |
| Previous skill | 4/4 | 3/4 | 4/4 | 4/4 | 4/4 (3/4) | 0 (1) | $3.21 ($4.28) |

- **"Never" is now read literally.** I agree with the review: a missed Friday run firing on
  Saturday breaks the request as written. 4 of 6 schedule candidates do it, including both
  Direct runs. The claim that Direct's outputs had none of the relevant defects has been
  withdrawn. The skill now says to read absolute words literally.
- **Reviewed's lower completion is mostly the helper's fault.** Its two schedule misses came
  from helper problems since fixed: an unapprovable count flag, and a review lost to the
  headless idle limit.
- **Trigger metric:** it now counts a load within the first 3 tool calls and before any edit,
  so reading an issue file first isn't a miss. A second held-out run under this metric
  scored 17/20, with no false triggers. Two prompts that were 3/3 in the first run went 0/3,
  with an unchanged description. That is run-to-run variance, reported rather than tuned
  away.

## Release validation

Three real sessions on commit 781715f (`evals/results/release-validation.md`, records in
`evals/results/records/release/`):

| Run | Reported | Gate | Hidden checks (retro.) | Repo CI | Est. cost |
|---|---|---|---|---|---|
| Direct, with the repo's CI and a skip-count approval | Done | PASS | pass (pass) | clean | $1.21 |
| Reviewed, headless review + repair + re-check | Done | PASS | pass (**fail**) | clean | $4.37 |
| Needs production credentials | Partial, canary not read | PASS | pass (pass) | clean | $1.13 |

- **The mechanics worked in all three runs:**
  - registered required CI checks with pinned tools;
  - bound count approvals, re-approved when a repair moved the count;
  - a passing fresh run, network-isolated in one run;
  - the background review completing;
  - an honest Partial when production access was needed.
- **The Reviewed run's gap:** its reviewer rated the missed-Friday case an observation, and
  the builder reported Done with it disclosed.
- **Follow-up, checked on the final revision 3c0debc:**
  - **The change:** after that run, the reviewer brief made a failed absolute requirement
    blocking, and SKILL.md says library precedent isn't acceptance.
  - **A Reviewed run on 3c0debc** finished Done and passed every check, including the
    retrospective one. Its builder skipped weekend runs from the start, so the new rule had
    nothing to block.
  - **The rule itself:** the same reviewer got the 781715f run's flawed candidate twice, with
    briefs differing only in the new sentence.
    - With the old wording, it rated the missed-Friday case an observation again, citing
      library precedent.
    - With the new wording, it rated it blocking.
    - That's one sample each (`evals/results/release-validation.md`, section "Final
      revision").

## Remaining limits

- **Fingerprint and ignored inputs:** these are detections, not proof. Only a passing `fresh`
  run shows the candidate works from its own contents plus a declared setup. Modification
  times can miss a change within the same second on coarse filesystems. Removed files in
  dependency folders aren't noticed.
- **Waivers:** a waiver is an explicit, reported escape hatch. A model could misuse it, but
  the report must list each one with its reason.
- **Dependency links:** links outside the checkout (for example global npm links or system
  interpreters) stay shared and are only reported.
- **Untested platforms:** the macOS paths (`sandbox-exec`, `cp -c`, the physical-path
  handling for `/tmp`) and Windows are untested.
- **Advisory limits:** the repair cap is advisory. Reviewer writes through Bash are detected,
  not prevented.
- **No re-pilot:** the pilot hasn't been re-run on the final revision. Its delivery numbers
  describe 29fe7f4.
