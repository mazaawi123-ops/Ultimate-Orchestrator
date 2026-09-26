# Which model for which role

One real `claude -p --agent` session per role and candidate model, on a fixed task with an
objective grader, on 2026-09-26 with Claude Code 2.1.281. The harness is
`evals/release/model_matrix.sh`, the grader `evals/release/model_matrix_grade.py`; the
replies, briefs, agent files and diffs are in `records/model-matrix/`. Dollar figures are
Claude Code's local estimates, not bills. **One sample per cell:** this shows what each model
did once on one task, not how often it would.

**Candidates:** Fable 5.1 at xhigh effort; Opus 5.5 at medium; Sonnet 5 (high for the
reviewer, medium otherwise, the skill's settings at the time); Haiku 4.5 (no effort setting).

| Role | Task | Ground truth |
|---|---|---|
| Reviewer | the 781715f release run's first candidate, which runs a missed Friday job on Saturday, with the current reviewer brief | verdict FAIL with the missed-Friday case blocking; the daylight-saving edge (a run an hour late after a spring-forward weekend) is an optional extra |
| Worker | `windowed(strict=)` in more-itertools, as a worker brief | the pilot's 11 hidden checks (functional, regression, safety, artifacts) |
| Mechanical | rename one private helper at its 8 sites in `schedule`, including three test names that contain it | old name gone, new name at all 8 sites, only two files changed, tests 40/41 unchanged, mypy and black clean, committed |
| Researcher | four questions about `schedule` (callers and callees of one method, which methods assign one attribute, which tests skip without pytz) | computed from the AST and a pytest run; F1 per question |

## Results

| Role | Model | Score | Est. cost | Turns | Wall | What happened |
|---|---|---|---|---|---|---|
| Reviewer | Haiku 4.5 | 0.1 | $0.33 | 30 | 3.3 min | PASS, no findings: missed the flaw |
| Reviewer | Sonnet 5, high | 0.1 | $0.33 | 18 | 1.7 min | PASS; one observation (the timezone decision); never looked at a late run |
| Reviewer | **Opus 5.5, medium** | 0.9 | $0.32 | 7 | 0.9 min | FAIL; the missed-Friday case blocking, with a reproduction and the smallest fix; two observations; no invented findings |
| Reviewer | Fable 5.1, xhigh | 0.9 | $1.30 | 8 | 2.7 min | FAIL; the same blocking finding with a reproduction; checked daylight-saving days but not the hour, so it missed the optional edge too |
| Worker | Haiku 4.5 | 1.0 | $0.54 | 49 | 6.3 min | 11/11 |
| Worker | Sonnet 5, medium | 1.0 | $0.66 | 25 | 4.9 min | 11/11 |
| Worker | **Opus 5.5, medium** | 1.0 | $0.32 | 6 | 2.2 min | 11/11; the clearest list of assumptions |
| Worker | Fable 5.1, xhigh | 1.0 | $1.20 | 21 | 3.1 min | 11/11 |
| Mechanical | Haiku 4.5 | 0.71 | $0.20 | 14 | 0.7 min | renamed 5 of 8 sites, left the three test names, and reported "no remaining references": a false claim |
| Mechanical | **Sonnet 5, medium** | 1.0 | $0.24 | 9 | 0.5 min | all 8 sites, every check clean |
| Mechanical | Opus 5.5, medium | 0.71 | $0.31 | 4 | 0.3 min | renamed 5 of 8 sites, then reported the three test names as a remaining problem (DONE_WITH_CONCERNS) |
| Mechanical | Fable 5.1, xhigh | 1.0 | $0.79 | 5 | 0.4 min | all 8 sites, every check clean |
| Researcher | Haiku 4.5 | 0.98 | $0.26 | 23 | 1.5 min | missed the annotated assignment in `__init__` |
| Researcher | Sonnet 5, medium | 0.95 | $0.30 | 11 | 0.8 min | missed that, and two method calls |
| Researcher | **Opus 5.5, medium** | 0.98 | $0.45 | 7 | 0.6 min | missed the annotated assignment in `__init__` |
| Researcher | Fable 5.1, xhigh | 1.0 | $1.13 | 13 | 0.8 min | the only fully correct answer |

For comparison, the earlier reviewer check on the same candidate (`release-validation.md`):
Opus 5.5 at **xhigh** found the blocking case and the daylight-saving edge, at $1.42.

## Choices

| Role | Agent | Model | Why |
|---|---|---|---|
| Worker | `orch-worker` | Opus 5.5, medium | full marks at the lowest cost and the fewest turns |
| Researcher | `orch-researcher` | Opus 5.5, medium | tied with Haiku on accuracy, in a third of the turns and time; Fable was fully correct for 2.5x the cost |
| Mechanical | `orch-mechanic` | Sonnet 5, medium | the only cheap model that did the whole rename; Haiku claimed it had |
| Reviewer | `orch-verifier` | Opus 5.5, medium | caught the blocking flaw at a quarter of Fable's cost; xhigh in the same file is the upgrade for high-stakes changes (it also found the optional edge) |
| Re-checker | `orch-rechecker` | Opus 5.5, medium | not tested in this role; chosen because Sonnet at high effort passed the flawed candidate as a reviewer, and Opus 5.5 at medium cost the same ($0.32 vs $0.33) |

Haiku 4.5 has no role left: it missed the review flaw, did a partial rename and reported it
as complete, and was the slowest worker.

## Corrections made while grading

- The researcher ground truth first missed `self.unit: Optional[str] = None` in `__init__`,
  an annotated assignment. Fable listed it; the grader was wrong. Fixed, and the three other
  models lost that item.
- The reviewer grader first credited Sonnet with a blocking missed-Friday finding and Fable
  with the daylight-saving edge on word matches alone. Sonnet had written "not classified as
  blocking" about a different case; Fable had checked which day daylight-saving runs land on,
  not the hour. Both checks were tightened, and every reviewer reply was read.

## Limits

- One run per cell. Run-to-run variance is real (the trigger tests varied by one or two
  prompts between runs), so a 0.9 against a 1.0 is not a ranking.
- One task per role, and all four in two small Python repos. A reviewer task with a subtler
  flaw, or a worker task with more design freedom, could order the models differently.
- The re-checker's model was inferred, not measured in that role.
- Costs are estimates from the session stream; the user is on a subscription, so they stand
  in for usage, not money.
