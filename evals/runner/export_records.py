"""Export end-to-end runs as sanitized, re-graded records.

usage: export_records.py <manifest.json> <records dir>

The manifest lists runs: {"runs": [{"src": run dir, "record": path under <records dir>,
"grader": grader name, "kind": "fixtures"|"repos", "base": commit (optional),
"label": what was run, "note": optional}]}.

For each run the record gets:
  prompt.txt, final_report.md, plan/notes/report files the run left, changes.patch
  timing.json   recomputed from stream.jsonl by collect.summarize (estimates, not bills)
  grading.json  the current graders' result (the run's repo is re-graded in place)
  grading.at-the-time.json  the grading that was recorded when the run was measured, if any
and records/summary.tsv gets one row per run. Absolute paths are replaced by placeholders.
"""
import json
import os
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "graders"))
import collect  # noqa: E402
import grade_fixtures  # noqa: E402
import grade_repos  # noqa: E402

PATHS = [
    (re.compile(r"/tmp/claude-\d+/[^\s\"'`)]*?/scratchpad(/code-orchestrator-workspace)?"), "<workspace>"),
    (re.compile(r"/tmp/grader-selftest-[A-Za-z0-9_]+"), "<tmp>"),
    (re.compile(r"/home/[A-Za-z0-9_.-]+"), "<home>"),
    (re.compile(r"/root/"), "<root>/"),
]
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Records name model families (as the agent files do), not exact model versions.
MODEL_ID = re.compile(r"claude-(opus|sonnet|haiku|fable)(-[0-9]+)*(-[0-9]{8})?(\[1m\])?")
MODEL_NAME = re.compile(r"\b(Opus|Sonnet|Haiku|Fable) [0-9]+(\.[0-9]+)?\b")
SESSION = re.compile(r"https://claude\.ai/code/session_[A-Za-z0-9]+")


def clean(text):
    for rx, rep in PATHS:
        text = rx.sub(rep, text)
    text = MODEL_ID.sub(lambda m: m.group(1), text)
    text = MODEL_NAME.sub(lambda m: m.group(1), text)
    text = SESSION.sub("<session>", text)
    return EMAIL.sub("<email>", text)


def merge_keys(d, keyfn):
    """Rename keys (e.g. model IDs to families), summing numeric fields of keys that collide."""
    out = {}
    for k, v in d.items():
        k2 = keyfn(k)
        if k2 not in out:
            out[k2] = dict(v)
            continue
        for f, x in v.items():
            if isinstance(x, (int, float)):
                out[k2][f] = round(out[k2].get(f, 0) + x, 4)
    return out


def put(dst, text):
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(clean(text))


def main():
    manifest, out = json.load(open(sys.argv[1])), Path(sys.argv[2])
    rows = [["record", "label", "cost_usd_estimate", "wall_seconds", "hidden_checks_passed", "functional", "regression",
             "safety", "artifact", "reporting", "dispatches", "note"]]
    for r in manifest["runs"]:
        src, dst = Path(r["src"]), out / r["record"]
        shutil.rmtree(dst, ignore_errors=True)
        dst.mkdir(parents=True)
        for name in ("prompt.txt",):
            if (src / name).exists():
                put(dst / name, (src / name).read_text())
        for f in sorted((src / "outputs").glob("*")):
            if f.is_file() and f.suffix in (".md", ".patch", ".txt") and f.name != "git_state.txt":
                put(dst / f.name, f.read_text(errors="replace"))
        # The run's own record (current skill: .orchestrator/; previous skill: plan and notes).
        for name in ("record.md", "evidence.tsv", "manifest", "summary.md", "notes.md", "plan.md", "request.md"):
            f = src / "outputs/orchestrator" / name
            if f.is_file():
                put(dst / "orchestrator" / name, f.read_text(errors="replace"))
        if (src / "probes.json").exists():
            put(dst / "probes.json", (src / "probes.json").read_text())
        old_timing = json.load(open(src / "timing.json")) if (src / "timing.json").exists() else {}
        if (src / "grading.json").exists() and not (src / "grading.at-the-time.json").exists():
            shutil.copy(src / "grading.json", src / "grading.at-the-time.json")
        if (src / "grading.at-the-time.json").exists():
            put(dst / "grading.at-the-time.json", (src / "grading.at-the-time.json").read_text())
        timing, _ = collect.summarize(collect.read_stream(src / "stream.jsonl"))
        timing["per_model"] = merge_keys(timing["per_model"], clean)
        timing["usage_by_agent"] = merge_keys(timing["usage_by_agent"], clean)
        timing["wall_seconds"] = old_timing.get("wall_seconds")
        timing["source"] = r["label"]
        timing["usage_note"] = ("per_model has complete token counts. usage_by_agent splits requests, input and cache tokens "
                                "exactly; output_at_start is the stream's start-of-message output count, a lower bound.")
        put(dst / "timing.json", json.dumps(timing, indent=2))
        if r.get("base") and not (src / "base.txt").exists():
            (src / "base.txt").write_text(r["base"] + "\n")
        if r["kind"] == "fixtures":
            g = grade_fixtures.grade_one(r["grader"], src, with_reporting=True)
        else:
            g = grade_repos.grade(r["grader"], str(src))
        put(dst / "grading.json", json.dumps(g, indent=2, ensure_ascii=False))
        cat = g["by_category"]
        cell = lambda c: f"{cat[c]['passed']}/{cat[c]['total']}" if c in cat else "-"
        rows.append([r["record"], r["label"], f"{timing['cost_usd_estimate']:.2f}", str(timing["wall_seconds"]),
                     str(g["hidden_checks_passed"]), cell("functional"), cell("regression"), cell("safety"), cell("artifact"),
                     cell("reporting"), " ".join(d["agent"] for d in timing["dispatches"]) or "-", r.get("note", "")])
        print("\t".join(rows[-1][:10]))
    (out / "summary.tsv").write_text("\n".join("\t".join(x) for x in rows) + "\n")


if __name__ == "__main__":
    main()
