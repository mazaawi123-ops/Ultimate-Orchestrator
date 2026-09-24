# Independent review of code-orchestrator, revision 77e8ff3

Reviewed 24 September 2026. Input: the supplied `code-orchestrator-review-bundle-1.md`, including the skill, helper, tests, pilot report, grader source and agent replies.

**My judgment: keep the architecture. The next version needs stronger completion checks and better evaluation, rather than more orchestration.** Direct by default, independent review when justified, and parallel work only for separable tasks is a sensible design. The current helper still permits successful completion with failed or stale evidence. I would fix those paths before describing completion as reliably enforced.

This review does not claim that any prompt, model configuration or orchestration policy is universally best. The pilot supplies useful local evidence, with important limits.

## What improved

- Direct is the default; delegation and review intensity are separate decisions.
- Reviewers receive the original request and can challenge the builder's interpretation. A review with no findings is allowed.
- Repairs have a whole-run budget; new findings do not reset it.
- The helper identifies a committed candidate, retains logs and exposes Done / Partial / Blocked.
- Ordinary copied dependency directories no longer share writable files with the main checkout.
- The documentation correctly says that a fresh checkout is not a filesystem sandbox.
- The report discloses lost reviews, incomplete runs, shared-environment changes, post-hoc checks and estimated rather than invoiced costs. Those disclosures are valuable.

I would preserve these decisions and keep this skill focused on coding. A future family of skills can share a small execution policy while retaining separate workflows for different jobs.

## What I independently checked

I extracted the supplied source into a temporary Git repository and ran its helper tests and reproduction script. I did not install the skill, edit the submitted implementation, launch paid model runs, or rerun the real-repository benchmark.

| Check | Result in this review |
|---|---|
| Supplied helper suite | 30 passed; 2 skipped because this host has no usable offline wrapper |
| Four original reproduction cases | None reproduced under the supplied script's definitions |
| Offline request on this unsupported host | Refused with exit 5 |
| Seven additional targeted hypotheses | All seven reproduced; details below |

The seven cases deliberately target suspected weaknesses. They are not a random sample or a reliability percentage. They use disposable local repositories, synthetic files and no external services. The four original cases being closed does not prove the broader guarantees complete: dependency symlinks are an example.

## Findings that should drive the next patch

### 1. Failed CI commands do not block Done

Location: `scripts/orch.sh`, `cmd_run`, `gate_problems`, `cmd_finish`.

After a passing `check`, I ran a command through `orch.sh run ci-format` that exited 2. The helper recorded it as failed and returned nonzero. Both `gate` and `finish done` nevertheless returned 0. The output explicitly contains the failed evidence beneath `GATE: PASS`.

This directly undermines the new instruction to run repository CI checks through `orch.sh run`. Adding the instruction alone did not make CI an enforced completion condition.

**Fix:** register stable required check IDs and evaluate the latest applicable result for every required check. Required missing, failed, pending or stale results must block Done. Exploratory commands need an explicit distinction or disposition, so an intentionally failing reproduction does not block a subsequently verified repair forever.

### 2. Evidence can survive a later failure or a new candidate

Location: `scripts/orch.sh`, `gate_problems`, `cmd_record`.

Two separate cases reproduced:

- With `require fresh`, a fresh run passed, a later fresh run failed, and the gate still passed. It searches for any passing fresh result rather than evaluating the current result for the required check.
- A manual check passed on commit A. I committed B and reran the automated suite, without repeating the manual check. The gate passed. Manual results are grouped by label without requiring their commit/tree to match the current candidate.

**Fix:** separate check identity from its human-readable note. Bind evidence to the candidate and relevant environment, preserve history, and apply one supersession rule consistently to tests, CI, review, manual and fresh checks. Changing the candidate should make prior evidence stale unless a documented dependency rule explicitly permits reuse.

### 3. The offline requirement can be satisfied without isolation

Location: `scripts/orch.sh`, `offline_or_die`, `cmd_fresh`, `gate_problems`.

