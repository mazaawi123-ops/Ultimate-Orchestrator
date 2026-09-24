"""Summarise a pilot results directory (after grading every run with grade_repos.py).

usage: summarize.py <out dir> [--candidates]

Prints one row per run and one per arm: task success, check categories, estimated cost,
wall time, the status the run reported, dispatched agents, and review and repair activity from
the run's .orchestrator record. With --candidates, it also grades each run's first reviewed
candidate (the commit its first review covered) when that differs from the delivered tree,
to show what the review and repair changed.
"""
import json
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "graders"))
import grade_repos  # noqa: E402

TASKS = {t["name"]: t for t in json.load(open(Path(__file__).resolve().parent / "tasks.json"))["tasks"]}


def reported_status(run):
    text = (run / "outputs/final_report.md").read_text() if (run / "outputs/final_report.md").exists() else ""
    m = re.search(r"\b(Done|Partial|Blocked)\b", text)
    return m.group(1) if m else "?"


def evidence(run):
    ev = run / "outputs/orchestrator/evidence.tsv"
    if not ev.exists():
        return []
    rows = [l.split("\t") for l in ev.read_text().splitlines()[1:] if l.strip()]
    return [dict(zip(["seq", "time", "kind", "label", "commit", "tree", "exit", "status", "secs", "envfp", "counts", "log", "command"], r)) for r in rows]


def manifest(run):
    mf = run / "outputs/orchestrator/manifest"
    return dict(l.split("=", 1) for l in mf.read_text().splitlines() if "=" in l) if mf.exists() else {}


def grade_commit(run, commit, grader):
    """Grade the tree at `commit` in a scratch copy of the run's repo."""
    d = Path(tempfile.mkdtemp(prefix="pilot-candidate-"))
    try:
        shutil.copytree(run / "repo", d / "repo", symlinks=True, ignore=shutil.ignore_patterns(".orchestrator"))
        subprocess.run(["git", "-C", str(d / "repo"), "checkout", "-q", "-f", commit], check=True)
        subprocess.run(["git", "-C", str(d / "repo"), "clean", "-q", "-fdx", "-e", ".claude"], check=True)
        shutil.copy(run / "base.txt", d / "base.txt")
        (d / "outputs").mkdir()
        return grade_repos.grade(grader, str(d))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    out, with_candidates = Path(sys.argv[1]), "--candidates" in sys.argv
    rows = []
    for g in sorted(out.glob("*/*/run-*/grading.json")):
        run = g.parent
        task, config = run.parent.parent.name, run.parent.name
        grading, timing = json.load(open(g)), json.load(open(run / "timing.json"))
        ev, mf = evidence(run), manifest(run)
        reviews = [e for e in ev if e["kind"] in ("review", "recheck")]
        first_diff = next((e for e in ev if e["kind"] == "review-diff"), None)
        row = {
            "task": task, "config": config, "run": run.name,
            "task_success": grading["task_success"],
            "by_category": {k: f"{v['passed']}/{v['total']}" for k, v in grading["by_category"].items()},
            "cost": timing["cost_usd_estimate"], "wall_min": round(timing["wall_seconds"] / 60, 1),
            "reported": reported_status(run), "finish": mf.get("status", "-"),
            "dispatches": [d["agent"] for d in timing["dispatches"]],
            "reviews": [f"{e['kind']}:{e['status']}" for e in reviews],
            "repair_cycles": mf.get("repair_cycles", "-"),
        }
        if with_candidates and first_diff and first_diff["commit"] != mf.get("candidate", "").split(" ")[0]:
            cand = grade_commit(run, first_diff["commit"], TASKS[task]["grader"])
            row["first_candidate_success"] = cand["task_success"]
            row["first_candidate_failed"] = [x["text"] for x in cand["expectations"] if not x["passed"]]
        rows.append(row)
        print(json.dumps(row))
    print()
    print("| Task | Arm | Runs | Task success | Est. cost (mean, range) | Wall min (mean) | Reported | Dispatches |")
    print("|---|---|---|---|---|---|---|---|")
    for (task, config) in sorted({(r["task"], r["config"]) for r in rows}):
        rs = [r for r in rows if r["task"] == task and r["config"] == config]
        costs = [r["cost"] for r in rs]
        print(f"| {task} | {config} | {len(rs)} | {sum(r['task_success'] for r in rs)}/{len(rs)} | "
              f"${statistics.mean(costs):.2f} (${min(costs):.2f}–${max(costs):.2f}) | {statistics.mean(r['wall_min'] for r in rs):.1f} | "
              f"{', '.join(r['reported'] for r in rs)} | {'; '.join(','.join(r['dispatches']) or 'none' for r in rs)} |")
    print()
    print("| Arm | Runs | Task success | Est. cost total | Est. cost per run (mean) | Wall min (mean) |")
    print("|---|---|---|---|---|---|")
    for config in sorted({r["config"] for r in rows}):
        rs = [r for r in rows if r["config"] == config]
        print(f"| {config} | {len(rs)} | {sum(r['task_success'] for r in rs)}/{len(rs)} | ${sum(r['cost'] for r in rs):.2f} | "
              f"${statistics.mean(r['cost'] for r in rs):.2f} | {statistics.mean(r['wall_min'] for r in rs):.1f} |")
    json.dump(rows, open(out / "summary.json", "w"), indent=1)


if __name__ == "__main__":
    main()
