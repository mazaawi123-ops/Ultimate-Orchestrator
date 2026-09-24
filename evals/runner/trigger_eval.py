"""Does the skill load when it should, and stay out when it shouldn't?

usage: trigger_eval.py --skill DIR --evals FILE [--runs 3] [--model sonnet] [--out FILE]

Installs the skill as a project skill in an empty git repo, then runs each query with
`claude -p` (at most 2 turns). A run counts as triggered when the session's first tool call
loads code-orchestrator. A query passes when most of its runs match its should_trigger label.
"""
import argparse
import concurrent.futures as cf
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def first_tool(query, project, model):
    p = subprocess.Popen(["claude", "-p", query, "--model", model, "--output-format", "stream-json", "--verbose", "--max-turns", "2"],
                         cwd=project, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    try:
        for line in p.stdout:
            if not line.startswith("{"):
                continue
            d = json.loads(line)
            if d.get("type") == "assistant":
                for b in d["message"].get("content", []):
                    if b.get("type") == "tool_use":
                        skill = (b.get("input") or {}).get("skill", "")
                        return "skill" if b["name"] == "Skill" and skill == "code-orchestrator" else f"{b['name']}:{skill}"
            if d.get("type") == "result":
                return "none"
        return "none"
    finally:
        p.kill()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", required=True)
    ap.add_argument("--evals", required=True)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--out")
    a = ap.parse_args()
    queries = json.load(open(a.evals))
    project = Path(tempfile.mkdtemp(prefix="trigger-"))
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    shutil.copytree(a.skill, project / ".claude/skills/code-orchestrator")
    jobs = [(i, r) for i in range(len(queries)) for r in range(a.runs)]
    results = {}
    with cf.ThreadPoolExecutor(10) as ex:
        for (i, _), res in zip(jobs, ex.map(lambda j: first_tool(queries[j[0]]["query"], project, a.model), jobs)):
            results.setdefault(i, []).append(res)
    rows, ok = [], 0
    for i, q in enumerate(queries):
        hits = sum(x == "skill" for x in results[i])
        passed = (hits > a.runs / 2) == q["should_trigger"]
        ok += passed
        rows.append({"query": q["query"], "should_trigger": q["should_trigger"], "triggered": hits, "runs": a.runs,
                     "first_tools": results[i], "passed": passed})
        print(f"{'PASS' if passed else 'FAIL'} {hits}/{a.runs} expect={q['should_trigger']} {results[i]} {q['query'][:70]}")
    print(f"score {ok}/{len(queries)}")
    if a.out:
        json.dump({"model": a.model, "runs": a.runs, "score": ok, "total": len(queries), "results": rows}, open(a.out, "w"), indent=1)
    shutil.rmtree(project, ignore_errors=True)


if __name__ == "__main__":
    main()
