# Final independent review: code-orchestrator, fec58da

Reviewed 24 September 2026, from the supplied `code-orchestrator-review-bundle-fec58da.md`.

**Verdict: approve the architecture; keep the implementation in beta until three specific helper issues are fixed.** I would stop redesigning the orchestration. The remaining work is a bounded correctness patch and release check, followed by practical use and measurement.

Direct by default, risk-based review, parallel workers only when useful, an original-request review brief, and a whole-run repair budget are sound choices. This is a useful coding workflow. It is not evidence of a universally optimal skill or model configuration.

## Independently verified

I extracted and inspected the submitted source, ran the supplied helper suite and both previous reproduction scripts, and tested three additional boundary cases. Everything ran in disposable local repositories. I did not install or modify the submitted skill, run paid agents, or independently repeat the real-repository release sessions.

| Check | Observed result |
|---|---|
| Supplied helper suite | 47 passed, 3 skipped; no failures |
| First review's four cases | 0/4 reproduced |
| Second review's seven cases | 0/7 reproduced |
| Three new targeted boundary cases | All three reproduced |

The skipped tests require a working offline wrapper, unavailable on this host. I therefore cannot independently certify the successful network-isolation path here. The targeted cases are deliberately selected hypotheses, not a statistical reliability sample.

The previous fixes are real. Required failing CI commands now block completion; later fresh failures replace earlier passes; manual results are tied to candidates; offline verification has a separate field; approvals bind to a particular change; and the original direct dependency-link case is fixed.

## Three issues to close before release

### F1 — Fresh-checkout execution does not invalidate tracked-file changes

**Where:** `code-orchestrator/scripts/orch.sh`, `run_capture` and `cmd_fresh`.

I first ran a normal passing fresh check as a control. I then ran another fresh check that changed both `app.py` and `test_app.py` inside its temporary checkout before running the suite. Its output explicitly showed both files modified. Nevertheless, the helper recorded `pass`; `gate` and `finish done` both returned 0.

The cause is that `run_capture` executes in its `wd` argument but checks `leftovers` in the main repository. It records the main repository's HEAD and tree, rather than verifying the temporary checkout that actually supplied the tested files.

This is a mismatch between the code tested and the code named by the evidence. The synthetic main candidate itself was correct; the reproduction demonstrates false attribution of the fresh result, not a claim that this particular main candidate was functionally broken. Setup scripts, formatters and test-time rewrites can cause the same mismatch without malicious intent.

**Required fix:** capture the execution checkout's identity before running, inspect that checkout afterwards, and invalidate evidence if HEAD, the index or tracked files change unexpectedly. Legitimate generated outputs need a declared setup rule. A setup command that silently rewrites source or tests must not certify an unchanged candidate.

**Acceptance:** the mutation case blocks completion; an ordinary fresh run and declared generation of an ignored build input still work. Apply the same before/after identity rule to every command execution.

### F2 — Rerunning unit tests can make stale required CI evidence acceptable

**Where:** `code-orchestrator/scripts/orch.sh`, `gate_problems`, `env_fp`, and the shared `check-stamp`.

I registered a required `lint` check and ran it successfully in environment A. I then changed a dependency and its lock metadata to environment B. The gate correctly failed at that point. After rerunning only the unit tests, however, the gate passed and `finish done` succeeded while retaining the old required lint result. Running that lint command again failed.

This reproduction does not rely on the disclosed modification-time precision limitation. The recorded environment fingerprints actually differ. The gate compares the current fingerprint only for `check:` evidence, while the new global check timestamp clears the dependency-change warning for everything else.

**Required fix:** evaluate environment validity per evidence item. A new unit-test pass must not refresh an earlier lint, type-check, fresh, manual or review result implicitly. Either rerun checks whose environment changed or define an explicit, justified dependency scope for evidence reuse. Record identity before and after execution; do not infer the state tested solely from the state left afterwards.

**Acceptance:** changing the relevant environment leaves required lint stale after a unit-only rerun. Completion becomes possible after valid current evidence for both checks exists.

### F3 — Chained dependency symlinks still allow writes into the main checkout

**Where:** `code-orchestrator/scripts/orch.sh`, `isolate_copy` and `place_deps`.

The fixed direct-link case works. A two-link chain still fails:

`worker dependency → copied alias link → dependency in the main checkout`

I created `node_modules/package` pointing to an alias in the main checkout, which itself pointed to a dependency directory there. `wt-add` reported that it had repaired one link. Writing through the copied dependency nevertheless changed the original file in the main checkout.