I required offline execution, then invoked `fresh --label smoke-offline` without `--offline`. The run printed `network: NOT isolated`, yet the gate accepted it as satisfying the offline requirement. The gate infers verification from a free-form label ending in `-offline`.

There is a second issue visible in the code, separate from that integration reproduction: `offline_or_die` continues for an `unverified: ...` probe result. Later, the substring pattern `*verified*` also matches `unverified`, allowing that result to retain the apparently verified label. The test capability predicate has the same substring ambiguity.

**Fix:** store separate structured fields for the isolation method, probe outcome and scope. Accept only an exact verified outcome. An unavailable or inconclusive probe must not satisfy the requirement. Never derive enforcement status from a user-supplied label. Test the unavailable, unverified and verified paths explicitly. I did not independently validate working network isolation on this host.

### 4. Copied dependencies can still write into the main checkout

Location: `scripts/orch.sh`, `cow_copy`, `place_deps`.

The original ordinary-directory reproduction is fixed. However, copying a dependency directory preserves symlinks inside it. I placed an absolute symlink inside `node_modules` pointing to a synthetic dependency directory in the main checkout. After the default `wt-add` copy, writing through the copied dependency changed the main checkout's file. The helper still printed that writes would not reach the main tree.

**Fix:** inspect dependency links and reject or materialize links that escape the isolated dependency tree, or explicitly treat that environment as shared. Do not promise independent writes merely because `cp` succeeded. Raw copies of Python environments also deserve separate validation because launchers and editable installs can retain absolute paths; I did not run a Python-environment portability experiment here.

### 5. Candidate and environment checks have broader limits than their wording suggests

Locations: `scripts/orch.sh`, `candidate_current`, `env_fp`, `cmd_check`, `cmd_fresh`.

Two more cases reproduced:

- Committed source depended on an ignored generated Python module. The normal test suite and gate passed, but a fresh checkout failed because the module was absent. A clean Git status does not establish that tests used only delivered source and declared setup inputs.
- I changed an ignored dependency file after a passing check. The environment fingerprint stayed identical and the gate passed. Rerunning the suite then failed. The fingerprint samples interpreter versions and selected metadata files, not the actual dependency state used by execution.

**Fix:** narrow the fingerprint claim and define the supported execution environment. For the completion proof, validate a committed snapshot with a declared setup/build process and controlled dependencies. Legitimate generated files need reproducible setup, not blanket rejection of ignored files. An isolated environment identified by pinned inputs is preferable to pretending a few hashes capture every relevant runtime input.

## My interpretation of the pilot

The reported figures support Direct as a cost-conscious default on these two tasks:

| Route | Runs | Hidden-check passes | Mean estimated cost | Mean wall time |
|---|---:|---:|---:|---:|
| Direct | 4 | 4/4 | $0.82 | 2.7 min |
| Reviewed | 4 | 4/4 | $2.36 | 11.3 min |
| Previous hierarchy | 4 | 4/4 | $3.21 | 14.3 min |

These figures come from the supplied pilot records. Direct cost approximately one third of Reviewed and one quarter of the old hierarchy. That is a useful reason to avoid mandatory delegation. It does not establish equal delivered quality or prove review unnecessary on higher-risk work.

Three issues matter for interpretation:

1. **Passing hidden checks is not successful completion.** `grade_repos.py` defines `task_success` using functional, regression and safety categories. Required artifacts, reporting, completed review and a successful final gate are outside that predicate. The Reviewed schedule run whose final message merely says it is waiting still counts as successful. It also reportedly fails the pinned formatting check. Two other runs report Partial. Keep the existing results, but label them `hidden_checks_passed` and report end-to-end delivery success separately. Include all attempt costs in the cost-per-delivered-success calculation.

