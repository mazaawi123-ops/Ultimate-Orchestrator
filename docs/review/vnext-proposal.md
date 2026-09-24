# Proposal: code-orchestrator vNext

This is the design I recommend implementing and testing next. It is based on the independent review of revision 919240501fd5bc50b39438f15ee586a336ef133a. It is a proposal, not an installed skill or a proven benchmark winner.

**Purpose:** finish coding tasks correctly at the lowest practical total cost, including planning, implementation, review and repairs.

Keep this skill focused on coding. A future general coordinator can route research, documents and other work to separate skills.

## 1. Make two decisions independently

The number of builders and the amount of review answer different questions.

| Decision | Default | Increase it when |
|---|---|---|
| How many builders? | One capable main session plans and implements | Substantial independent pieces, useful separation of context, or an explicit user request justify delegation |
| How much review? | Relevant automated checks and direct inspection | Behavior is uncertain, consequences are substantial, checks are weak, integration is difficult, or the user requests independent verification |

Examples:
- A mechanical rename across several files: one builder, standard checks.
- A one-line authorization change: one builder, independent review.
- Two substantial independent components: separate builders, merged validation; add independent review for integration or behavioral risk.
- A poorly specified feature: resolve material ambiguity before splitting it into workers.

File count, line count and an impressive number of agents should not determine the workflow.

## 2. Recommended roles and model policy

| Role | Responsibility | Model policy |
|---|---|---|
| Main session | Understand, choose the route, plan proportionately, implement or delegate, integrate and finish | Use the user's selected capable model; let it implement directly |
| Optional worker | Complete a bounded deliverable with sufficient context | Use the cheapest available model demonstrated to handle that type of work |
| Optional independent reviewer | Check the original intent and candidate; produce evidence for defects | Choose capability for the difficulty of the review; calibrate effort on frozen candidate patches |

If Mo chooses Opus/high for the main session, keep that choice and let that session build. Do not add a separate planner purely to preserve a hierarchy.

Use Haiku for a bounded transformation only when writing the brief is clearly less work than doing the transformation. Treat Sonnet or Opus review settings as configurable candidates to test, rather than universally optimal assignments. Extra-high effort should earn its cost through evaluation.

Use only the models, delegation controls and tools actually available in the host. Keep provider-specific agent settings separate from the core skill.

## 3. Proposed core instructions

The following is a compact behavioral specification to turn into SKILL.md. Keep detailed templates and platform mechanics outside this core.

**Trigger:** Use for implementing, debugging, refactoring or migrating code when a repeatable completion and verification workflow is useful. Follow explicit invocation. Leave standalone explanations, PR-only reviews and unrelated work to their existing workflows.

**Goal:** Deliver the requested behavior with evidence, at proportionate total effort. Prefer a capable main session. Delegate when there is a concrete benefit.

1. Understand the original request and relevant repository instructions. Inspect only enough context to identify behavior, interfaces and useful checks. Preserve existing user work. Ask only about ambiguities that materially change the requested outcome or require new authorization.

2. Establish what completion means. Record concise, checkable acceptance criteria and any existing relevant failures. Small tasks may keep this in the conversation; longer, delegated or interruptible tasks need a durable run record. Preserve established contracts unless the requested change deliberately alters them.

3. Choose execution and review separately. Use one builder by default. Delegate substantial independent work or a bounded task that can be briefed economically. Use independent review when risk, uncertainty, weak coverage or the user requires it. Keep the initial worker count small.

4. Give a worker the goal, relevant original requirements, allowed work area, interfaces, useful commands, known failures and an expected deliverable. Include examples where the behavior is genuinely ambiguous. Let the worker inspect relevant source. Request a concise result, material assumptions, remaining problems and evidence locations.

5. Implement and check progressively. For a bug, obtain a focused failing reproduction when practical. Run relevant tests while editing and meaningful integrated checks before delivery. Inspect changes to existing tests and test configuration. Explain legitimate test updates; never weaken tests solely to make a change pass.

6. Create an identifiable candidate containing all intended changes. Test, review and deliver that same candidate. Account for unintended or missing files. Tie evidence to the source, tests, command and relevant environment. Invalidate affected evidence after changes.

7. Give an independent reviewer the original request, relevant contracts, labeled assumptions, acceptance criteria and the candidate. Let it assess behavior before seeing worker self-assessments. Require reproducible or source-grounded findings. A clean review is valid. Record unverified behavior explicitly.

8. Resolve confirmed failures and regressions. Group related fixes. Check each reproduced failure and relevant neighboring behavior again; obtain targeted independent re-review when needed. Reassess the approach after an unsuccessful repair. Respect the whole-run budget and stop on repeated lack of progress.

