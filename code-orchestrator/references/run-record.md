# Run record

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
