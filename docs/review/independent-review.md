# Independent review of code-orchestrator

Date: 24 September 2026
Reviewed revision: 919240501fd5bc50b39438f15ee586a336ef133a
Scope: the uploaded review brief, the actual skill, agent definitions, helper script, plan/worker/verifier templates, measurements, installer, and published evaluation files.

**Recommendation: preserve the verification discipline, repair the helper's guarantees, and make a capable builder with optional independent review the default candidate to test. The current evidence does not establish that the orchestration hierarchy saves money.**

This is a review, not an installed replacement or a modification of the project. The model benchmark figures below are the author's reported results. I independently inspected the source and ran four local reproductions against the byte-identical helper from this revision. I did not rerun the paid Claude benchmarks or verify their original transcripts.

## 1. What the evidence supports

| Reported comparison | Observation | Defensible interpretation |
|---|---|---|
| Three real repositories: current skill with Haiku workers versus Opus alone | $11.36 versus $7.06; all 30 functional checks passed in both | The orchestrated setup cost 60.9% more on these runs. Equal measured functional results do not establish equal overall quality. |
| Same repositories, Sonnet workers | $11.43 | Changing the worker did not resolve the overhead in this small sample. It does not establish that worker choice never matters. |
| Three fixtures: current agent settings versus Opus without the skill | $8.76 versus $5.24; both 28/29 code checks | Most of the aggregate grading gain comes from process/reporting. Those outcomes matter, but should be scored separately. |
| High versus extra-high verifier configurations | $6.65 versus $8.76 total; 40/41 graded checks in each | No measured improvement on that rubric. More reported findings alone cannot establish more accurate review. |
| Repo-notes worker comparison | 11.0/13 versus 11.7/13 checks, with lower reported usage | Promising cost signal, insufficient evidence of unchanged quality. |