2. **I disagree with treating Saturday execution as merely an interpretation choice.** The original task explicitly says the weekday job should “never” run on Saturday or Sunday. An overdue Friday job executing on Saturday conflicts with that reading, even if ordinary daily jobs behave that way. The report says four of six schedule candidates do it, while the hidden grader polls every day and misses that case. I would count that behavior as a requirement defect unless the user explicitly accepts the exception. Mark a corrected retrospective score as retrospective; do not relabel it as the original held-out score. This also means the claim that Direct's outputs had none of the relevant defects is too strong.

3. **The pilot did not exercise the final submitted revision.** It used `29fe7f4`; the bundle is `77e8ff3`. The count-approval, headless-review, environment and CI changes followed the pilot. Their end-to-end behavior still needs confirmation. A source edit is an implemented fix, not yet a validated operational fix.

The evidence therefore supports “Direct is a sensible default with substantial savings on these runs,” rather than “all routes deliver the same quality.” The value of review on consequential or poorly tested changes remains an empirical question. Treat the current reviewer model/effort setting as a profile to evaluate, not a proven optimum.

## What to do next, in order

1. **Freeze the architecture while fixing the helper.** Centralize evidence eligibility and completion logic. Address required CI, stale/manual/fresh evidence, offline metadata, escaping dependency links and the candidate/environment claims. Do not add more agent roles to solve these problems.
2. **Turn the reproductions into regression tests.** Test both directions: bad evidence blocks completion, and a valid current rerun permits completion. Include deliberately exploratory failures, so repaired work is not permanently blocked by its history. Bind test-change/count approvals to the intended change and expected count movement rather than a broad reusable label.
3. **Run a small release validation on the exact resulting commit.** Exercise Direct with repository CI, Reviewed with headless reviewer completion, and an intentionally blocked case. Include the skip-count approval path. Publish final candidate, gate result, terminal status and revision. There is no need to repeat all twelve paid runs merely to check these fixes.
4. **Strengthen evaluation before expanding the benchmark.** Separate functional quality, required artifacts, CI, workflow completion, false claims of completion, cost and latency. Add the missed-Friday case and corrected oracle. Judge outputs against the original request, not only the builder's criteria.
5. **Then test review where it could matter.** Preselect representative changes with weak coverage, authorization boundaries, migrations or compatibility risk. Compare the same builder alone with that builder plus review; include repair-induced regressions and completed delivery in the scoring. Do not keep choosing tasks until Direct loses. Blinded review of the same fixed patches can first compare reviewer configurations cheaply.

The skill text is already reasonably sized. Move historical benchmark discussion and detailed troubleshooting out of the everyday instructions if they do not change a decision. Do not optimize trigger tests to penalize harmless reading of an issue file before selecting a skill. The most valuable improvement now is a trustworthy relationship between the original request, the candidate, the evidence and the completion claim.

## Implementation handoff

> Keep Direct as the default and preserve the current review/delegation architecture. Fix the demonstrated helper failures before adding orchestration features. Define required checks with stable identities; make completion depend on current applicable evidence; represent offline verification as an exact structured result; handle escaping dependency symlinks; and narrow or strengthen candidate/environment guarantees. Add the supplied cases as regressions, correct the benchmark's completion metric and missed-Friday oracle, then run a small end-to-end validation on the final commit. Report measured outcomes and remaining limits without claiming a universal optimum.

## Reproduction appendix

The following script uses the submitted test fixtures and helper. Save it outside the implementation and run:

```bash
python3 independent_checks.py /absolute/path/to/Ultimate-Orchestrator
```

It creates temporary repositories and writes `independent-results.json` beside the script. The tested source must contain `tests/helper/test_orch.py` and `code-orchestrator/scripts/orch.sh`. The result names describe review hypotheses; `REPRODUCED` means the unwanted behavior occurred on the submitted version. After a fix, some setup assertions may also need updating to express the corrected behavior.

