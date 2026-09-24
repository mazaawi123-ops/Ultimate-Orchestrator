"""Post-hoc probes: the repos' own CI checks, and the issues reviewers raised during the
pilot, run against every arm's final candidate. They were written after the reviews, so
they're reported apart from the hidden checks fixed before the pilot.

usage: ci_probes.py <pilot results dir> --black <black 20.8b1 executable> [--perf]
  p1 (more-itertools): its `make check` (ruff format --check, ruff check, stubtest);
     --perf also times the non-strict path against BASE (a reviewer's observation).
  p2 (schedule): its CI format job (black 20.8b1 --check), no new mypy errors, and two
     behaviours reviewers raised: a missed Friday run first polled on Saturday, and a job
     whose next run falls past its until() deadline.
Writes <run dir>/probes.json and prints a table.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

SCHEDULE_PROBE = r'''
import datetime, json, schedule
from test_schedule import mock_datetime
r = {}
try:
    runs = []
    schedule.clear()
    with mock_datetime(2024, 1, 5, 8, 0):          # Friday 08:00; Friday 09:00 is missed
        schedule.every().weekday.at("09:00").do(lambda: runs.append(1))
    with mock_datetime(2024, 1, 6, 12, 0):         # first poll: Saturday 12:00
        schedule.run_pending()
    r["missed_friday_runs_on_saturday"] = len(runs) > 0
    runs = []
    schedule.clear()
    # Sunday noon: Monday's run is past it. Built inside mock_datetime, which swaps the class.
    with mock_datetime(2024, 1, 5, 8, 0):
        schedule.every().weekday.at("09:00").until(datetime.datetime(2024, 1, 7, 12, 0)).do(lambda: runs.append(1))
    with mock_datetime(2024, 1, 6, 12, 0):
        schedule.run_pending()
        deadline = datetime.datetime(2024, 1, 7, 12, 0)
        r["until_job_lingers_past_deadline"] = bool(schedule.jobs) and schedule.next_run() > deadline
    with mock_datetime(2024, 1, 8, 9, 0, 1):
        before = len(runs)
        schedule.run_pending()
        r["until_runs_after_deadline"] = len(runs) > before
except Exception as e:
    r["error"] = repr(e)
# Another unit combined with .weekday, before or after it: rejected, or silently accepted?
for name, build in (("unit_before_weekday_rejected", lambda: schedule.every().hour.weekday.do(lambda: None)),
                    ("unit_after_weekday_rejected", lambda: schedule.every().weekday.hours.do(lambda: None))):
    schedule.clear()
    try:
        build()
        r[name] = False
    except Exception:
        r[name] = True
print(json.dumps(r))
'''


def sh(cmd, cwd, env=None, timeout=600):
    e = dict(os.environ, **(env or {}))
    p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, env=e, timeout=timeout)
    return p.returncode, p.stdout + p.stderr


def tree(repo, rev):
    """A clean copy of `rev` (committed or working tree) outside the repo."""
    d = Path(tempfile.mkdtemp(prefix="probe-"))
    if rev == "WORKTREE":
        shutil.copytree(repo, d / "t", symlinks=True, ignore=shutil.ignore_patterns(".git", ".claude", ".orchestrator", "__pycache__", ".venv", "venv",
                                                           ".*_cache", "*.egg-info", "node_modules", "build", "dist"))
    else:
        (d / "t").mkdir()
        subprocess.run(f"git -C {repo} archive {rev} | tar -x -C {d / 't'}", shell=True, check=True)
    return d


def mypy_errors(t):
    _, out = sh("mypy -p schedule", t, timeout=900)
    return sorted({re.sub(r":\d+(:\d+)?:", ":", l) for l in out.splitlines() if ": error:" in l})


def perf(t, base):
    stmt = "for _ in windowed(data, 5): pass"
    setup = "from more_itertools import windowed; data = list(range(200000))"
    best = {}
    for _ in range(3):  # alternate to spread noise
        for name, path in (("base", base), ("cand", t)):
            _, out = sh(f'python3 -m timeit -r 7 -n 5 -s "{setup}" "{stmt}"', path, {"PYTHONPATH": str(path)})
            m = re.search(r"best of \d+: ([\d.]+) (\w+)", out) or re.search(r": ([\d.]+) (\w+) per loop", out)
            v = float(m.group(1)) * {"nsec": 1e-9, "usec": 1e-6, "msec": 1e-3, "sec": 1}[m.group(2)]
            best[name] = min(best.get(name, v), v)
    return round(best["cand"] / best["base"], 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--black", required=True)
    ap.add_argument("--perf", action="store_true")
    a = ap.parse_args()
    rows, bases = [], {}
    for run in sorted(Path(a.results).glob("*/*/run-*")):
        if not (run / "repo").is_dir() or not (run / "timing.json").exists():
            continue  # unfinished runs are skipped
        task, config = run.parent.parent.name, run.parent.name
        repo, base = run / "repo", (run / "base.txt").read_text().strip()
        d = tree(repo, "WORKTREE")
        t = d / "t"
        res = {}
        if task.startswith("more-itertools"):
            res["ruff_format"] = sh("ruff format --check .", t)[0] == 0
            res["ruff_check"] = sh("ruff check more_itertools tests", t)[0] == 0
            res["stubtest"] = sh("stubtest more_itertools.more more_itertools.recipes", t, {"PYTHONPATH": str(t)}, 900)[0] == 0
            if a.perf:
                if "p1" not in bases:
                    bases["p1"] = tree(repo, base)
                res["nonstrict_time_vs_base"] = perf(t, bases["p1"] / "t")
        else:
            res["black_20_8b1"] = sh(f"{a.black} --check .", t)[0] == 0
            if "p2" not in bases:
                bases["p2"] = tree(repo, base)
                bases["p2_mypy"] = mypy_errors(bases["p2"] / "t")
            new = [e for e in mypy_errors(t) if e not in bases["p2_mypy"]]
            res["no_new_mypy_errors"] = not new
            if new:
                res["new_mypy_errors"] = new[:5]
            _, out = sh(f"python3 - <<'PYEOF'\n{SCHEDULE_PROBE}\nPYEOF", t)
            res.update(json.loads([l for l in out.splitlines() if l.startswith("{")][-1]))
        shutil.rmtree(d, ignore_errors=True)
        json.dump(res, open(run / "probes.json", "w"), indent=1)
        rows.append((task, config, run.name, res))
        print(task, config, run.name, json.dumps(res))
    for k in ("p1", "p2"):
        if k in bases:
            shutil.rmtree(bases[k], ignore_errors=True)


if __name__ == "__main__":
    main()
