# Reviewer brief

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

## Full review

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

## Targeted re-check (after a repair)

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
