"""The second independent review's seven targeted checks (docs/review/second-review.md),
verbatim apart from the default paths. REPRODUCED means the unwanted behaviour occurred.

usage: python3 tests/helper/second_review_reproductions.py [repo root] [results.json]
"""
import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE.parent.parent
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
(Path(sys.argv[2]) if len(sys.argv) > 2 else Path(tempfile.gettempdir()) / "independent-results.json").write_text(json.dumps(payload, indent=2) + "\n")
for result in results:
    print(f"{result['case']}: {'REPRODUCED' if result['reproduced'] else 'not reproduced'}")
print(f"{sum(r['reproduced'] for r in results)}/{len(results)} hypotheses reproduced")