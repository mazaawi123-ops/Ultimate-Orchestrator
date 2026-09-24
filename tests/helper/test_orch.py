"""Regression tests for code-orchestrator/scripts/orch.sh.

Run from the repo root:  python3 -m unittest discover -s tests/helper -v
Each test builds a disposable git repo. Nothing touches the network except one loopback
listener. The first four classes are the independent review's reproductions (revision
919240501fd5), turned into checks that the flaws no longer reproduce.
"""
import http.server
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

HELPER = Path(__file__).resolve().parents[2] / "code-orchestrator" / "scripts" / "orch.sh"
PY = sys.executable


def offline_available():
    r = subprocess.run(["bash", str(HELPER), "caps"], cwd=Path(__file__).parent, capture_output=True, text=True)
    return "verified" in r.stdout


class Repo:
    def __init__(self, root: Path, files: dict):
        self.root = root
        root.mkdir(parents=True)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        self.write(files)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "baseline")

    def git(self, *args):
        r = subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr)
        return r.stdout.strip()

    def write(self, files: dict):
        for name, content in files.items():
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)

    def commit(self, msg="change", files=None):
        if files:
            self.write(files)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)

    def orch(self, *args, env=None):
        e = dict(os.environ)
        e.pop("ORCH_MAX_REPAIR_CYCLES", None)
        if env:
            e.update(env)
        return subprocess.run(["bash", str(HELPER), *args], cwd=self.root, capture_output=True, text=True, env=e, timeout=120)

    def evidence(self):
        p = self.root / ".orchestrator/evidence.tsv"
        rows = p.read_text().splitlines()[1:] if p.exists() else []
        return [r.split("\t") for r in rows]


APP = {
    ".gitignore": "__pycache__/\n",
    "app.py": "def answer():\n    return 41\n",
    "test_app.py": "import unittest\nfrom app import answer\n\n\nclass Check(unittest.TestCase):\n    def test_answer(self):\n        self.assertEqual(answer(), 41)\n",
}
UNITTEST = [PY, "-m", "unittest", "-q"]


def approve(r, path="test_app.py", reason="ruling 1: the requested behaviour changes the answer to 42"):
    """The requested change alters an existing assertion on purpose: record it as approved."""
    with open(r.root / ".orchestrator/approved-test-changes", "a") as f:
        f.write(f"{path}  {reason}\n")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="orch-test-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def started(self, files=APP, name="demo", baseline=True):
        r = Repo(self.tmp / "repo", files)
        args = ["start", name] + (["--", *UNITTEST] if baseline else [])
        res = r.orch(*args)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        return r


# ------------------------------------------------------------------ review reproductions

class ReviewA_CandidateConsistency(Base):
    def test_uncommitted_changes_cannot_pass_check(self):
        r = self.started()
        r.write({"app.py": "def answer():\n    return 42\n",
                 "test_app.py": APP["test_app.py"].replace("41", "42")})
        res = r.orch("check", "--", *UNITTEST)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("LEFTOVERS", res.stdout)
        self.assertFalse(any(row[2] == "check" for row in r.evidence()), "no evidence may be recorded without a candidate")

    def test_review_diff_refuses_a_dirty_tree_and_covers_the_candidate(self):
        r = self.started()
        r.commit("answer 42", {"app.py": "def answer():\n    return 42\n",
                               "test_app.py": APP["test_app.py"].replace("41", "42")})
        approve(r)
        self.assertEqual(r.orch("check", "--", *UNITTEST).returncode, 0)
        r.write({"app.py": "def answer():\n    return 43\n"})
        self.assertNotEqual(r.orch("diff").returncode, 0)
        r.git("checkout", "--", "app.py")
        res = r.orch("diff")
        self.assertEqual(res.returncode, 0, res.stderr)
        patch = next((r.root / ".orchestrator/review").glob("*.patch")).read_text()
        self.assertIn("+    return 42", patch)

    def test_gate_rejects_evidence_after_head_moves(self):
        r = self.started()
        r.commit("answer 42", {"app.py": "def answer():\n    return 42\n",
                               "test_app.py": APP["test_app.py"].replace("41", "42")})
        approve(r)
        self.assertEqual(r.orch("check", "--", *UNITTEST).returncode, 0)
        self.assertEqual(r.orch("gate").returncode, 0)
        r.commit("later edit", {"app.py": "def answer():\n    return 42  # edited\n"})
        res = r.orch("gate")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("HEAD moved", res.stdout)

    def test_command_that_writes_files_voids_its_evidence(self):
        r = self.started()
        res = r.orch("check", "--", "bash", "-c", "echo x > generated.txt")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("DIRTY AFTER", res.stdout)
        self.assertEqual(r.evidence()[-1][7], "dirty-after")


