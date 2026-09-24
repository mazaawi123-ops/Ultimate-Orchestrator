"""Collect usage, outputs and git state for one end-to-end run directory.

usage: collect.py <run dir> <start epoch> <end epoch>

Writes <run dir>/timing.json and fills <run dir>/outputs/. Costs are Claude Code's local
estimates (total_cost_usd / costUSD: token counts at list price), not billing records.
usage_by_agent keeps request-level token classes per agent, so costs can be re-priced
exactly instead of being split in proportion to tokens.
"""
import json
import os
import shutil
import subprocess
import sys

COST_NOTE = "Claude Code local estimate at list price; not a billing record"


def read_stream(path):
    lines = []
    for raw in open(path):
        try:
            lines.append(json.loads(raw))
        except Exception:
            pass
    return lines


def summarize(lines):
    """Cost, per-model and per-agent usage, dispatches and skill use from a stream-json log."""
    res = ([l for l in lines if l.get("type") == "result"] or [{}])[-1]
    per_model = {}
    for m, u in (res.get("modelUsage") or {}).items():
        per_model[m] = {
            "input": u.get("inputTokens", 0), "output": u.get("outputTokens", 0),
            "cache_read": u.get("cacheReadInputTokens", 0), "cache_write": u.get("cacheCreationInputTokens", 0),
            "cost_usd_estimate": round(u.get("costUSD", 0) or 0, 4),
        }
    # Dispatches and request-level usage per agent (deduplicated by message id).
    agents, dispatches = {}, []
    for l in lines:
        if l.get("type") == "assistant" and not l.get("parent_tool_use_id"):
            for b in (l.get("message") or {}).get("content") or []:
                if b.get("type") == "tool_use" and b.get("name") in ("Agent", "Task"):
                    i = b.get("input") or {}
                    agents[b["id"]] = i.get("subagent_type") or ("model:" + str(i.get("model", "inherit")))
                    dispatches.append({"agent": agents[b["id"]], "model_param": i.get("model"), "description": i.get("description")})
    usage_by_agent, seen = {}, set()
    for l in lines:
        if l.get("type") != "assistant":
            continue
        m = l.get("message") or {}
        if m.get("id") in seen:
            continue
        seen.add(m.get("id"))
        u = m.get("usage") or {}
        who = agents.get(l.get("parent_tool_use_id"), "subagent") if l.get("parent_tool_use_id") else "main"
        key = f"{who}|{m.get('model', '')}"
        a = usage_by_agent.setdefault(key, {"requests": 0, "input": 0, "output": 0, "cache_read": 0, "cache_write": 0})
        a["requests"] += 1
        a["input"] += u.get("input_tokens", 0) or 0
        a["output"] += u.get("output_tokens", 0) or 0
        a["cache_read"] += u.get("cache_read_input_tokens", 0) or 0
        a["cache_write"] += u.get("cache_creation_input_tokens", 0) or 0
    skill_used = any(
        b.get("type") == "tool_use" and b.get("name") == "Skill" and (b.get("input") or {}).get("skill") == "code-orchestrator"
        for l in lines if l.get("type") == "assistant" and not l.get("parent_tool_use_id")
        for b in (l.get("message") or {}).get("content") or [])
    return {
        "cost_usd_estimate": round(res.get("total_cost_usd") or 0, 4),
        "cost_note": COST_NOTE,
        "num_turns": res.get("num_turns"),
        "subtype": res.get("subtype"),
        "per_model": per_model,
        "usage_by_agent": usage_by_agent,
        "dispatches": dispatches,
        "skill_used": skill_used,
    }, res.get("result") or "(no result message)"


def main():
    D, start, end = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    repo = os.path.join(D, "repo")
    out = os.path.join(D, "outputs")
    os.makedirs(out, exist_ok=True)
    summary, report = summarize(read_stream(os.path.join(D, "stream.jsonl")))
    open(os.path.join(out, "final_report.md"), "w").write(report)
    timing = {"cost_usd_estimate": summary["cost_usd_estimate"], "cost_note": COST_NOTE,
              "wall_seconds": end - start, "total_duration_seconds": end - start}
    timing.update({k: v for k, v in summary.items() if k not in timing})
    json.dump(timing, open(os.path.join(D, "timing.json"), "w"), indent=2)

    def git(*args, cwd=repo):
        return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True).stdout

    base = open(os.path.join(D, "base.txt")).read().strip() if os.path.exists(os.path.join(D, "base.txt")) else "main"
    snap = os.path.join(D, "_snap")
    shutil.rmtree(snap, ignore_errors=True)
    shutil.copytree(repo, snap, symlinks=True, ignore=shutil.ignore_patterns(".claude", "node_modules", "__pycache__", ".pytest_cache"))
    git("add", "-A", "--", ".", ":!.orchestrator", cwd=snap)
    open(os.path.join(out, "changes.patch"), "w").write(git("diff", "--cached", base, "--", ".", ":!.orchestrator", cwd=snap))
    shutil.rmtree(snap, ignore_errors=True)
    open(os.path.join(out, "git_state.txt"), "w").write(
        f"base: {base}\nbranches:\n{git('branch', '-a', '-v')}\nstatus:\n{git('status', '--short')}\n"
        f"worktrees:\n{git('worktree', 'list')}\nlog since base:\n{git('log', '--oneline', base + '..HEAD')}")
    orch = os.path.join(repo, ".orchestrator")
    if os.path.isdir(orch):
        shutil.copytree(orch, os.path.join(out, "orchestrator"), dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("worktrees", "runs", "node_modules", ".venv", "venv"))
    print(json.dumps({k: timing[k] for k in ("cost_usd_estimate", "wall_seconds", "skill_used", "subtype")}),
          [d["agent"] for d in timing["dispatches"]])


if __name__ == "__main__":
    main()