The correction from final context size to usage-based cost was necessary. Another distinction is still needed: Claude Code's displayed dollar totals are locally calculated estimates, not necessarily invoice charges. Subscription use is also not billed as each run's displayed API-equivalent amount. Keep the measurements, but label them precisely and state the authentication/billing mode. Official documentation: [Claude Code costs](https://code.claude.com/docs/en/costs).

The role-level cost attribution is weaker than a per-run total if it was allocated by aggregate token counts. Input, output, cache-read and cache-write tokens have different prices. If two roles use Opus, modelUsage alone does not identify how much each role cost. Use request-level usage and role identifiers, and avoid counting a child's usage again if it is already included in the session total.

The finding that a verifier repaired delegated mistakes demonstrates recovery within that workflow. It does not establish that adding those workers improved the outcome or cost relative to a stronger builder.

## 2. Four independently reproduced helper limitations

These are helper-level results. They do not show that a complete Claude run would always accept the bad state: a model reviewer could still notice it. They show that the mechanical checks do not enforce the guarantees the instructions rely on.

### A. Tests and review can concern different code — high priority

Source: [orch.sh, cmd_check]( https://github.com/mazaawi123-ops/Ultimate-Orchestrator/blob/919240501fd5bc50b39438f15ee586a336ef133a/code-orchestrator/scripts/orch.sh#L99 ) and [cmd_diff]( https://github.com/mazaawi123-ops/Ultimate-Orchestrator/blob/919240501fd5bc50b39438f15ee586a336ef133a/code-orchestrator/scripts/orch.sh#L264 ).

I changed a tracked implementation and its test without committing. The current working tree passed its test. The check command printed the uncommitted changes but returned success. The old-test check found no deleted lines, and the generated review patch was empty because it compared BASE with HEAD.

Observed: check exit 0; two modified tracked files; review diff 0 bytes.

This permits a green test result and an apparently complete review to refer to different states.

Fix:
- Define the exact candidate snapshot being delivered.
- Test and review that same snapshot, including all intended files.
- Block final verification on unexplained tracked or untracked leftovers, or deliberately include them in an immutable candidate snapshot.
- Record the candidate identifier, command, exit code and log location.
- Invalidate the evidence if source, relevant tests or environment change. Check again after verification, since test commands can write files.

### B. Clean-room is an environment check, not enforced isolation — high priority

Source: [orch.sh, cmd_clean_room]( https://github.com/mazaawi123-ops/Ultimate-Orchestrator/blob/919240501fd5bc50b39438f15ee586a336ef133a/code-orchestrator/scripts/orch.sh#L208 ).

With API_URL redirected to a closed port, a controlled test still:
- made a successful HTTP request to a separate loopback-only endpoint;
- read a synthetic file outside the repository;
- received a synthetic GIT-prefixed credential variable;
- read a tracked dummy .env file.

All values and files were synthetic; no real credentials or external services were used. This establishes that the helper itself does not enforce a network or filesystem boundary. External connectivity still depends on the host's restrictions; this test did not probe the public internet.

The helper copies tracked files, preserves most of the ambient environment and exempts all GIT-prefixed variables. A closed URL only affects code that actually uses that variable.

Fix:
- Rename this check to describe what it really validates if full isolation is not intended.
- For a guaranteed offline check, use an execution environment with restricted egress, an allowlisted environment, controlled filesystem access and no credential mounts.
- Run the risky tests there from the outset. Running the normal suite first could already trigger the action that the later check is intended to prevent.
- Treat clean-room failures as failures to investigate. Missing build artifacts, packaging mistakes and environment differences can also cause them; they do not prove a live service call or secret dependency.

### C. Worktree dependencies are shared and writable — medium priority

Source: [orch.sh, link_deps]( https://github.com/mazaawi123-ops/Ultimate-Orchestrator/blob/919240501fd5bc50b39438f15ee586a336ef133a/code-orchestrator/scripts/orch.sh#L54 ).

I created a worker worktree and changed a synthetic marker through its node_modules path. The marker in the main checkout changed because the dependency directory was a writable symbolic link.

Fix: use immutable/read-only shared dependencies, separate environments, or a documented constrained sharing model. Worktrees isolate versioned source changes; shared writable dependencies can create cross-worker interference. A timestamp check after the fact is a diagnostic, not prevention.

### D. An addition-only test skip passes the old-test check — medium priority

Source: [orch.sh, cmd_old_tests]( https://github.com/mazaawi123-ops/Ultimate-Orchestrator/blob/919240501fd5bc50b39438f15ee586a336ef133a/code-orchestrator/scripts/orch.sh#L243 ).

I added only a unittest skip decorator to an existing failing test, then committed it. No original line was deleted. Both old-tests and check returned success; the suite reported one skipped test.

Fix:
- Inspect additions as well as deletions in existing tests.
- Include test-runner configuration, discovery/exclusion rules and relevant fixtures.
- Capture unexpected changes in collected, executed and skipped tests.
- Represent approved test changes explicitly; the current deletion check can also reject legitimate changes the plan allows.
- Treat these checks as signals for review. Static diffs alone cannot prove that test strength has been preserved.

The complete reproduction and its output are included below.

## 3. Design changes I would make

| Current rule or pattern | Recommended change |
|---|---|
| Planner always delegates implementation | Let the active capable session build directly unless delegation has a concrete benefit. |
| Direct restricted mainly to one small file | Route using uncertainty, coupling, consequences and test coverage. A ten-file mechanical rename may be simpler than a one-line authorization change. Align the trigger description with this policy. |
| Full expensive verification for every Lite task | Compare a lighter review by default, and escalate for demonstrated risk. Hold reviewer model and effort constant when comparing architectures. |
| Every input without an exact example becomes a decision | Record material ambiguities. Preserve established API contracts and conventions; excessive speculation expands scope. |
| Fail loudly on all odd input unless the new request says otherwise | Preserve existing documented behavior, including deliberate coercion or tolerance. An instruction to fix one bug is not permission to make an API stricter everywhere. |
| Every new test needs a separate red/green exercise | Require a focused failing reproduction for a bug and targeted evidence for a test-gap fix. Batch related checks when that gives the same evidence. |
| Full suites run at several successive handoffs | Use targeted checks while editing and a final integrated check on the exact candidate. Reuse evidence only while its source, tests and environment remain unchanged. |
| Never finding an issue implies the reviewer is not reviewing | Remove this incentive. A clean result is valid. Require evidence for each finding, and measure false alarms as well as defects caught. |
| Three repair attempts per finding | Also impose an overall time/spend/turn budget and a no-progress stop rule. New findings otherwise restart the allowance indefinitely. |
| Repeated failure is always the brief's fault | Diagnose whether the cause is missing requirements, model capability, environment, flaky tests or a wrong proposed fix. |
| Every routine plan deviation requires a user interruption | Continue with reversible implementation adjustments within the authorized goal. Escalate material scope changes or actions needing authorization. Preserve Mo's explicit preferences on secrets and production data. |
| Delete the entire run directory at the end | Retain a compact final manifest, findings and raw evidence needed to audit or reproduce the result; clean temporary worktrees separately. |

Specific verifier changes:
- Supply the original user request verbatim, relevant repository contracts and separately labeled approved decisions, in addition to planner-derived criteria.
- Keep worker self-assessments out of the initial review.
- Let the verifier challenge criteria that omit or contradict the request.
- A fresh context gives useful separation; it does not remove shared blind spots if both roles rely on the same mistaken plan.
- Enforce read-only source access and delegation limits through the runtime where available. The agent definitions currently specify model and effort but no tool restrictions or turn limits. Prompt instructions are guidance, not an execution boundary.

Claude's current subagent documentation does support effort in agent definitions. That is not evidence that a particular historical run applied the intended setting: pin the CLI/model versions and retain the resolved configuration. Native isolation can be useful, but check its base-revision behavior before replacing the custom worktrees. [Official subagent documentation](https://code.claude.com/docs/en/sub-agents).

Keep the main skill as a short router and completion policy. Keep model settings, helper mechanics, detailed templates and historical measurements in their appropriate separate files. Avoid embedding small-sample dollar estimates as universal prices.

## 4. Architecture I would test next

**Default candidate:** one capable builder does the necessary planning and implementation, then deterministic checks run against its exact candidate. Add independent review when consequences, uncertainty or a user requirement justify it.

| Mode | Appropriate use | Shape |
|---|---|---|
| Direct | Well-specified change with effective checks | One builder plus final validation |
| Reviewed | Uncertain behavior, consequential logic, weak tests, or requested independent review | One builder plus one fresh reviewer, followed by a bounded repair and targeted re-check |
| Parallel | Substantial tasks whose dependencies and integration contracts are understood | A small number of workers, explicit integration ownership, checks on the merged candidate |

Retain a compact coordinator policy across modes, but do not require a separately active planning role in every run. If Mo chooses an Opus session, compare letting it implement against paying it to write a detailed implementation brief. A precise Haiku brief can itself become most of the implementation work.

Haiku remains a useful candidate for bounded mechanical tasks, extraction, test execution summaries or repetitive transformations. The evidence does not justify replacing every worker with Sonnet, nor does it justify eliminating all delegation.

## 5. Are the benchmarks fair?

They are useful exploratory tests, with several limits:

1. **Fixture baseline prompts force orchestration.** The published prompts explicitly request workers and independent verification. They compare the skill with an unmanaged delegated workflow. They do not establish the best direct single-session alternative. The real-repository rows use an “Opus alone” label; publish their exact prompts and traces to resolve that distinction.
2. **Process and code outcomes are combined.** A report format can earn points without changing behavior. Separate functional acceptance, regression checks, safety boundaries, evidence/reporting and review precision.
3. **Task-level sample size is small.** Several checks in the same task are correlated; 30 successful checks are not 30 independent task successes. Most configurations have one run, and the small worker A/B does not establish equivalence.
4. **Held-out evaluation is missing.** Keep the tasks used to tune descriptions and rules as development tests. Use fresh unseen tasks for subsequent claims.
5. **Effort comparisons use different generated implementations.** To compare reviewers, give them the same frozen patches, including some correct patches. Adjudicate findings without knowing the configuration.
6. **Reproducibility is incomplete in the published tree.** This revision contains fixture creation code and assertion descriptions, but I did not find the claimed real-repository graders, benchmark runner, raw usage records or full result artifacts in the recursive tree. Publish sanitized versions with pinned repository commits, exact prompts and replay instructions.
7. **A reference solution passing proves only one direction.** Also confirm that buggy variants fail. Checks that both correct and broken implementations pass do not validate the change.
8. **Access-time evidence is conditional.** An unchanged file access time alone is insufficient proof of no reads unless its behavior is validated on that filesystem and all relevant access paths. Byte-identical data establishes no detected content change, not no access.

## 6. The next experiment

First repair the snapshot and isolation claims. Then freeze the revised policies before evaluating.

A small directional pilot: **two unseen tasks × three approaches × two repeats = twelve scored runs**.

Choose one well-specified change in a mature repository and one task with real ambiguity or weak coverage. Use tasks representative of Mo's actual coding, not only tiny library exercises.

| Arm | Configuration | Question |
|---|---|---|
| A | One capable builder with the same completion requirements | What is the cost and outcome without mandated delegation? |
| B | The same builder plus one independent reviewer | What incremental value does review add? |
| C | Current planner, cheap worker and independent reviewer | Does delegated implementation justify its extra coordination and repair cost? |

Use identical task requirements, starting commits, budgets, tools and dependency environments. Do not tell A to delegate. Hold the reviewer model/effort constant between B and C. Randomize run order and preserve the original pre-review patch from every run. Where practical, branch a saved A candidate into B to measure the marginal value of review on exactly the same code; account for the shared build cost once in expenditure and include it in both comparable end-to-end route costs.

Record:
- complete task success against hidden behavioral and regression checks;
- first-pass success before reviewer-directed fixes;
- confirmed defects caught, false alarms and defects introduced during repair;
- total usage-estimated cost, actual billed cost when available, wall time and user interruptions;
- unresolved criteria and environment-blocked checks.

Use a task-level success measure, not the number of reviewer findings. For a cost-per-success metric, include the cost of failed attempts in the numerator. Twelve runs can reject an obviously wasteful design or guide the next iteration; they cannot establish universal superiority.

If B matches C's observed outcomes at lower cost, simplify the default and reserve C for workloads where it earns its overhead. If A performs as well as B on low-risk work, make review conditional there. Compare Sonnet versus Opus as the builder, and high versus extra-high review, only after the topology decision; otherwise several factors change at once.

## 7. Concrete handoff to Claude

Keep the existing project as the comparison baseline. Create a candidate revision that:
1. ties testing, review and reporting to the exact same candidate snapshot;
2. accurately labels the environment check and uses real isolation where it promises isolation;
3. detects or explicitly approves skipped/weakened existing tests;
4. prevents writes through shared dependency directories;
5. removes pressure on reviewers to find issues and gives them the original request;
6. routes directly by default when delegation has no demonstrated benefit;
7. caps the whole repair process and preserves a compact evidence record;
8. includes a reproducible runner and held-out evaluation before making new cost-saving claims.

Success is a correctly completed user task at an acceptable total cost. A role earns its place when it improves that outcome on the workloads you actually do.

## Sources and verification scope

- [Reviewed pull request](https://github.com/mazaawi123-ops/Ultimate-Orchestrator/pull/1)
- [Skill at reviewed revision](https://github.com/mazaawi123-ops/Ultimate-Orchestrator/blob/919240501fd5bc50b39438f15ee586a336ef133a/code-orchestrator/SKILL.md)
- [Helper at reviewed revision](https://github.com/mazaawi123-ops/Ultimate-Orchestrator/blob/919240501fd5bc50b39438f15ee586a336ef133a/code-orchestrator/scripts/orch.sh)
- [Verifier template](https://github.com/mazaawi123-ops/Ultimate-Orchestrator/blob/919240501fd5bc50b39438f15ee586a336ef133a/code-orchestrator/references/verifier-brief.md)
- [Reported measurements](https://github.com/mazaawi123-ops/Ultimate-Orchestrator/blob/919240501fd5bc50b39438f15ee586a336ef133a/code-orchestrator/references/example-run.md)
- [Published eval prompts and assertions](https://github.com/mazaawi123-ops/Ultimate-Orchestrator/blob/919240501fd5bc50b39438f15ee586a336ef133a/evals/evals.json)
- [Recursive reviewed tree](https://api.github.com/repos/mazaawi123-ops/Ultimate-Orchestrator/git/trees/919240501fd5bc50b39438f15ee586a336ef133a?recursive=1)
- [Claude Code cost reporting](https://code.claude.com/docs/en/costs)
- [Claude Code subagent configuration](https://code.claude.com/docs/en/sub-agents)

Original helper Git blob: cd06c14e54887f98ab922a1fa5ca30bca5ce3c08.
SHA-256 of the locally tested helper: 8219a0e111f33f7e0ae390a2206bdd18c6ee9db7b10dac75e693a2d7ca5f192f.

Local checks ran on Linux using disposable Git repositories and standard Python libraries. They do not validate macOS, Windows, Claude's permission layer or the end-to-end model benchmark. No repository changes were published.

## Appendix: reproduce the four helper observations

Save the following Python block as reproduce.py in a disposable directory. Place the exact pinned helper beside it as orch-original.sh, and verify the SHA-256 above. Run python3 reproduce.py. It makes disposable fixtures, serves one loopback-only HTTP request, and writes reproduction-results.json. Only execute the supplied revision that has been reviewed.


```python
"""Bounded, offline reproductions against an unchanged orch.sh snapshot."""
import hashlib
import http.server
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading

SCRIPT = Path(__file__).with_name("orch-original.sh")
OUT = Path(__file__).parent
checks = []

def call(repo, *args, env=None):
    return subprocess.run(args, cwd=repo, text=True, capture_output=True, env=env, timeout=20)

def git(repo, *args):
    r = call(repo, "git", *args)
    if r.returncode:
        raise RuntimeError(r.stderr)
    return r.stdout.strip()

def init_repo(root, files):
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.name", "Orchestrator Review")
    git(root, "config", "user.email", "review@example.invalid")
    for name, content in files.items():
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "synthetic baseline")
    return git(root, "rev-parse", "HEAD")

def orch(root, *args, env=None):
    return call(root, "bash", str(SCRIPT), *args, env=env)

with tempfile.TemporaryDirectory(prefix="orch-review-", dir=OUT) as directory:
    parent = Path(directory)
    repo = parent / "dirty"
    base = init_repo(repo, {
        ".gitignore": ".orchestrator/\n__pycache__/\n",
        "app.py": "def answer():\n    return 41\n",
        "test_app.py": "import unittest\nfrom app import answer\nclass Check(unittest.TestCase):\n    def test_answer(self):\n        self.assertEqual(answer(), 41)\n"
    })
    (repo / "app.py").write_text("def answer():\n    return 42\n")
    (repo / "test_app.py").write_text(
        "import unittest\nfrom app import answer\nclass Check(unittest.TestCase):\n    def test_answer(self):\n        self.assertEqual(answer(), 42)\n")
    checked = orch(repo, "check", base, "test_app.py", "--", "python3", "-m", "unittest", "-q")
    diffed = orch(repo, "diff", base, "1")
    checks.append({
        "case": "dirty_check_and_empty_review_diff",
        "check_exit": checked.returncode,
        "check_output": checked.stdout,
        "diff_exit": diffed.returncode,
        "review_diff_bytes": (repo / ".orchestrator/diff-1.patch").stat().st_size,
        "reproduced": checked.returncode == 0 and (repo / ".orchestrator/diff-1.patch").stat().st_size == 0
    })

    repo = parent / "clean-room"
    hits = []
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            hits.append(self.path)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"synthetic-local-only")
        def log_message(self, *args):
            pass
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    probe = (
        "import os, pathlib, urllib.request\n"
        f"assert urllib.request.urlopen('http://127.0.0.1:{port}/probe', timeout=3).read() == b'synthetic-local-only'\n"
        "assert pathlib.Path(os.environ['ORCH_REVIEW_SYNTHETIC_PATH']).read_text() == 'dummy-only'\n"
        "assert os.environ.get('GIT_REVIEW_TOKEN') == 'synthetic-not-a-secret'\n"
        "assert pathlib.Path('.env').read_text() == 'DUMMY=not-a-secret\\n'\n"
        "print('Local network, synthetic outside file, GIT-prefixed dummy env, tracked dummy .env: reachable')\n"
    )
    base = init_repo(repo, {".gitignore": ".orchestrator/\n", "probe.py": probe, ".env": "DUMMY=not-a-secret\n"})
    fake = parent / "synthetic-credential.txt"
    fake.write_text("dummy-only")
    review_env = dict(os.environ)
    review_env["ORCH_REVIEW_SYNTHETIC_PATH"] = str(fake)
    review_env["GIT_REVIEW_TOKEN"] = "synthetic-not-a-secret"
    try:
        result = orch(repo, "clean-room", "API_URL=http://127.0.0.1:9", "--", "python3", "probe.py", env=review_env)
    finally:
        server.shutdown()
        server.server_close()
    checks.append({
        "case": "clean_room_not_credential_or_network_isolation",
        "exit": result.returncode,
        "output": result.stdout,
        "error": result.stderr,
        "local_requests_observed": len(hits),
        "reproduced": result.returncode == 0 and len(hits) == 1
    })

    repo = parent / "shared-deps"
    base = init_repo(repo, {".gitignore": ".orchestrator/\nnode_modules/\n", "app.txt": "baseline\n"})
    (repo / "node_modules").mkdir()
    (repo / "node_modules/review-marker.txt").write_text("before")
    worker = orch(repo, "wt-add", "review")
    if worker.returncode:
        raise RuntimeError(worker.stderr)
    dependency = repo / ".orchestrator/worktrees/review/node_modules/review-marker.txt"
    dependency.write_text("changed-by-worker-fixture")
    checks.append({
        "case": "shared_dependency_directory",
        "is_symlink": dependency.parent.is_symlink(),
        "main_marker": (repo / "node_modules/review-marker.txt").read_text(),
        "reproduced": (repo / "node_modules/review-marker.txt").read_text() == "changed-by-worker-fixture"
    })

    repo = parent / "old-tests"
    base = init_repo(repo, {
        ".gitignore": ".orchestrator/\n__pycache__/\n",
        "test_old.py": "import unittest\nclass TestOld(unittest.TestCase):\n    def test_never_passes(self):\n        self.fail('pre-existing regression check')\n"
    })
    p = repo / "test_old.py"
    p.write_text(p.read_text().replace("    def test_never_passes", "    @unittest.skip('synthetic skip')\n    def test_never_passes"))
    git(repo, "add", "test_old.py")
    git(repo, "commit", "-q", "-m", "add-only skip")
    old = orch(repo, "old-tests", base, "test_old.py")
    checked = orch(repo, "check", base, "test_old.py", "--", "python3", "-m", "unittest", "-q")
    checks.append({
        "case": "add_only_test_skip",
        "old_tests_exit": old.returncode,
        "check_exit": checked.returncode,
        "output": checked.stdout,
        "reproduced": old.returncode == 0 and checked.returncode == 0
    })

report = {
    "source_commit": "919240501fd5bc50b39438f15ee586a336ef133a",
    "helper_sha256": hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
    "scope": "Synthetic local fixtures; one loopback HTTP request; no real credentials or external services; no model benchmark rerun.",
    "checks": checks
}
(OUT / "reproduction-results.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
if not all(c["reproduced"] for c in checks):
    raise SystemExit("At least one hypothesis was not reproduced; inspect evidence.")
```

## Observed output

```json
{
  "source_commit": "919240501fd5bc50b39438f15ee586a336ef133a",
  "helper_sha256": "8219a0e111f33f7e0ae390a2206bdd18c6ee9db7b10dac75e693a2d7ca5f192f",
  "scope": "Synthetic local fixtures; one loopback HTTP request; no real credentials or external services; no model benchmark rerun.",
  "checks": [
    {
      "case": "dirty_check_and_empty_review_diff",
      "check_exit": 0,
      "check_output": "== tests: python3 -m unittest -q\n----------------------------------------------------------------------\nRan 1 test in 0.000s\n\nOK\nexit 0\n== uncommitted:  M app.py\n M test_app.py\n== commits since BASE:\n== old tests:\nOK: no lines deleted from tests that existed at BASE\n",
      "diff_exit": 0,
      "review_diff_bytes": 0,
      "reproduced": true
    },
    {
      "case": "clean_room_not_credential_or_network_isolation",
      "exit": 0,
      "output": "clean room: /tmp/orch-clean.XYVK7Q/repo (HEAD 297fbd4), with API_URL=http://127.0.0.1:9; 1 credential-like variable(s) unset\nLocal network, synthetic outside file, GIT-prefixed dummy env, tracked dummy .env: reachable\nclean room: exit 0\n",
      "error": "",
      "local_requests_observed": 1,
      "reproduced": true
    },
    {
      "case": "shared_dependency_directory",
      "is_symlink": true,
      "main_marker": "changed-by-worker-fixture",
      "reproduced": true
    },
    {
      "case": "add_only_test_skip",
      "old_tests_exit": 0,
      "check_exit": 0,
      "output": "== tests: python3 -m unittest -q\n----------------------------------------------------------------------\nRan 1 test in 0.000s\n\nOK (skipped=1)\nexit 0\n== uncommitted: none\n== commits since BASE:\n78e16e9 add-only skip\n test_old.py | 1 +\n 1 file changed, 1 insertion(+)\n== old tests:\nOK: no lines deleted from tests that existed at BASE\n",
      "reproduced": true
    }
  ]
}
```