class ReviewB_FreshCheckoutIsHonest(Base):
    def test_git_prefixed_and_other_variables_are_not_passed(self):
        r = self.started(baseline=False)
        self.assertEqual(r.orch("candidate").returncode, 0)
        probe = "import os; print('LEAK' if os.environ.get('GIT_REVIEW_TOKEN') or os.environ.get('SOME_API_KEY') else 'CLEAN'); print('HOME', os.environ['HOME'])"
        res = r.orch("fresh", "--", PY, "-c", probe, env={"GIT_REVIEW_TOKEN": "synthetic", "SOME_API_KEY": "synthetic"})
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        log = (r.root / r.evidence()[-1][11]).read_text()
        self.assertIn("CLEAN", log)
        self.assertNotIn(str(Path.home()), log.split("HOME", 1)[1])

    def test_label_says_filesystem_and_network_are_not_sandboxed(self):
        r = self.started(baseline=False)
        r.orch("candidate")
        res = r.orch("fresh", "--", "true")
        self.assertIn("filesystem: NOT sandboxed", res.stdout)
        self.assertIn("network: NOT isolated", res.stdout)

    def test_tracked_secret_like_file_is_disclosed(self):
        files = dict(APP, **{".env": "DUMMY=not-a-secret\n"})
        r = self.started(files, baseline=False)
        r.orch("candidate")
        res = r.orch("fresh", "--", "true")
        self.assertIn(".env", res.stdout)

    @unittest.skipUnless(offline_available(), "no verified offline method on this host")
    def test_offline_blocks_a_loopback_request_that_works_without_it(self):
        hits = []

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                hits.append(1); self.send_response(200); self.end_headers(); self.wfile.write(b"ok")

            def log_message(self, *a):
                pass

        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        port = srv.server_address[1]
        try:
            r = self.started(baseline=False)
            r.orch("candidate")
            probe = f"import urllib.request; urllib.request.urlopen('http://127.0.0.1:{port}/', timeout=3)"
            online = r.orch("fresh", "--", PY, "-c", probe)
            self.assertEqual(online.returncode, 0, online.stdout)
            offline = r.orch("fresh", "--offline", "--", PY, "-c", probe)
            self.assertNotEqual(offline.returncode, 0)
            self.assertIn("verified", offline.stdout)
            self.assertEqual(len(hits), 1, "only the non-offline run may reach the server")
        finally:
            srv.shutdown(); srv.server_close()

    @unittest.skipUnless(offline_available(), "no verified offline method on this host")
    def test_check_offline_runs_the_tests_without_network(self):
        s = socket.socket(); s.bind(("127.0.0.1", 0)); s.listen(1); port = s.getsockname()[1]
        try:
            files = dict(APP, **{"test_net.py": f"import socket, unittest\n\n\nclass Net(unittest.TestCase):\n    def test_no_network(self):\n        with self.assertRaises(OSError):\n            socket.create_connection(('127.0.0.1', {port}), timeout=2)\n"})
            r = self.started(files, baseline=False)
            res = r.orch("check", "--offline", "--", *UNITTEST)
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        finally:
            s.close()