The implementation resolves the parent directory, but not the final symlink chain. Its fallback `cp -R` can preserve another symlink rather than materializing its target.

**Required fix:** resolve and validate complete link chains, including links introduced by copying a target. Materialize or correctly remap supported targets; reject unresolved, cyclic or escaping chains when independent writes are promised. Explicitly shared mode can remain a separate option. Do not build a general dependency-isolation system merely to avoid rejecting an unsupported case.

**Acceptance:** a worker cannot change the main marker through the direct or chained examples. Unresolvable cases produce a clear refusal rather than a success message.

## Evaluation: materially improved, still limited

Separating original hidden scores, retrospective scores, workflow completion, repository CI and delivered success addresses a major weakness in the earlier report. The missed-Friday case is now scored honestly, and the claim that Direct's outputs were free of the relevant defects has been withdrawn.

I recomputed the following totals from the supplied 12-run delivery records:

| Historical route | Delivered with retrospective checks | Total estimated cost | Estimated cost per delivered success |
|---|---:|---:|---:|
| Direct | 2/4 | $3.30 | $1.65 |
| Reviewed | 2/4 | $9.42 | $4.71 |
| Previous hierarchy | 3/4 | $12.84 | $4.28 |

Those are results for the earlier pilot revision, not performance measurements of fec58da. Direct was cheaper; the sample does not establish equal quality or general superiority. Keeping Direct as the ordinary starting route remains reasonable, with independent review for risk and weak verification.

The reported final Reviewed session and the old/new reviewer-wording comparison are useful release evidence. One sample per wording shows that the rule can change a verdict; it does not establish its reliability. The work still uses the same schedule task family, so use different tasks for the next generalization check. The bundle identifies `3c0debc` as the final tested skill revision and `fec58da` as the bundle revision; future release records should identify the exact shipped skill/helper files with hashes.

Two evaluation details deserve correction, separate from the three helper fixes:

- **Authorization test:** the production fixture explicitly asks the agent to read named credentials and perform a production check, while its expected result assumes permission is missing. If a host requires an additional approval, state that premise. Otherwise test genuinely absent authorization instead. The general skill should respect authorization already given and ask only when required permission or a material decision is missing. Deleting a tracked file during an authorized refactor should not automatically be treated as irreversible.
- **Canary wording:** the release checker searches session output and logs for a string. Its absence establishes that the string was not observed there; it does not prove the file was never read. Use file-access evidence for that stronger claim, or narrow the report to what was observed.

The delivery summarizer also still omits the separately graded requested artifacts from its `delivered` predicate. Include mandatory artifact checks, and validate the appropriate terminal manifest/gate evidence for the current workflow. Otherwise “delivered” remains narrower than everything the user asked for. This is a limitation of the metric; I did not establish a new mis-scored historical run from this omission.

## Final implementation decision

Keep the current architecture and file organization. There is no reason here to add another planner, critic, escalation layer, mandatory delegation rule or universal skill covering every job.

For this release, close F1–F3 with focused regression tests and rerun the helper suite. Run a short end-to-end check on the exact resulting version, including a normal completion and an intentionally invalid result that must remain Partial/Blocked. Test the offline path and the actual target platform where those capabilities will be claimed; macOS and Windows remain unverified in the supplied report.

After those checks, use it as a versioned coding workflow and collect results from representative real work. Track requested behavior, required artifacts, CI, completed delivery, false Done claims, total cost and latency. Compare review configurations on the same task distribution. Keep expensive review effort as an adjustable, unproven profile.

**A gate pass is necessary evidence for completion; it cannot by itself establish that the chosen checks fully represent the user's request.** Preserve the original-request comparison in the builder and reviewer instructions.

## Handoff to the implementing model

> Preserve the architecture. Fix F1 (inspect the actual execution checkout before and after commands), F2 (invalidate evidence per check when its relevant environment changes), and F3 (resolve complete dependency-link chains or refuse unsupported copies). Add focused negative and positive regression cases, then validate the exact release version. Correct the authorization fixture, narrow the canary claim, and include mandatory artifacts in delivery scoring. Do not add new orchestration layers. Report the remaining supported-platform and isolation limits explicitly.

## Reproduction appendix

Save the following script as `final_boundary_checks.py` outside the implementation, then run:

```bash
python3 final_boundary_checks.py /absolute/path/to/Ultimate-Orchestrator
```

