"""Summarise a pilot results directory, after grading every run with grade_repos.py and
probing it with ci_probes.py.

usage: summarize.py <out dir> [--candidates]

Each measure is reported separately, so none can hide another:
  hidden_checks_passed     the functional, regression and safety checks fixed before the runs
  ..._retrospective        the same plus checks written after the runs were seen (reported apart)
  workflow_completed       the run finished Done; for the current skill, through its own gate
  ci_clean                 the repo's own CI checks pass (post-hoc probes)
  delivered                all three: what a user would get and could merge
  false_completion_claim   the run said Done while a hidden check or a CI check fails
Cost per delivered success keeps every attempt's cost in the numerator.
With --candidates it also grades the code each run's first review saw.
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
CI_KEYS = ("ruff_format", "ruff_check", "stubtest", "black_20_8b1", "no_new_mypy_errors")


def reported_status(run):
    text = (run / "outputs/final_report.md").read_text() if (run / "outputs/final_report.md").exists() else ""
    m = re.search(r"\b(Done|Partial|Blocked)\b", text, re.I)
    return m.group(1).capitalize() if m else "none"


def evidence(run):
    ev = run / "outputs/orchestrator/evidence.tsv"
    if not ev.exists():
        return []
    rows = [l.split("\t") for l in ev.read_text().splitlines()[1:] if l.strip()]
    return [dict(zip(["seq", "time", "kind", "label", "commit", "tree", "exit", "status", "secs", "envfp", "counts", "log", "command"], r)) for r in rows]


def manifest(run):
    mf = run / "outputs/orchestrator/manifest"
    return dict(l.split("=", 1) for l in mf.read_text().splitlines() if "=" in l) if mf.exists() else {}


def grade_commit(run, commit, grader, patch=None):
    """Grade the tree at `commit` (plus `patch`, if given) in a scratch copy of the run's repo."""
    d = Path(tempfile.mkdtemp(prefix="pilot-candidate-"))
    try:
        shutil.copytree(run / "repo", d / "repo", symlinks=True, ignore=shutil.ignore_patterns(".orchestrator"))
        git = ["git", "-C", str(d / "repo")]
        subprocess.run(git + ["checkout", "-q", "-f", commit], check=True)
        subprocess.run(git + ["clean", "-q", "-fdx", "-e", ".claude"], check=True)
        if patch:
            subprocess.run(git + ["apply", "--whitespace=nowarn", str(patch)], check=True)
        shutil.copy(run / "base.txt", d / "base.txt")
        (d / "outputs").mkdir()
        return grade_repos.grade(grader, str(d))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def first_candidate(run, ev, mf):
    """The code the first review saw, as (commit, patch), or None when it's the delivered code.
    Current skill: the commit of the first review-diff row. Previous skill: BASE + diff-1.patch."""
    first_diff = next((e for e in ev if e["kind"] == "review-diff"), None)
    if first_diff:
        return None if first_diff["commit"] == mf.get("candidate") else (first_diff["commit"], None)
    old = run / "outputs/orchestrator/diff-1.patch"
    if old.exists():
        return ((run / "base.txt").read_text().strip(), old)
    return None


def main():
    out, with_candidates = Path(sys.argv[1]), "--candidates" in sys.argv
    rows = []
    for g in sorted(out.glob("*/*/run-*/grading.json")):
        run = g.parent
        task, config = run.parent.parent.name, run.parent.name
        grading, timing = json.load(open(g)), json.load(open(run / "timing.json"))
        probes = json.load(open(run / "probes.json")) if (run / "probes.json").exists() else {}
        ev, mf = evidence(run), manifest(run)
        reported, finish = reported_status(run), mf.get("status", "-")
        # The previous skill has no gate or manifest: its own "Done" is all there is.
        completed = reported == "Done" and finish in ("done", "-")
        ci = [probes[k] for k in CI_KEYS if k in probes]
        ci_clean = bool(ci) and all(ci)
        hidden = grading["hidden_checks_passed"]
        retro = grading.get("hidden_checks_passed_retrospective", hidden)
        row = {
            "task": task, "config": config, "run": run.name,
            "hidden_checks_passed": hidden, "hidden_checks_passed_retrospective": retro,
            "by_category": {k: f"{v['passed']}/{v['total']}" for k, v in grading["by_category"].items()},
            "reported": reported, "finish": finish, "workflow_completed": completed, "ci_clean": ci_clean,
            "delivered": hidden and completed and ci_clean, "delivered_retrospective": retro and completed and ci_clean,
            "false_completion_claim": reported == "Done" and not (hidden and ci_clean),
            "false_completion_claim_retrospective": reported == "Done" and not (retro and ci_clean),
            "cost": timing["cost_usd_estimate"], "wall_min": round(timing["wall_seconds"] / 60, 1),
            "dispatches": [d["agent"] for d in timing["dispatches"]],
            "reviews": [f"{e['kind']}:{e['status']}" for e in ev if e["kind"] in ("review", "recheck")],
            "repair_cycles": mf.get("repair_cycles", "-"), "probes": probes,
        }
        fc = first_candidate(run, ev, mf) if with_candidates else None
        if fc:
            try:
                cand = grade_commit(run, fc[0], TASKS[task]["grader"], fc[1])
                row["first_candidate_hidden_checks_passed"] = cand["hidden_checks_passed"]
                row["first_candidate_failed"] = [x["text"] for x in cand["expectations"] if not x["passed"]]
            except subprocess.CalledProcessError as e:
                row["first_candidate_hidden_checks_passed"] = f"not reconstructable: {e}"
        rows.append(row)
        print(json.dumps(row))

    def frac(rs, k):
        return f"{sum(bool(r[k]) for r in rs)}/{len(rs)}"

    def per(rs, k):
        n = sum(bool(r[k]) for r in rs)
        return f"${sum(r['cost'] for r in rs) / n:.2f}" if n else "n/a"

    print()
    print("| Arm | Runs | Hidden checks | + retrospective | Workflow completed | Repo CI clean | Delivered | Delivered (retro.) | False Done claims (retro.) | Est. cost total | Per delivered | Per delivered (retro.) | Mean wall |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for config in sorted({r["config"] for r in rows}):
        rs = [r for r in rows if r["config"] == config]
        print(f"| {config} | {len(rs)} | {frac(rs, 'hidden_checks_passed')} | {frac(rs, 'hidden_checks_passed_retrospective')} | "
              f"{frac(rs, 'workflow_completed')} | {frac(rs, 'ci_clean')} | {frac(rs, 'delivered')} | {frac(rs, 'delivered_retrospective')} | "
              f"{frac(rs, 'false_completion_claim')} ({frac(rs, 'false_completion_claim_retrospective')}) | "
              f"${sum(r['cost'] for r in rs):.2f} | {per(rs, 'delivered')} | {per(rs, 'delivered_retrospective')} | "
              f"{statistics.mean(r['wall_min'] for r in rs):.1f} |")
    print()
    print("| Task | Arm | Run | Hidden | Retro. | Reported | Helper status | CI clean | Delivered | Est. cost | Wall min |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['task']} | {r['config']} | {r['run']} | {r['hidden_checks_passed']} | {r['hidden_checks_passed_retrospective']} | "
              f"{r['reported']} | {r['finish']} | {r['ci_clean']} | {r['delivered']} | ${r['cost']:.2f} | {r['wall_min']} |")
    json.dump(rows, open(out / "summary.json", "w"), indent=1)


if __name__ == "__main__":
    main()