class ReviewC_WorkerDependencies(Base):
    def test_worktree_dependencies_are_copies_not_links(self):
        r = self.started(dict(APP, **{".gitignore": "__pycache__/\nnode_modules/\n"}), baseline=False)
        (r.root / "node_modules").mkdir()
        (r.root / "node_modules/marker.txt").write_text("before")
        res = r.orch("wt-add", "w1")
        self.assertEqual(res.returncode, 0, res.stderr)
        dep = r.root / ".orchestrator/worktrees/w1/node_modules"
        self.assertFalse(dep.is_symlink())
        (dep / "marker.txt").write_text("changed-by-worker")
        self.assertEqual((r.root / "node_modules/marker.txt").read_text(), "before")

    def test_link_mode_is_explicit_and_warns(self):
        r = self.started(dict(APP, **{".gitignore": "__pycache__/\nnode_modules/\n"}), baseline=False)
        (r.root / "node_modules").mkdir()
        res = r.orch("wt-add", "w2", "--deps", "link")
        self.assertIn("WARNING", res.stdout)
        self.assertTrue((r.root / ".orchestrator/worktrees/w2/node_modules").is_symlink())

    def test_wt_finish_keeps_the_report_and_cleans_up(self):
        r = self.started(baseline=False)
        wt = Path(r.orch("wt-add", "w3").stdout.strip().splitlines()[-1])
        (wt / ".orchestrator/task-report.md").write_text("done")
        subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "w3"], cwd=wt, check=True,
                       env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t"))
        r.git("merge", "-q", "--no-ff", "orch-wt/w3", "-m", "merge w3")
        res = r.orch("wt-finish", "w3")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue((r.root / ".orchestrator/reports/w3/task-report.md").exists())
        self.assertFalse(wt.exists())


class ReviewD_TestChanges(Base):
    SKIPPED = APP["test_app.py"].replace("    def test_answer", "    @unittest.skip('synthetic')\n    def test_answer")

    def test_add_only_skip_is_flagged(self):
        r = self.started()
        r.commit("skip", {"test_app.py": self.SKIPPED})
        self.assertNotEqual(r.orch("tests").returncode, 0)
        res = r.orch("check", "--", *UNITTEST)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("skip/only/xfail marker added", res.stdout)
        self.assertIn("skipped tests rose from 0 at BASE to 1", res.stdout)

    def test_skip_inside_an_existing_test_is_flagged(self):
        r = self.started()
        r.commit("skip", {"test_app.py": APP["test_app.py"].replace("        self.assertEqual", "        self.skipTest('slow')\n        self.assertEqual")})
        res = r.orch("check", "--", *UNITTEST)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("skip/only/xfail marker added", res.stdout)

    def test_approved_change_passes_with_its_reason(self):
        r = self.started()
        r.commit("skip", {"test_app.py": self.SKIPPED})
        (r.root / ".orchestrator/approved-test-changes").write_text("test_app.py  ruling 2: flaky on CI, tracked in issue 9\n")
        res = r.orch("tests")
        self.assertIn("approved", res.stdout)
        self.assertIn("ruling 2", res.stdout)

    def test_deleted_assertion_is_flagged(self):
        r = self.started()
        r.commit("loosen", {"test_app.py": APP["test_app.py"].replace("self.assertEqual(answer(), 41)", "self.assertTrue(answer())")})
        res = r.orch("tests")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("deleted or changed", res.stdout)

    TZ = "import unittest\n\n\n@unittest.skipUnless(False, 'needs pytz')\nclass TZ(unittest.TestCase):\n    def test_one(self):\n        pass\n"

    def test_skipped_count_rise_can_be_approved(self):
        # A new test inside an already-skipped class raises only the skipped count.
        r = self.started(dict(APP, **{"test_tz.py": self.TZ}))
        r.commit("tz test", {"test_tz.py": self.TZ + "\n    def test_two(self):\n        pass\n"})
        res = r.orch("check", "--", *UNITTEST)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("skipped tests rose from 1 at BASE to 2", res.stdout)
        (r.root / ".orchestrator/approved-test-changes").write_text("count:skipped  new test_two needs pytz, like test_one\n")
        res = r.orch("check", "--", *UNITTEST)
        self.assertEqual(res.returncode, 0, res.stdout)
        self.assertIn("approved  skipped tests rose from 1 at BASE to 2 (new test_two needs pytz", res.stdout)

    def test_runner_configuration_change_is_flagged(self):
        r = self.started(dict(APP, **{"setup.cfg": "[tool:pytest]\ntestpaths = .\n"}))
        r.commit("narrow discovery", {"setup.cfg": "[tool:pytest]\ntestpaths = nothing\n"})
        res = r.orch("tests")
        self.assertIn("runner or discovery configuration changed", res.stdout)

    def test_new_test_file_with_only_marker_is_flagged(self):
        r = self.started()
        r.commit("focused", {"extra.test.js": "test.only('x', () => {})\n"})
        self.assertIn("new test file contains", r.orch("tests").stdout)

    def test_adding_tests_only_is_clean(self):
        r = self.started()
        r.commit("more tests", {"test_app.py": APP["test_app.py"] + "\n    def test_type(self):\n        self.assertIsInstance(answer(), int)\n"})
        res = r.orch("check", "--", *UNITTEST)
        self.assertEqual(res.returncode, 0, res.stdout)
        self.assertIn("OK: no changes to existing tests", res.stdout)