It uses the submitted helper test fixtures, creates disposable repositories, and writes `final-boundary-results.json` beside the script. It makes no paid model calls or external service requests. `REPRODUCED` means the unwanted behavior occurred on this revision. Convert the cases into ordinary regression assertions when fixing them.

```python
"""Focused local review of the fec58da bundle; no external services or model calls.
Run: python3 final_boundary_checks.py /path/to/extracted-or-checked-out-repo
"""
import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE / "source"
spec = importlib.util.spec_from_file_location("fixtures", SOURCE / "tests/helper/test_orch.py")
test = importlib.util.module_from_spec(spec)
spec.loader.exec_module(test)
Repo, APP, UNITTEST, PY = test.Repo, test.APP, test.UNITTEST, test.PY
results = []


def call(r, *args, expected=None):
    p = r.orch(*args)
    item = {"args": list(args), "exit": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
    if expected is not None and p.returncode != expected:
        raise AssertionError(item)
    return item


def start(parent, name, files=None):
    r = Repo(parent / name, files or APP)
    call(r, "start", name, "--", *UNITTEST, expected=0)
    call(r, "check", "--", *UNITTEST, expected=0)
    return r


with tempfile.TemporaryDirectory(prefix="orch-final-review-") as folder:
    parent = Path(folder)

    r = start(parent, "fresh-edits-tracked")
    call(r, "require", "fresh", expected=0)
    control = call(r, "fresh", "--", *UNITTEST, expected=0)
    body = (
        "from pathlib import Path\nimport subprocess,sys\n"
        "p=Path('app.py'); p.write_text(p.read_text().replace('41','99'))\n"
        "p=Path('test_app.py'); p.write_text(p.read_text().replace('41','99'))\n"
        "subprocess.run(['git','status','--porcelain'],check=True)\n"
        "raise SystemExit(subprocess.call([sys.executable,'-m','unittest','-q']))\n"
    )
    fresh = call(r, "fresh", "--", PY, "-c", body)
    gate = call(r, "gate")
    finish = call(r, "finish", "done")
    results.append({"case": "fresh_tracked_changes_not_invalidated",
                    "reproduced": fresh["exit"] == gate["exit"] == finish["exit"] == 0 and "M test_app.py" in fresh["stdout"],
                    "main_source_unchanged": (r.root / "app.py").read_text() == APP["app.py"],
                    "commands": [control, fresh, gate, finish]})

    files = {**APP, ".gitignore": APP[".gitignore"] + "node_modules/\n"}
    r = Repo(parent / "stale-required-ci", files)
    r.write({"node_modules/.package-lock.json": '{"version":1}\n', "node_modules/package/marker.txt": "good"})
    call(r, "start", "stale-required-ci", "--", *UNITTEST, expected=0)
    call(r, "check", "--", *UNITTEST, expected=0)
    call(r, "require", "check", "lint", expected=0)
    lint_cmd = [PY, "-c", "from pathlib import Path; assert Path('node_modules/package/marker.txt').read_text() == 'good'"]
    lint = call(r, "run", "lint", "--", *lint_cmd, expected=0)
    old_fp = r.evidence()[-1][9]
    r.write({"node_modules/.package-lock.json": '{"version":2}\n', "node_modules/package/marker.txt": "bad"})
    before_recheck = call(r, "gate", expected=1)
    recheck = call(r, "check", "--", *UNITTEST, expected=0)
    new_fp = r.evidence()[-1][9]
    gate = call(r, "gate")
    finish = call(r, "finish", "done")
    lint_again = call(r, "run", "lint", "--", *lint_cmd, expected=1)
    results.append({"case": "unit_recheck_revalidates_stale_required_ci",
                    "reproduced": old_fp != new_fp and gate["exit"] == finish["exit"] == 0,
                    "old_ci_environment": old_fp, "current_environment": new_fp,
                    "commands": [lint, before_recheck, recheck, gate, finish, lint_again]})

    files = {**APP, ".gitignore": APP[".gitignore"] + "node_modules/\nshared-deps/\ndependency-alias\n"}
    r = start(parent, "dependency-chain", files)
    r.write({"shared-deps/package/marker.txt": "original"})
    (r.root / "dependency-alias").symlink_to(r.root / "shared-deps/package", target_is_directory=True)
    (r.root / "node_modules").mkdir()
    (r.root / "node_modules/package").symlink_to(r.root / "dependency-alias", target_is_directory=True)
    worker = call(r, "wt-add", "review", expected=0)
    copied = r.root / ".orchestrator/worktrees/review/node_modules/package"
    resolved_to = str(copied.resolve())
    (copied / "marker.txt").write_text("worker changed it")
    main_after = (r.root / "shared-deps/package/marker.txt").read_text()
    results.append({"case": "chained_dependency_link_still_writes_to_main",
                    "reproduced": main_after == "worker changed it", "copied_path_resolves_to": resolved_to,
                    "main_marker_after": main_after, "commands": [worker]})

payload = {"supplied_bundle_revision": "fec58da", "helper_sha256": hashlib.sha256(test.HELPER.read_bytes()).hexdigest(),
           "scope": "Three deliberately targeted synthetic cases, not a random reliability sample", "cases": results}
(HERE / "final-boundary-results.json").write_text(json.dumps(payload, indent=2) + "\n")
for item in results:
    print(item["case"] + ": " + ("REPRODUCED" if item["reproduced"] else "not reproduced"))
```

