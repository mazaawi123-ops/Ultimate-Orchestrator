# Evals

Everything needed to re-run the measurements: task definitions pinned to exact commits, the
runner, the graders, the graders' self-test, and the records of the runs already made.

## Task sets

| File | Tasks | Role |
|---|---|---|
| `evals.json` | 3 small fixture repos (todo-cli, inventory, textkit), made by `make_fixtures.py` | development: earlier designs were tuned on these |
| `real-repos.json` | humanize, click, qs at pinned commits | development: the real-repo lessons came from these |
| `pilot/tasks.json` | more-itertools `windowed(strict=)`, schedule `every().weekday` at pinned commits | held out: written after the current skill was frozen, and not used to tune it |

A task names its repo, the pinned commit, the setup commands, the test command, any
environment it needs, its grader and the exact prompt.

## Replaying a run

```
# 1. Prepare the repos (clones at the pinned commit on branch main; setup installs test deps)
python3 evals/make_fixtures.py                                    # fixtures → evals/fixtures/
bash evals/runner/prepare_repos.sh evals/real-repos.json /tmp/repos
bash evals/runner/prepare_repos.sh evals/pilot/tasks.json /tmp/pilot

# 2. Run one arm on one task (a real `claude -p` session on a fresh copy of the repo)
bash evals/runner/run_e2e.sh --tasks evals/pilot/tasks.json --id p1 --repos /tmp/pilot \
  --out /tmp/results --config direct --run 1 \
  --skill code-orchestrator --agents agents \
  --route "Use the code-orchestrator skill in Direct mode (no delegation, no independent review)."

# 3. Grade it
python3 evals/graders/grade_repos.py windowed_strict /tmp/results/more-itertools-windowed-strict/direct/run-1
python3 evals/graders/grade_fixtures.py --run todo <run dir>        # fixture tasks
```

`run_e2e.sh` copies the prepared repo, installs the skill and agents as project files,
appends a line saying nobody is available to answer questions (plus the route line, if any),
and runs `claude -p` with a hard `--max-budget-usd` cap. `collect.py` then writes
`timing.json` and fills `outputs/` with the final report, the patch against the base commit,
the git state, and the run's `.orchestrator/` record.

`timing.json` holds Claude Code's own cost estimate (`total_cost_usd`: token counts at list
price, calculated locally). **It is an estimate, not a bill.** It also keeps request-level
token counts per agent and model, so a run can be re-priced exactly.

## Graders

`graders/grade_fixtures.py` and `graders/grade_repos.py` run hidden checks against the final
working tree. Every check has a category, and each category is reported separately:

| Category | What it checks |
|---|---|
| functional | the requested behaviour |
| regression | the full suite, and behaviour that must not change |
| safety | existing tests not deleted, weakened or skipped |
| artifact | deliverables the request names: tests, stubs, docs, changelog |
| reporting | what the final report says (a heuristic, reported apart from the code) |

`task_success` means every functional, regression and safety check passed. Process checks
(artifact, reporting) are never mixed into it.

**Self-test.** A checker is only trustworthy if it passes a correct solution and fails broken
ones. `graders/selftest.py` applies a correct reference implementation of each of the 8 tasks
and asserts it passes every core check. It then applies mutants, each one realistic bug, and
asserts the checks aimed at that bug fail. Every task has one mutant that weakens an existing
test (a deleted assertion, or an added `skip`/`skipTest`). Three tasks also get a harmless
test edit (an import changed, a test added, imports reordered), which must not be flagged.

```
python3 evals/graders/selftest.py --fixtures evals/fixtures --repos /tmp/repos --pilot /tmp/pilot
```

The last run (`results/grader-selftest.log`) passed: 8 references pass, 37 mutants are
caught, and 3 harmless edits pass. Writing it found four problems, all fixed:
- The "no existing test weakened" check counted any changed line, so an edited import failed
  every inventory run. Now only removed assertions or test definitions count.
- A test skipped with `self.skipTest(...)` passed both the graders and the helper's audit.
- The stub check accepted a stub where only one of `windowed`'s two overloads gained `strict`.
- One mutant edited the wrong function: other functions in `more.pyi` take `strict` too.

The qs reference is a wrapper, so the lint check is excluded for it alone.

## Trigger tests

`trigger/dev.json` holds the 20 prompts the description was tuned on. `trigger/heldout.json`
holds 20 more, written before the final description and run once against it. Each set has
10 prompts that should load the skill and 10 near-misses that shouldn't.

```
python3 evals/runner/trigger_eval.py --skill code-orchestrator --evals evals/trigger/heldout.json --runs 3
```

A run counts as triggered when the session's first tool call loads the skill. That's strict:
a session that reads a named file first and loads the skill second counts as a miss. Results
are in `results/trigger/`.

## Records

`results/records/` holds the runs behind `results/measurements.md` (iterations v2–v5 and the
real-repo runs), exported by `runner/export_records.py`:

- `prompt.txt`, `final_report.md`, any plan, notes or report files the run left, and `changes.patch`
- `timing.json`, recomputed from the run's stream log
- `grading.json`: the current graders' result, re-graded from the run's final tree
- `grading.at-the-time.json`: the grading recorded when the run was measured, by an earlier
  version of the same checks without categories

`summary.tsv` has one row per run. Paths, session links and e-mail addresses are replaced by
placeholders. Models are named by family (Opus, Sonnet, Haiku), as in the agent files.
The raw stream logs aren't published: they hold the full transcripts, environment details
included.

## Limits

- Most configurations ran once, and the tasks are few. Differences of a few checks or a few
  dollars are within run-to-run noise.
- Hidden checks cover what the task asks for, not everything that matters. "Equal on the checks"
  isn't "equal quality".
- The development tasks were used to tune earlier designs. Only `pilot/` is held out.
