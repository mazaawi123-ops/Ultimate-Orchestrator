"""The independent review's four helper reproductions, run against a chosen helper.

usage: python3 tests/helper/review_reproductions.py [path/to/orch.sh]
Default: the current code-orchestrator/scripts/orch.sh. Writes JSON to stdout. Each case
reports whether the review's hypothesis still reproduces, and each property separately,
so limits that remain by design stay visible. Synthetic, local-only fixtures; one loopback
HTTP server; no real credentials or external services.
"""
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

SCRIPT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "code-orchestrator/scripts/orch.sh"
PY = sys.executable


def call(repo, *args, env=None):
    return subprocess.run(args, cwd=repo, text=True, capture_output=True, env=env, timeout=60)


def git(repo, *args):
    r = call(repo, "git", *args)
    if r.returncode:
        raise RuntimeError(r.stderr)
    return r.stdout.strip()


def init_repo(root, files):
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.name", "Review")
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


checks = []
with tempfile.TemporaryDirectory(prefix="orch-review-") as d:
    parent = Path(d)

    # A. tests and review can concern different code
    repo = parent / "dirty"
    init_repo(repo, {".gitignore": "__pycache__/\n", "app.py": "def answer():\n    return 41\n",
                     "test_app.py": "import unittest\nfrom app import answer\nclass Check(unittest.TestCase):\n    def test_answer(self):\n        self.assertEqual(answer(), 41)\n"})
    orch(repo, "start", "a")
    (repo / "app.py").write_text("def answer():\n    return 42\n")
    (repo / "test_app.py").write_text("import unittest\nfrom app import answer\nclass Check(unittest.TestCase):\n    def test_answer(self):\n        self.assertEqual(answer(), 42)\n")
    checked = orch(repo, "check", "--", PY, "-m", "unittest", "-q")
    diffed = orch(repo, "diff")
    patches = list((repo / ".orchestrator/review").glob("*.patch")) if (repo / ".orchestrator/review").exists() else []
    checks.append({"case": "dirty_check_and_empty_review_diff", "check_exit": checked.returncode,
                   "diff_exit": diffed.returncode, "review_patches_written": len(patches),
                   "reproduced": checked.returncode == 0})

    # B. clean-room is an environment check, not isolation
    hits = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            hits.append(self.path); self.send_response(200); self.end_headers(); self.wfile.write(b"synthetic-local-only")

        def log_message(self, *a):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]
    probe = (
        "import os, pathlib, urllib.request, json\n"
        "r = {}\n"
        f"try:\n    r['loopback_http'] = urllib.request.urlopen('http://127.0.0.1:{port}/probe', timeout=3).read() == b'synthetic-local-only'\n"
        "except Exception:\n    r['loopback_http'] = False\n"
        "try:\n    r['outside_file'] = pathlib.Path(os.environ.get('ORCH_REVIEW_SYNTHETIC_PATH', '/nonexistent')).read_text() == 'dummy-only'\n"
        "except Exception:\n    r['outside_file'] = False\n"
        "r['outside_file_by_absolute_path'] = pathlib.Path(os.environ.get('ABS_PATH_HINT', '/nonexistent')).exists()\n"
        "r['git_prefixed_variable'] = os.environ.get('GIT_REVIEW_TOKEN') == 'synthetic-not-a-secret'\n"
        "r['tracked_env_file'] = pathlib.Path('.env').exists()\n"
        "print('PROBE ' + json.dumps(r))\n"
    )
    repo = parent / "clean-room"
    init_repo(repo, {"probe.py": probe, ".env": "DUMMY=not-a-secret\n"})
    fake = parent / "synthetic-credential.txt"
    fake.write_text("dummy-only")
    env = dict(os.environ, ORCH_REVIEW_SYNTHETIC_PATH=str(fake), GIT_REVIEW_TOKEN="synthetic-not-a-secret")
    orch(repo, "start", "b")
    orch(repo, "candidate")
    try:
        results = {}
        for mode in ([], ["--offline"]):
            res = orch(repo, "fresh", *mode, "API_URL=http://127.0.0.1:9", f"ABS_PATH_HINT={fake}", "--", PY, "probe.py", env=env)
            log = next((l for l in (repo / ".orchestrator/logs").glob("*") if l.stat().st_mtime), None)
            logs = sorted((repo / ".orchestrator/logs").glob("*"))
            text = logs[-1].read_text() if logs else ""
            line = next((l for l in text.splitlines() if l.startswith("PROBE ")), "PROBE {}")
            results["offline" if mode else "default"] = {"exit": res.returncode, "label": res.stdout.splitlines()[0] if res.stdout else res.stderr.strip()[:200],
                                                        "reachable": json.loads(line[6:])}
    finally:
        server.shutdown(); server.server_close()
    default = results["default"]["reachable"]
    checks.append({"case": "clean_room_not_credential_or_network_isolation", "runs": results,
                   "loopback_requests_observed": len(hits),
                   "reproduced": all(default.get(k) for k in ("loopback_http", "outside_file", "git_prefixed_variable", "tracked_env_file"))})

    # C. worktree dependencies shared and writable
    repo = parent / "shared-deps"
    init_repo(repo, {".gitignore": "node_modules/\n", "app.txt": "baseline\n"})
    (repo / "node_modules").mkdir()
    (repo / "node_modules/review-marker.txt").write_text("before")
    orch(repo, "start", "c")
    orch(repo, "wt-add", "review")
    dep = repo / ".orchestrator/worktrees/review/node_modules/review-marker.txt"
    dep.write_text("changed-by-worker-fixture")
    checks.append({"case": "shared_dependency_directory", "is_symlink": dep.parent.is_symlink(),
                   "main_marker": (repo / "node_modules/review-marker.txt").read_text(),
                   "reproduced": (repo / "node_modules/review-marker.txt").read_text() == "changed-by-worker-fixture"})

    # D. an addition-only skip passes the old-test check
    repo = parent / "old-tests"
    init_repo(repo, {".gitignore": "__pycache__/\n",
                     "test_old.py": "import unittest\nclass TestOld(unittest.TestCase):\n    def test_never_passes(self):\n        self.fail('pre-existing regression check')\n"})
    orch(repo, "start", "d", "--", PY, "-m", "unittest", "-q")
    p = repo / "test_old.py"
    p.write_text(p.read_text().replace("    def test_never_passes", "    @unittest.skip('synthetic skip')\n    def test_never_passes"))
    git(repo, "add", "test_old.py"); git(repo, "commit", "-q", "-m", "add-only skip")
    old = orch(repo, "tests")
    checked = orch(repo, "check", "--", PY, "-m", "unittest", "-q")
    checks.append({"case": "add_only_test_skip", "tests_exit": old.returncode, "check_exit": checked.returncode,
                   "flags": [l.strip() for l in (old.stdout + checked.stdout).splitlines() if "FLAG" in l],
                   "reproduced": old.returncode == 0 and checked.returncode == 0})

print(json.dumps({"helper": str(SCRIPT), "checks": checks}, indent=2))