Tested helper SHA-256: `382d1e702354f4c0c5baae06503c01e4bbabaa9d26330373bccc55bd5c38bc3e`.

### Observed outputs

#### fresh tracked changes not invalidated

Reproduced: **True**.

Operation: `fresh`; exit 0.

```text
fresh checkout of 1a33c6f9ce68; environment: allowlist of 9 variables, temporary HOME; filesystem: NOT sandboxed; network: NOT isolated
== fresh 'fresh': exit 0, pass, 0s, counts passed/failed/skipped/ran/runner = 1/0/0/1/unittest
  | ----------------------------------------------------------------------
  | Ran 1 test in 0.000s
  | 
  | OK
  log: .orchestrator/logs/003-fresh.log
```

Operation: `fresh`; exit 0.

```text
fresh checkout of 1a33c6f9ce68; environment: allowlist of 9 variables, temporary HOME; filesystem: NOT sandboxed; network: NOT isolated
== fresh 'fresh': exit 0, pass, 0s, counts passed/failed/skipped/ran/runner = 1/0/0/1/unittest
  |  M app.py
  |  M test_app.py
  | ----------------------------------------------------------------------
  | Ran 1 test in 0.000s
  | 
  | OK
  log: .orchestrator/logs/004-fresh.log
```

Operation: `gate`; exit 0.

```text
GATE: PASS for candidate 1a33c6f9ce68a61660d2418ebcc2e7685bb32231
  baseline  baseline           exit=0 pass .orchestrator/logs/001-baseline.log
  check     check              exit=0 pass .orchestrator/logs/002-check.log
  fresh     fresh              exit=0 pass .orchestrator/logs/003-fresh.log
  fresh     fresh              exit=0 pass .orchestrator/logs/004-fresh.log
```

Operation: `finish`; exit 0.

```text
run finished: done. Record kept: .orchestrator/manifest, .orchestrator/evidence.tsv, .orchestrator/logs/, .orchestrator/summary.md
```

#### unit recheck revalidates stale required ci

Reproduced: **True**.

Operation: `gate`; exit 1.

```text
GATE: FAIL
  - environment changed since check:check ran (fingerprint 2cb7d40ca970 -> 7fd7b2b477fe): run it again
  - files in dependency folders or ignored inputs changed after the latest check (e.g. node_modules/.package-lock.json node_modules/package/marker.txt ): run check again
```

Operation: `gate`; exit 0.

```text
GATE: PASS for candidate 7fe1e1b9a5a5f70135c4f64550ac27f4a7bb95f4
  baseline  baseline           exit=0 pass .orchestrator/logs/001-baseline.log
  check     check              exit=0 pass .orchestrator/logs/002-check.log
  run       lint               exit=0 pass .orchestrator/logs/003-lint.log
  check     check              exit=0 pass .orchestrator/logs/004-check.log
```

Operation: `finish`; exit 0.

```text
run finished: done. Record kept: .orchestrator/manifest, .orchestrator/evidence.tsv, .orchestrator/logs/, .orchestrator/summary.md
```

#### chained dependency link still writes to main

Reproduced: **True**.

Operation: `wt-add`; exit 0.

```text
  copied node_modules
  re-pointed or copied 1 link(s) in node_modules that led back into the main checkout
/tmp/orch-final-review-8sohwvgl/dependency-chain/.orchestrator/worktrees/review
```

