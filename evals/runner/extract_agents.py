"""Write each dispatched agent's brief and reply from a run's stream log to a Markdown file.

usage: extract_agents.py <run dir> [<run dir> ...]
Writes <run dir>/outputs/agents.md. Used to read and adjudicate reviewer findings.
"""
import json
import sys
from pathlib import Path


def text_of(content):
    if isinstance(content, str):
        return content
    return "\n".join(b.get("text", "") for b in content or [] if isinstance(b, dict) and b.get("type") == "text")


for run in map(Path, sys.argv[1:]):
    calls, results = [], {}
    for raw in open(run / "stream.jsonl"):
        try:
            l = json.loads(raw)
        except Exception:
            continue
        # An agent that runs in the background replies through a task notification.
        if l.get("type") == "system" and l.get("subtype") == "task_notification" and l.get("tool_use_id"):
            results[l["tool_use_id"]] = l.get("summary") or ""
            continue
        if l.get("parent_tool_use_id"):
            continue
        for b in (l.get("message") or {}).get("content") or []:
            if not isinstance(b, dict):
                continue
            if l.get("type") == "assistant" and b.get("type") == "tool_use" and b.get("name") in ("Agent", "Task"):
                calls.append(b)
            if l.get("type") == "user" and b.get("type") == "tool_result":
                results.setdefault(b.get("tool_use_id"), text_of(b.get("content")))
    out = [f"# Agents dispatched in {run.parent.parent.name}/{run.parent.name}/{run.name}\n"]
    for i, c in enumerate(calls, 1):
        inp = c.get("input") or {}
        out.append(f"## {i}. {inp.get('subagent_type') or 'general'}: {inp.get('description', '')}\n")
        out.append("### Brief\n\n```text\n" + (inp.get("prompt") or "") + "\n```\n")
        out.append("### Reply\n\n```text\n" + results.get(c["id"], "(no reply recorded)") + "\n```\n")
    (run / "outputs").mkdir(exist_ok=True)
    (run / "outputs/agents.md").write_text("\n".join(out))
    print(run, len(calls), "dispatches")