# ------------------------------------------------------------------ other guarantees

class BaselineFailures(Base):
    FAILING = dict(APP, **{"test_old.py": "import unittest\n\n\nclass Old(unittest.TestCase):\n    def test_broken(self):\n        self.fail('pre-existing')\n"})

    def test_pre_existing_failure_is_known_not_new(self):
        r = self.started(self.FAILING)
        self.assertIn("test_broken", (r.root / ".orchestrator/baseline/failures.txt").read_text())
        r.commit("feature", {"app.py": APP["app.py"] + "\n\ndef extra():\n    return 1\n"})
        res = r.orch("check", "--", *UNITTEST)
        self.assertEqual(res.returncode, 0, res.stdout)
        self.assertEqual(r.evidence()[-1][7], "known-failures")
        self.assertIn("pre-existing failures remain", r.orch("gate").stdout)

    def test_new_failure_is_reported_as_new(self):
        r = self.started(self.FAILING)
        r.commit("break", {"app.py": "def answer():\n    return 0\n"})
        res = r.orch("check", "--", *UNITTEST)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("new failures", res.stdout)
        self.assertIn("test_answer", res.stdout)


class Lifecycle(Base):
    def test_start_refuses_uncommitted_work(self):
        r = Repo(self.tmp / "repo", APP)
        r.write({"app.py": "x = 1\n"})
        self.assertEqual(r.orch("start", "demo").returncode, 4)

    def test_unfinished_run_stops_start_and_finished_run_is_archived(self):
        r = self.started(baseline=False)
        self.assertEqual(r.orch("start", "again").returncode, 3)
        self.assertEqual(r.orch("finish", "partial", "stopped early").returncode, 0)
        r.git("checkout", "-q", "main")
        res = r.orch("start", "again")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("archived", res.stdout)
        self.assertTrue(list((r.root / ".orchestrator/runs").glob("*demo/manifest")))

    def test_finish_done_requires_the_gate(self):
        r = self.started()
        r.commit("answer 42", {"app.py": "def answer():\n    return 42\n", "test_app.py": APP["test_app.py"].replace("41", "42")})
        approve(r)
        self.assertNotEqual(r.orch("finish", "done").returncode, 0)
        self.assertEqual(r.orch("check", "--", *UNITTEST).returncode, 0)
        res = r.orch("finish", "done", "all criteria met")
        self.assertEqual(res.returncode, 0, res.stdout)
        self.assertTrue((r.root / ".orchestrator/summary.md").exists())
        self.assertTrue((r.root / ".orchestrator/evidence.tsv").exists(), "the record is kept")

    def test_required_review_blocks_until_recorded_for_this_candidate(self):
        r = self.started()
        r.orch("require", "review")
        self.assertEqual(r.orch("check", "--", *UNITTEST).returncode, 0)
        res = r.orch("gate")
        self.assertIn("review required", res.stdout)
        r.orch("record", "review", "pass", "no blocking findings")
        self.assertEqual(r.orch("gate").returncode, 0)
        r.commit("repair", {"app.py": "def answer():\n    return 41  # repaired\n"})
        r.orch("check", "--", *UNITTEST)
        self.assertIn("review required", r.orch("gate").stdout, "a review of an older candidate doesn't count")

    def test_repair_budget(self):
        r = self.started(baseline=False)
        self.assertEqual(r.orch("repair", "finding 1").returncode, 0)
        self.assertEqual(r.orch("repair", "finding 2").returncode, 0)
        res = r.orch("repair", "finding 3")
        self.assertEqual(res.returncode, 1)
        self.assertIn("REPAIR BUDGET SPENT", res.stdout)

    def test_environment_change_makes_evidence_stale(self):
        files = dict(APP, **{".gitignore": "__pycache__/\nnode_modules/\n"})
        r = self.started(files)
        (r.root / "node_modules").mkdir()
        (r.root / "node_modules/.package-lock.json").write_text('{"v":1}')
        self.assertEqual(r.orch("check", "--", *UNITTEST).returncode, 0)
        (r.root / "node_modules/.package-lock.json").write_text('{"v":2}')
        self.assertIn("environment changed", r.orch("gate").stdout)

    def test_manual_check_pending_blocks_gate(self):
        r = self.started()
        self.assertEqual(r.orch("check", "--", *UNITTEST).returncode, 0)
        r.orch("record", "manual", "pending", "layout-on-mobile")
        self.assertIn("manual check not verified", r.orch("gate").stdout)
        r.orch("record", "manual", "pass", "layout-on-mobile")
        self.assertEqual(r.orch("gate").returncode, 0)

    def test_credentials_are_masked_in_the_evidence(self):
        r = self.started(baseline=False)
        r.orch("candidate")
        r.orch("run", "echo", "--", "env", "API_TOKEN=synthetic123", "true")
        self.assertIn("API_TOKEN=***", r.evidence()[-1][12])
        self.assertNotIn("synthetic123", r.evidence()[-1][12])


