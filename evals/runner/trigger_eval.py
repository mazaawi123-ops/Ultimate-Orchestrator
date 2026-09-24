"""Does the skill load when it should, and stay out when it shouldn't?

usage: trigger_eval.py --skill DIR --evals FILE [--runs 3] [--model sonnet] [--out FILE]

Installs the skill as a project skill in an empty git repo, then runs each query with
`claude -p`. A run counts as triggered when the session loads code-orchestrator within its
first 3 tool calls and before any file edit (Edit, Write, NotebookEdit), so reading an issue
file first isn't penalised. --strict counts only a first-call load (the metric used before).
A query passes when most of its runs match its should_trigger label.
"""
import argparse
import concurrent.futures as cf
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


EDITS = ("Edit", "Write", "NotebookEdit")


def first_tool(query, project, model, strict=False):
    """'skill' if the session loads code-orchestrator in time, else the tools it used first."""
    limit = 1 if strict else 3
    p = subprocess.Popen(["claude", "-p", query, "--model", model, "--output-format", "stream-json", "--verbose",
                          "--max-turns", str(limit + 1)],
                         cwd=project, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    seen = []
    try:
        for line in p.stdout:
            if not line.startswith("{"):
                continue
            d = json.loads(line)
            if d.get("type") == "assistant" and not d.get("parent_tool_use_id"):
                for b in d["message"].get("content", []):
                    if b.get("type") != "tool_use":
                        continue
                    skill = (b.get("input") or {}).get("skill", "")
                    if b["name"] == "Skill" and skill == "code-orchestrator":
                        return "skill" if not seen else "skill after " + ",".join(seen)
                    seen.append(f"{b['name']}:{skill}" if skill else b["name"])
                    if b["name"] in EDITS or len(seen) >= limit:
                        return "+".join(seen)
            if d.get("type") == "result":
                break
        return "+".join(seen) or "none"
    finally:
        p.kill()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", required=True)
    ap.add_argument("--evals", required=True)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--out")
    ap.add_argument("--strict", action="store_true", help="count only a first-call load")
    a = ap.parse_args()
    queries = json.load(open(a.evals))
    project = Path(tempfile.mkdtemp(prefix="trigger-"))
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    shutil.copytree(a.skill, project / ".claude/skills/code-orchestrator")
    jobs = [(i, r) for i in range(len(queries)) for r in range(a.runs)]
    results = {}
    with cf.ThreadPoolExecutor(10) as ex:
        for (i, _), res in zip(jobs, ex.map(lambda j: first_tool(queries[j[0]]["query"], project, a.model, a.strict), jobs)):
            results.setdefault(i, []).append(res)
    rows, ok = [], 0
    for i, q in enumerate(queries):
        hits = sum(x.startswith("skill") for x in results[i])
        passed = (hits > a.runs / 2) == q["should_trigger"]
        ok += passed
        rows.append({"query": q["query"], "should_trigger": q["should_trigger"], "triggered": hits, "runs": a.runs,
                     "first_tools": results[i], "passed": passed})
        print(f"{'PASS' if passed else 'FAIL'} {hits}/{a.runs} expect={q['should_trigger']} {results[i]} {q['query'][:70]}")
    print(f"score {ok}/{len(queries)}")
    if a.out:
        json.dump({"model": a.model, "runs": a.runs, "metric": "first call" if a.strict else "within 3 calls, before any edit",
                   "score": ok, "total": len(queries), "results": rows}, open(a.out, "w"), indent=1)
    shutil.rmtree(project, ignore_errors=True)


if __name__ == "__main__":
    main()