```python
"""Local, synthetic follow-up checks of the supplied 77e8ff3 review bundle.

No model calls, package installation, credentials, or external network access.
Each case uses a disposable Git repository. This does not modify the skill.
"""
import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE / "source"
spec = importlib.util.spec_from_file_location("supplied_tests", SOURCE / "tests/helper/test_orch.py")
test = importlib.util.module_from_spec(spec)
spec.loader.exec_module(test)
Repo, APP, UNITTEST = test.Repo, test.APP, test.UNITTEST
results = []


def call(repo, *args, expect=None):
    p = repo.orch(*args)
    if expect is not None and p.returncode != expect:
        raise AssertionError((args, p.returncode, p.stdout, p.stderr))
    return {"args": list(args), "exit": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


def start(parent, name, files=None):
    r = Repo(parent / name, APP if files is None else files)
    call(r, "start", name, "--", *UNITTEST, expect=0)
    call(r, "check", "--", *UNITTEST, expect=0)
    return r


with tempfile.TemporaryDirectory(prefix="orch-independent-") as folder:
    parent = Path(folder)

    r = start(parent, "failed-ci")
    failed = call(r, "run", "ci-format", "--", "bash", "-c", "printf 'CI formatting failed\\n'; exit 2", expect=1)
    gate = call(r, "gate")
    finish = call(r, "finish", "done")
    results.append({"case": "failed_CI_does_not_block_done", "reproduced": gate["exit"] == finish["exit"] == 0,
                    "commands": [failed, gate, finish]})

    r = start(parent, "latest-fresh")
    call(r, "require", "fresh", expect=0)
    passed = call(r, "fresh", "--", *UNITTEST, expect=0)
    failed = call(r, "fresh", "--", "bash", "-c", "printf 'fresh validation failed\\n'; exit 2", expect=1)
    gate = call(r, "gate")
    results.append({"case": "earlier_fresh_pass_overrides_later_failure", "reproduced": gate["exit"] == 0,
                    "commands": [passed, failed, gate]})

    r = start(parent, "manual-stale")
    old = r.git("rev-parse", "HEAD")
    recorded = call(r, "record", "manual", "pass", "UI acceptance check", expect=0)
    r.commit("candidate changed", {"app.py": APP["app.py"] + "\n# New candidate; manual check has not been repeated.\n"})
    new = r.git("rev-parse", "HEAD")
    checked = call(r, "check", "--", *UNITTEST, expect=0)
    gate = call(r, "gate")
    results.append({"case": "manual_pass_reused_after_candidate_changes", "reproduced": old != new and gate["exit"] == 0,
                    "manual_commit": old, "current_commit": new, "commands": [recorded, checked, gate]})

    r = start(parent, "offline-label")
    call(r, "require", "offline", expect=0)
    run = call(r, "fresh", "--label", "smoke-offline", "--", *UNITTEST, expect=0)
    gate = call(r, "gate")
    results.append({"case": "offline_requirement_satisfied_by_label_only",
                    "reproduced": "network: NOT isolated" in run["stdout"] and gate["exit"] == 0,
                    "commands": [run, gate]})

    files = {**APP, ".gitignore": APP[".gitignore"] + "node_modules/\nshared-deps/\n"}
    r = start(parent, "dependency-link", files)
    r.write({"shared-deps/package/marker.txt": "main original"})
    (r.root / "node_modules").mkdir()
    (r.root / "node_modules/package").symlink_to(r.root / "shared-deps/package", target_is_directory=True)
    added = call(r, "wt-add", "review", expect=0)
    copied = r.root / ".orchestrator/worktrees/review/node_modules/package"
    link_preserved = copied.is_symlink()
    (copied / "marker.txt").write_text("changed through copied dependency")
    after = (r.root / "shared-deps/package/marker.txt").read_text()
    results.append({"case": "copied_dependency_preserves_writable_link_to_main", "reproduced": after == "changed through copied dependency",
                    "symlink_preserved": link_preserved, "main_marker_after": after, "commands": [added]})

    files = {**APP, ".gitignore": APP[".gitignore"] + "generated_settings.py\n"}
    r = start(parent, "ignored-runtime-input", files)
    r.commit("use generated settings", {"app.py": "from generated_settings import VALUE\n\ndef answer():\n    return VALUE\n"})
    r.write({"generated_settings.py": "VALUE = 41\n"})
    checked = call(r, "check", "--", *UNITTEST, expect=0)
    gate = call(r, "gate")
    fresh = call(r, "fresh", "--", *UNITTEST, expect=1)
    tracked = r.git("ls-tree", "-r", "--name-only", "HEAD").splitlines()
    results.append({"case": "ignored_runtime_input_missing_from_candidate",
                    "reproduced": gate["exit"] == 0 and "generated_settings.py" not in tracked and "ModuleNotFoundError" in fresh["stdout"],
                    "tracked_files": tracked, "commands": [checked, gate, fresh]})

    files = {**APP, ".gitignore": APP[".gitignore"] + "node_modules/\n",
             "test_dependency.py": "import unittest\nfrom pathlib import Path\nclass DependencyCheck(unittest.TestCase):\n    def test_dependency(self):\n        self.assertEqual(Path('node_modules/package/marker.txt').read_text(), 'good')\n"}
    r = Repo(parent / "dependency-fingerprint", files)
    r.write({"node_modules/package/marker.txt": "good"})
    call(r, "start", "dependency-fingerprint", "--", *UNITTEST, expect=0)
    checked = call(r, "check", "--", *UNITTEST, expect=0)
    before_fp = r.evidence()[-1][9]
    r.write({"node_modules/package/marker.txt": "bad"})
    gate = call(r, "gate")
    checked_again = call(r, "check", "--", *UNITTEST, expect=1)
    after_fp = r.evidence()[-1][9]
    results.append({"case": "changed_dependency_not_detected_by_environment_fingerprint",
                    "reproduced": gate["exit"] == 0 and before_fp == after_fp,
                    "fingerprint_before": before_fp, "fingerprint_after": after_fp,
                    "commands": [checked, gate, checked_again]})

payload = {"bundle_commit": "77e8ff3", "helper_sha256": hashlib.sha256(test.HELPER.read_bytes()).hexdigest(),
           "scope": "Synthetic local fixtures; no paid agent runs or live benchmark reruns.", "cases": results}
(HERE / "independent-results.json").write_text(json.dumps(payload, indent=2) + "\n")
for result in results:
    print(f"{result['case']}: {'REPRODUCED' if result['reproduced'] else 'not reproduced'}")
print(f"{sum(r['reproduced'] for r in results)}/{len(results)} hypotheses reproduced")
```

