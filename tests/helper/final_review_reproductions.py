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
SOURCE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE.parent.parent
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
(Path(sys.argv[2]) if len(sys.argv) > 2 else Path(tempfile.gettempdir()) / "final-boundary-results.json").write_text(json.dumps(payload, indent=2) + "\n")
for item in results:
    print(item["case"] + ": " + ("REPRODUCED" if item["reproduced"] else "not reproduced"))
