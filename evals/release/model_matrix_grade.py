"""Grade a model_matrix.sh results directory: one row per role x model, with an objective
score for the role's task and the session's estimated cost, turns and wall time.

usage: model_matrix_grade.py <out dir> --schedule-repo <clean schedule clone at BASE>
                             [--black <black 20.8b1>] [--mypy-python <python with mypy>]

Scores (0-1):
  reviewer    verdict FAIL (0.4), the missed-Friday/weekend case rated blocking (0.4), the
              daylight-saving edge found (0.1), tree untouched (0.1). Read the replies too:
              this can't tell a supported finding from an invented one.
  worker      fraction of the windowed(strict=) hidden checks passed (grade_repos), and
              whether every core check passed
  mechanical  fraction of: committed and clean; only the two files changed; old name gone;
              new name at all 19 sites; pytest 40 passed/41 skipped; mypy clean; black clean
  researcher  mean F1 over the four questions against computed ground truth, tree untouched
Writes <out dir>/summary.json and each cell's reply.md; prints a Markdown table.
"""
import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "graders"))
import grade_repos  # noqa: E402

OLD, NEW, NEW_SITES = "_move_to_next_weekday", "_advance_to_weekday", 8  # git grep -o at BASE


def sh(cmd, cwd, timeout=900):
    p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout + p.stderr


