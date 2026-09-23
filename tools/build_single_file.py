"""Rebuild code-orchestrator.single-file.md, the one-file version of the skill.

Some places take a skill as a single SKILL.md, so this folds the references in as
appendices A-D and the helper script in as appendix E.

Usage (from the repo root):  python tools/build_single_file.py
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "code-orchestrator")
OUT = os.path.join(ROOT, "code-orchestrator.single-file.md")

REFS = [
    ("references/plan-template.md", "A", "Plan template"),
    ("references/worker-brief.md", "B", "Worker brief"),
    ("references/verifier-brief.md", "C", "Verifier briefs"),
    ("references/example-run.md", "D", "Worked examples: real runs"),
]
SCRIPT_NOTE = (
    "The mechanical steps are in the script in Appendix E: the stray-write check, worktrees,\n"
    "the clean-room run, the old-test check and the diff. Once per run, after `.orchestrator/`\n"
    "is git-ignored, save it as `.orchestrator/orch.sh` and run it as\n"
    "`bash .orchestrator/orch.sh <command>` from inside the repo. If you can't run it, read\n"
    "it: each command is a few lines of git you can run by hand."
)


def demote(text):
    out, fenced = [], False
    for line in text.split("\n"):
        if line.startswith("```"):
            fenced = not fenced
        if not fenced and line.startswith("## "):
            line = "#" + line
        out.append(line)
    return "\n".join(out)


def fix_refs(text):
    for path, letter, _ in REFS:
        text = text.replace(f"`{path}`", f"Appendix {letter}")
        text = text.replace(f"`{path.split('/')[-1]}`", f"Appendix {letter}")
    return text.replace("bash <skill-dir>/scripts/orch.sh", "bash .orchestrator/orch.sh")


def main():
    s = open(os.path.join(SKILL, "SKILL.md")).read()
    s, n = re.subn(r"The mechanical steps are in `scripts/orch.sh`.*?by hand\.", SCRIPT_NOTE, s, count=1, flags=re.S)
    assert n == 1, "script paragraph not found in SKILL.md"
    s = fix_refs(s)
    s, n = re.subn(
        r"## Files\n.*\Z",
        "## Appendices\n\n"
        "- Appendix A: the plan template, with an example filled in\n"
        "- Appendix B: the worker brief. Fill every section\n"
        "- Appendix C: the full and scoped verifier briefs\n"
        "- Appendix D: real runs, with token counts and cost per agent\n"
        "- Appendix E: orch.sh, the helper script\n\n"
        "Read the appendix you need when you reach that step; you don't need all of them up front.\n",
        s, flags=re.S)
    assert n == 1, "## Files section not found in SKILL.md"
    out = [s.rstrip() + "\n"]
    for path, letter, title in REFS:
        body = open(os.path.join(SKILL, path)).read()
        body = demote(fix_refs(re.sub(r"^# .*\n", "", body, count=1)))
        out.append(f"\n---\n\n## Appendix {letter} — {title}\n" + body)
    script = open(os.path.join(SKILL, "scripts", "orch.sh")).read()
    out.append("\n---\n\n## Appendix E — orch.sh\n\n"
               "Save this as `.orchestrator/orch.sh` (the folder is git-ignored) and run it with `bash`.\n\n"
               "````bash\n" + script.rstrip() + "\n````\n")
    open(OUT, "w").write("".join(out))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