### Observed result summary

Helper SHA-256: `de18c27cec0d74595f329eb3b4b513581586b611344756bdd161df54412b7e6c`.

| Targeted case | Observed |
|---|---|
| failed CI does not block done | Reproduced |
| earlier fresh pass overrides later failure | Reproduced |
| manual pass reused after candidate changes | Reproduced |
| offline requirement satisfied by label only | Reproduced |
| copied dependency preserves writable link to main | Reproduced |
| ignored runtime input missing from candidate | Reproduced |
| changed dependency not detected by environment fingerprint | Reproduced |

### Failed CI reproduction: actual output

Command: `orch.sh run ci-format -- bash -c printf 'CI formatting failed\n'; exit 2`; exit 1.

```text
== run 'ci-format': exit 2, fail, 0s, counts passed/failed/skipped/ran/runner = ?/?/?/?/unknown
  | CI formatting failed
  log: .orchestrator/logs/003-ci-format.log
```

Command: `orch.sh gate`; exit 0.

```text
GATE: PASS for candidate 5e253d17f3e9cd6ddb59298525b465a6e22ab8c6
  baseline  baseline           exit=0 pass .orchestrator/logs/001-baseline.log
  check     check              exit=0 pass .orchestrator/logs/002-check.log
  run       ci-format          exit=2 fail .orchestrator/logs/003-ci-format.log
```

Command: `orch.sh finish done`; exit 0.

```text
run finished: done. Record kept: .orchestrator/manifest, .orchestrator/evidence.tsv, .orchestrator/logs/, .orchestrator/summary.md
```

