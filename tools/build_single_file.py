"""Rebuild code-orchestrator.single-file.md, the one-file version of the skill.

Some places take a skill as a single SKILL.md, so this folds the references in as
appendices A-C and the helper script in as appendix D.

Usage (from the repo root):  python tools/build_single_file.py
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "code-orchestrator")
OUT = os.path.join(ROOT, "code-orchestrator.single-file.md")

REFS = [
    ("references/run-record.md", "A", "Run record template"),
    ("references/worker-brief.md", "B", "Worker brief"),
    ("references/reviewer-brief.md", "C", "Reviewer briefs"),
]
SCRIPT_PARAGRAPH = re.compile(
    r"The mechanical guarantees live in `scripts/orch\.sh` in this skill's directory\. Run it as\s+"
    r"`bash <skill-dir>/scripts/orch\.sh <command>` from inside the repo; `help` lists everything\.")
SCRIPT_NOTE = (
    "The mechanical guarantees live in the helper script in Appendix D. Once per run, save it\n"
    "as `/tmp/orch.sh` and run it as `bash /tmp/orch.sh <command>` from inside the repo; `help`\n"
    "lists everything.")
APPENDICES = (
    "## Appendices\n\n"
    "- Appendix A: the run record template\n"
    "- Appendix B: the worker brief (only when delegating)\n"
    "- Appendix C: the reviewer briefs (only for an independent review)\n"
    "- Appendix D: orch.sh, the helper script\n\n"
    "Read the appendix you need when you reach that step; you don't need all of them up front.\n")


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
    return text.replace("bash <skill-dir>/scripts/orch.sh", "bash /tmp/orch.sh")


def main():
    s = open(os.path.join(SKILL, "SKILL.md")).read()
    s, n = SCRIPT_PARAGRAPH.subn(lambda m: SCRIPT_NOTE, s, count=1)
    assert n == 1, "script paragraph not found in SKILL.md"
    s = fix_refs(s)
    s, n = re.subn(r"## Files\n.*\Z", lambda m: APPENDICES, s, flags=re.S)
    assert n == 1, "## Files section not found in SKILL.md"
    out = [s.rstrip() + "\n"]
    for path, letter, title in REFS:
        body = open(os.path.join(SKILL, path)).read()
        body = demote(fix_refs(re.sub(r"^# .*\n", "", body, count=1)))
        out.append(f"\n---\n\n## Appendix {letter} — {title}\n" + body)
    script = open(os.path.join(SKILL, "scripts", "orch.sh")).read()
    out.append("\n---\n\n## Appendix D — orch.sh\n\n"
               "Save this as `/tmp/orch.sh` and run it with `bash`.\n\n"
               "````bash\n" + script.rstrip() + "\n````\n")
    open(OUT, "w").write("".join(out))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