9. Continue through necessary reversible work already authorized. Apply the user's existing approval and access boundaries. Use actual runtime controls for any claimed isolation; accurately describe limitations when those controls are unavailable.

10. Finish only when required behavior and applicable checks are satisfied and no unresolved blocker remains. Otherwise return a precise partial or blocked result. State what changed, what evidence supports it, what remains unverified and any material decisions. Retain a compact run record and clean up only owned temporary resources.

## 4. The helper's responsibilities

Put reliable mechanical checks in the helper and runtime. Keep decisions requiring judgment in the skill.

| Responsibility | Required behavior |
|---|---|
| Capability discovery | Report available isolation, model/delegation options, usage metrics and enforceable limits accurately |
| Candidate snapshot | Identify all delivered source and tests; preserve unrelated user changes; record a commit/tree or equivalent content fingerprint |
| Command evidence | Capture command, exit status, timing, candidate identity and log location without exposing credentials |
| Relevant environment | Identify dependency lock state and configured runtime/environment; do not claim perfect reproducibility from a source hash alone |
| Test changes | Flag changed assertions, additions that skip tests, collection exclusions and relevant runner configuration |
| Existing failures | Distinguish pre-existing failures from new ones; do not report a wholly green suite when exceptions exist |
| Worker isolation | Isolate source and mutable dependencies; permit only intentionally immutable sharing |
| Offline execution | Enforce restricted network/filesystem access when promised, from the first risky test onward |
| Completion gate | Refuse a success result based on missing, stale or mismatched evidence |
| Recovery | Preserve task identity, candidate, completed steps, unresolved findings and evidence locations |

If a test runner cannot supply structured collection/skip counts, record that limitation rather than inventing counts. A static test diff is a signal, not proof that coverage remains effective.

Do not rewrite the whole runtime for this revision. Repair the existing helpers first; add machinery only for a concrete guarantee or repeated need.

## 5. Review and repair policy

A finding should contain:
- the violated requirement or contract;
- the affected location;
- a reproduction or specific source evidence;
- practical impact and the minimum justified correction.

Use three outcomes: blocking defect, useful optional improvement, or observation. Match severity to impact. Do not use a finding quota.

The reviewer may challenge planner assumptions. The original request remains the reference for scope; the reviewer should not silently add product requirements.

For the initial trial, allow at most two whole repair cycles, then diagnose or return the unresolved blocker. This is a configurable starting limit, not a measured optimum. Also honor any user-specified time or spending budget. Enforce hard limits through the runtime where supported; label advisory targets honestly.

A new finding must not reset the whole-run allowance. Escalation should follow the diagnosed problem: improve missing context, fix the environment, use a more capable model, or ask about a material requirement.

## 6. Keep context and storage small

Use:
- one short core skill;
- one worker brief template, loaded only for delegation;
- one reviewer template, loaded only for independent review;
- provider-specific agent configuration;
- a small helper;
- a separate evaluation suite.

For a substantial run, keep one structured manifest and command logs. Store the original request, acceptance criteria, baseline, chosen workflow, candidate identity, evidence, material decisions and unresolved findings. Preserve those records across interruptions.

Do not make every tiny change create several plans, reports and approval steps. Do not load the benchmark history during ordinary work. Do not paste the full core skill into every worker.

## 7. Precise completion states

| Status | Meaning |
|---|---|
| Done | Required criteria met; applicable evidence belongs to the delivered candidate; no unresolved blocker |
| Partial | Useful work exists, but required behavior or verification is incomplete |
| Blocked | A concrete dependency, authorization, environment or exhausted budget prevents further justified progress |

Known unrelated failures must be disclosed. They can be accepted exceptions to a requirement only when that requirement actually permits them. A failed check must not become a passing check through a change of wording.

Manual checks remain unverified until performed. Use browser or other available tools where they can meaningfully validate the behavior, rather than assuming all UI work requires manual verification.

## 8. Implementation order

1. Fix candidate/evidence consistency and the misleading clean-room guarantee.
2. Repair test-change detection and mutable dependency sharing.
3. Introduce direct execution as the default candidate and separate execution from review routing.
4. Simplify briefs, remove reviewer pressure, and add the original request to review input.
5. Add bounded repair and a durable, compact run record.
6. Run the small comparative pilot before making model-routing or cost-saving claims.

Use the previous independent review's four helper reproductions as regression cases. Include correct changes in reviewer tests to measure false alarms.

Compare one builder, the same builder plus review, and the current hierarchy on two unseen tasks with two repeats each. Separate behavioral results from reporting quality. Measure complete task success, new regressions, confirmed findings, false alarms, total usage cost, elapsed time and user interruptions.

The design earns adoption when it completes the user's actual coding work at acceptable quality and lower total cost or time. Keep optional delegation where the results justify it.