class RunnerSummaries(Base):
    CASES = {
        "pytest": ("3 passed, 2 skipped in 0.12s", "3/0/2/3/pytest"),
        "pytest-fail": ("1 failed, 3 passed, 1 xfailed in 0.2s", "3/1/1/4/pytest"),
        "unittest": ("Ran 5 tests in 0.001s\n\nOK (skipped=2)", "3/0/2/5/unittest"),
        "node-test": ("# tests 4\n# pass 3\n# fail 0\n# skipped 1\n# todo 0", "3/0/1/3/tap"),
        "jest": ("Tests:       1 failed, 2 skipped, 10 passed, 13 total", "10/1/2/11/jest"),
        "cargo": ("test result: ok. 5 passed; 0 failed; 1 ignored; 0 measured", "5/0/1/5/cargo"),
        "go": ("--- PASS: TestA (0.00s)\n--- SKIP: TestB (0.00s)\n--- FAIL: TestC (0.00s)", "1/1/1/2/go"),
        "unknown": ("all good", "?/?/?/?/unknown"),
    }

    def test_counts_are_parsed_or_marked_unknown(self):
        r = self.started(baseline=False)
        r.orch("candidate")
        for name, (text, want) in self.CASES.items():
            with self.subTest(name):
                r.orch("run", name, "--", "printf", "%s\n", text)
                self.assertEqual(r.evidence()[-1][10], want)


class Stray(Base):
    def test_ignored_file_written_during_workers_is_caught(self):
        r = self.started(baseline=False)
        self.assertEqual(r.orch("stamp").returncode, 0)
        (r.root / "__pycache__").mkdir(exist_ok=True)
        (r.root / "__pycache__/stray.pyc").write_text("x")
        res = r.orch("stray")
        self.assertEqual(res.returncode, 1)
        self.assertIn("stray.pyc", res.stdout)


if __name__ == "__main__":
    unittest.main()
