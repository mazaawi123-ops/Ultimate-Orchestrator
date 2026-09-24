"""Build one self-contained Markdown file for an independent reviewer: the report, the whole
skill, the evidence and the verification code.

usage: python3 tools/build_review_bundle.py [output path]
"""
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "code-orchestrator-review-bundle.md"
LANG = {".py": "python", ".sh": "bash", ".json": "json", ".md": "markdown", ".tsv": "text", ".log": "text"}


def fenced(path, text=None):
    text = (ROOT / path).read_text() if text is None else text
    longest = max((len(m) for m in re.findall(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    lang = LANG.get(Path(path).suffix, "text")
    return f"#### `{path}`\n\n{fence}{lang}\n{text.rstrip()}\n{fence}\n"


def reviewer_replies():
    """Every reviewer and re-checker reply from the pilot, verbatim."""
    out = []
    for f in sorted((ROOT / "evals/results/records/pilot").glob("*/*/agents.md")):
        run = f"{f.parent.parent.name} / {f.parent.name}"
        for part in re.split(r"\n## \d+\. ", f.read_text())[1:]:
            head = part.split("\n", 1)[0]
            if not head.startswith(("orch-verifier", "orch-rechecker")):
                continue
            reply = part.split("### Reply", 1)[1].strip() if "### Reply" in part else "(no reply recorded)"
            out.append(f"#### {run}: {head}\n\n{reply}\n")
    return "\n".join(out)


def final_reports():
    out = []
    for f in sorted((ROOT / "evals/results/records/pilot").glob("*/*/final_report.md")):
        out.append(fenced(str(f.relative_to(ROOT))))
    return "\n".join(out)


def trigger_table():
    rows = ["| Set | Score | Query | Expected | Triggered (of 3) |", "|---|---|---|---|---|"]
    for name in ("dev-first-description", "dev-final-description", "heldout-final-description"):
        d = json.load(open(ROOT / f"evals/results/trigger/{name}.json"))
        for r in d["results"]:
            q = r["query"].replace("|", "\\|")
            q = q if len(q) <= 110 else q[:107] + "..."
            rows.append(f"| {name} | {d['score']}/{d['total']} | {q} | {'load' if r['should_trigger'] else 'stay out'} | {r['triggered']} |")
    return "\n".join(rows) + "\n"


def main():
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    sections = [
        ("Part 1. The report", [("docs/review/vnext-report.md", None)]),
        ("Part 2. The skill, complete", [
            ("code-orchestrator/SKILL.md", None),
            ("code-orchestrator/references/run-record.md", None),
            ("code-orchestrator/references/worker-brief.md", None),
            ("code-orchestrator/references/reviewer-brief.md", None),
            ("agents/orch-worker-haiku.md", None),
            ("agents/orch-worker-sonnet.md", None),
            ("agents/orch-verifier.md", None),
            ("agents/orch-rechecker.md", None),
            ("code-orchestrator/scripts/orch.sh", None),
            ("install.sh", None),
            ("README.md", None),
        ]),
        ("Part 3. Evidence", [
            ("evals/results/pilot.md", None),
            ("evals/results/records/pilot/summary.tsv", None),
            ("docs/review/reproduction-before-after.json", None),
            ("evals/results/grader-selftest.log", None),
            ("evals/results/records/summary.tsv", None),
        ]),
    ]
    toc = ["Part 1. The report", "Part 2. The skill, complete", "Part 3. Evidence",
           "Part 4. Pilot reviewer replies, verbatim", "Part 5. Pilot final reports, verbatim",
           "Part 6. Trigger test results", "Part 7. Verification code", "Part 8. Historical measurements",
           "Part 9. The first independent review and the vNext proposal"]
    out = [f"# code-orchestrator: complete review bundle (commit {head})\n",
           "Everything an independent reviewer needs, in one file: the report, the whole skill, the "
           "evidence and the code that produced it. Paths in the report refer to files reproduced "
           "below under the same path. Dollar figures are Claude Code's local estimates, not bills.\n",
           "**Reading order:** Parts 1–3 are the core, about a third of the file. Parts 4–9 are there "
           "to check claims against.\n",
           "## Contents\n", "\n".join(f"{i}. {t}" for i, t in enumerate(toc, 1)) + "\n"]
    for title, files in sections:
        out.append(f"\n---\n\n## {title}\n")
        for path, text in files:
            if path == "docs/review/vnext-report.md":
                text = (ROOT / path).read_text().split("\n", 1)[1]  # drop its title; the Part heading replaces it
                text = re.sub(r"^### ", "#### ", text, flags=re.M)
                out.append(re.sub(r"^## ", "### ", text, flags=re.M))
            else:
                out.append(fenced(path, text))
    out.append("\n---\n\n## Part 4. Pilot reviewer replies, verbatim\n")
    out.append("Every `orch-verifier` and `orch-rechecker` reply from the 12 pilot runs, as the main "
               "session received it. The run `schedule-weekday / reviewed-run-1` has no reply: its "
               "review was stopped by `claude -p`'s idle limit (report, section 5).\n")
    out.append(reviewer_replies())
    out.append("\n---\n\n## Part 5. Pilot final reports, verbatim\n")
    out.append(final_reports())
    out.append("\n---\n\n## Part 6. Trigger test results\n")
    out.append("First tool call loads the skill = triggered; 3 runs per prompt, Sonnet session, "
               "`--max-turns 2`. A prompt passes when the majority matches its expectation.\n\n")
    out.append(trigger_table())
    out.append("\n---\n\n## Part 7. Verification code\n")
    for path in ["tests/helper/test_orch.py", "tests/helper/review_reproductions.py", "evals/README.md",
                 "evals/graders/grade_repos.py", "evals/graders/grade_fixtures.py", "evals/graders/selftest.py",
                 "evals/pilot/README.md", "evals/pilot/tasks.json", "evals/pilot/run_pilot.sh", "evals/pilot/ci_probes.py",
                 "evals/pilot/summarize.py", "evals/runner/run_e2e.sh", "evals/runner/collect.py",
                 "evals/runner/prepare_repos.sh", "evals/runner/trigger_eval.py", "evals/runner/export_records.py",
                 "evals/runner/extract_agents.py", "evals/real-repos.json", "evals/trigger/dev.json", "evals/trigger/heldout.json"]:
        out.append(fenced(path))
    out.append("\n---\n\n## Part 8. Historical measurements\n")
    out.append(fenced("evals/results/measurements.md"))
    out.append("\n---\n\n## Part 9. The first independent review and the vNext proposal\n")
    out.append(fenced("docs/review/independent-review.md"))
    out.append(fenced("docs/review/vnext-proposal.md"))
    OUT.write_text("\n".join(out))
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