def stream_summary(cell):
    res, models, turns = None, {}, 0
    for line in (cell / "stream.jsonl").read_text(errors="replace").splitlines():
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("type") == "assistant":
            turns += 1
        if e.get("type") == "result":
            res = e
    if not res:
        return {"cost": None, "turns": turns, "subtype": "no result", "reply": ""}
    for m, u in (res.get("modelUsage") or {}).items():
        models[m] = {k: u.get(k) for k in ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens", "costUSD")}
    return {"cost": res.get("total_cost_usd"), "turns": res.get("num_turns", turns), "subtype": res.get("subtype"),
            "reply": res.get("result") or "", "models": models, "duration_ms": res.get("duration_ms")}


def tree_clean(repo, base):
    rc, out = sh("git status --porcelain", repo)
    rc2, diff = sh(f"git diff --stat {base} HEAD", repo)
    return out.strip() == "" and diff.strip() == ""


def grade_reviewer(cell, reply):
    base = (cell / "base.txt").read_text().strip()
    verdict = re.search(r"Verdict:\s*\**\s*(PASS|FAIL)", reply, re.I)
    verdict = verdict.group(1).upper() if verdict else "none"
    # A blocking finding whose text names the weekend/late-run case.
    blocking = False
    for m in re.finditer(r"blocking", reply, re.I):
        window = reply[m.start(): m.start() + 900]
        if re.search(r"Saturday|Sunday|weekend|missed Friday|late run|overdue", window, re.I):
            blocking = True
            break
    dst = bool(re.search(r"DST|daylight|gap hour|spring[- ]forward", reply, re.I))
    clean = tree_clean(cell / "repo", "HEAD") and not sh("git status --porcelain", cell / "repo")[1].strip()
    score = 0.4 * (verdict == "FAIL") + 0.4 * blocking + 0.1 * dst + 0.1 * clean
    return round(score, 2), {"verdict": verdict, "missed_friday_blocking": blocking, "dst_edge_found": dst, "tree_untouched": clean}


def grade_worker(cell, reply):
    (cell / "outputs").mkdir(exist_ok=True)
    (cell / "outputs/final_report.md").write_text(reply)
    g = grade_repos.grade("windowed_strict", str(cell))
    exp = g["expectations"]
    passed = sum(x["passed"] for x in exp)
    core = all(x["passed"] for x in exp if x["category"] in ("functional", "regression", "safety"))
    committed = sh("git status --porcelain", cell / "repo")[1].strip() == ""
    return round(passed / len(exp), 2), {"checks": f"{passed}/{len(exp)}", "core_all_passed": core, "committed_clean": committed,
                                        "failed": [x["text"] for x in exp if not x["passed"]]}


def grade_mechanical(cell, reply, black, mypy_python):
    repo, base = cell / "repo", (cell / "base.txt").read_text().strip()
    checks = {}
    checks["committed_clean"] = sh("git status --porcelain", repo)[1].strip() == ""
    _, files = sh(f"git diff --name-only {base} HEAD", repo)
    checks["only_two_files"] = set(files.split()) == {"schedule/__init__.py", "test_schedule.py"}
    _, old = sh(f"git grep -c {OLD} HEAD -- . | cat", repo)
    checks["old_name_gone"] = old.strip() == ""
    _, new = sh(f"git grep -o {NEW} HEAD -- . | wc -l", repo)
    checks["new_name_at_all_sites"] = new.strip() == str(NEW_SITES)
    _, t = sh("python3 -m pytest -q -p no:cacheprovider", repo)
    checks["tests_unchanged_result"] = "40 passed, 41 skipped" in t
    if mypy_python:
        checks["mypy_clean"] = sh(f"{mypy_python} -m mypy -p schedule", repo)[0] == 0
    if black:
        checks["black_clean"] = sh(f"{black} --check .", repo)[0] == 0
    return round(sum(checks.values()) / len(checks), 2), checks


def researcher_truth(schedule_repo):
    src = subprocess.run(["git", "-C", str(schedule_repo), "show", "HEAD:schedule/__init__.py"], capture_output=True, text=True).stdout
    tree = ast.parse(src)

    def calls_in(node):
        out = set()
        for n in ast.walk(node):
            if isinstance(n, ast.Call):
                f = n.func
                out.add(f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", ""))
        return out
    callers, callees, setters = set(), set(), set()
    for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
        for fn in [n for n in cls.body if isinstance(n, ast.FunctionDef)]:
            if fn.name == "_schedule_next_run":
                callees = calls_in(fn)
            elif "_schedule_next_run" in calls_in(fn):
                callers.add(f"{cls.name}.{fn.name}")
            if cls.name == "Job" and any(isinstance(n, ast.Assign) and any(isinstance(t, ast.Attribute) and t.attr == "unit"
                                                                       and isinstance(t.value, ast.Name) and t.value.id == "self" for t in n.targets)
                                         for n in ast.walk(fn)):
                setters.add(fn.name)
    _, out = sh("python3 -m pytest -v -p no:cacheprovider test_schedule.py", schedule_repo)
    skipped = {m.group(1) for m in re.finditer(r"::(test_\w+)\s+SKIPPED", out)}
    return {"callers": callers, "callees": callees, "unit_setters": setters, "pytz_skipped_tests": skipped}


def norm(name):
    name = str(name).strip().strip("`").split("(")[0]
    return name.split(".")[-1]


def grade_researcher(cell, reply, truth):
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", reply, re.S)
    answer = None
    for b in reversed(blocks):
        try:
            answer = json.loads(b)
            break
        except Exception:
            continue
    details = {"parsed": answer is not None, "tree_untouched": sh("git status --porcelain", cell / "repo")[1].strip() == ""}
    if answer is None:
        return 0.0, details
    f1s = []
    for k, want in truth.items():
        got = {norm(x) for x in (answer.get(k) or [])}
        want_n = {norm(x) for x in want}
        tp = len(got & want_n)
        p = tp / len(got) if got else 0.0
        r = tp / len(want_n) if want_n else 0.0
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        f1s.append(f1)
        details[k] = {"f1": round(f1, 2), "missed": sorted(want_n - got), "extra": sorted(got - want_n)}
    score = sum(f1s) / len(f1s) * (1.0 if details["tree_untouched"] else 0.9)
    return round(score, 2), details


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--schedule-repo", required=True)
    ap.add_argument("--black")
    ap.add_argument("--mypy-python")
    a = ap.parse_args()
    out = Path(a.out)
    truth = researcher_truth(Path(a.schedule_repo))
    rows = []
    for cell in sorted(out.glob("*/*/stream.jsonl")):
        cell = cell.parent
        role, model = cell.parent.name, cell.name
        s = stream_summary(cell)
        (cell / "reply.md").write_text(s["reply"])
        if role == "reviewer":
            score, det = grade_reviewer(cell, s["reply"])
        elif role == "worker":
            score, det = grade_worker(cell, s["reply"])
        elif role == "mechanical":
            score, det = grade_mechanical(cell, s["reply"], a.black, a.mypy_python)
        else:
            score, det = grade_researcher(cell, s["reply"], truth)
        row = {"role": role, "model": model, "score": score, "details": det, "cost": s["cost"], "turns": s["turns"],
               "subtype": s["subtype"], "wall_seconds": int((cell / "wall_seconds").read_text()) if (cell / "wall_seconds").exists() else None,
               "models": s.get("models", {})}
        rows.append(row)
        print(json.dumps(row))
    json.dump({"truth": {k: sorted(v) for k, v in truth.items()}, "rows": rows}, open(out / "summary.json", "w"), indent=1)
    print()
    print("| Role | Model | Score | Est. cost | Turns | Wall | Result |")
    print("|---|---|---|---|---|---|---|")
    order = {"haiku": 0, "sonnet": 1, "opus": 2, "fable": 3}
    for r in sorted(rows, key=lambda r: (r["role"], order.get(r["model"], 9))):
        cost = f"${r['cost']:.2f}" if r["cost"] is not None else "-"
        wall = f"{r['wall_seconds'] / 60:.1f} min" if r["wall_seconds"] else "-"
        print(f"| {r['role']} | {r['model']} | {r['score']} | {cost} | {r['turns']} | {wall} | {r['subtype']} |")


if __name__ == "__main__":
    main()
