# Routing pilot

The independent review's proposed experiment (`docs/review/independent-review.md`, section 6),
at its suggested size: **2 held-out tasks × 3 arms × 2 repeats = 12 runs**. It's directional:
12 runs can expose an obviously wasteful route, but they can't prove one route is better in
general.

## Tasks

Both were written after the current skill was frozen, and neither was used to tune it. Each
is pinned to a commit in `tasks.json`.

| Task | Repo | Why this task |
|---|---|---|
| p1: `windowed(strict=)` | more-itertools (mature, ~930 tests) | well specified: behaviour, laziness, stub and docstring are all stated |
| p2: `every().weekday` | schedule (40 tests pass and 41 skip at the pinned commit) | real ambiguity: the API shape and its interaction with `.at()`, intervals and `until` are left open |

## Arms

| Arm | Configuration | Question |
|---|---|---|
| A `direct` | current skill + agents, told to use Direct mode | cost and outcome with one builder and no reviewer |
| B `reviewed` | current skill + agents, told to use Reviewed mode | what one independent review adds |
| C `hierarchy` | the previous skill (commit 9192405) + its agents, routing itself | does delegated building justify its coordination and repair cost? |

The arms share everything else:
- the task prompt and starting commit
- the main-session model and effort: `opus`, `--effort high`
- the `--max-budget-usd 12` cap
- the tools and the dependency environment
- the reviewer: `orch-verifier`, Opus at extra-high effort, in both agent sets

A isn't told to delegate. Runs start in a seeded random order (`order.txt`), six at a time.

## Measures

- **Task success:** every functional, regression and safety check passes, by the self-tested
  graders in `../graders/`. Artifact and reporting checks are reported separately.
- **First-pass success:** the code the first review saw, graded the same way. For the
  current skill, that's the commit in its `review-diff` evidence row. For the previous skill,
  it's BASE plus `diff-1.patch`.
- **Estimated cost and wall time.** The cost per success keeps failed attempts' cost in the
  numerator.
- **Review findings, adjudicated by hand:** confirmed defects, false alarms, and defects
  introduced by repair.
- **The status each run reported** (Done / Partial / Blocked), and whether it matched the
  graders.

## Replay

```
bash evals/runner/prepare_repos.sh evals/pilot/tasks.json /tmp/pilot
mkdir -p /tmp/old && git archive 9192405 code-orchestrator agents | tar -x -C /tmp/old
bash evals/pilot/run_pilot.sh /tmp/pilot /tmp/pilot-results /tmp/old 2 6
python3 evals/graders/grade_repos.py windowed_strict /tmp/pilot-results/more-itertools-windowed-strict/*/run-*
python3 evals/graders/grade_repos.py schedule_weekday /tmp/pilot-results/schedule-weekday/*/run-*
python3 evals/pilot/summarize.py /tmp/pilot-results --candidates
python3 evals/runner/extract_agents.py /tmp/pilot-results/*/*/run-*   # briefs and replies, for adjudication
```

Results: `../results/pilot.md`.
