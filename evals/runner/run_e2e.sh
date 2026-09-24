#!/usr/bin/env bash
# Run one end-to-end eval: a real `claude -p` session on a fresh copy of a task repo.
#
# usage: run_e2e.sh --tasks FILE --id ID --repos DIR --out DIR --config NAME [options]
#   --tasks FILE     a tasks JSON (evals/evals.json, evals/real-repos.json, evals/pilot/tasks.json)
#   --id ID          task id in that file
#   --repos DIR      directory holding the prepared task repos (by the task's "repo_dir" or
#                    the last component of its "files" entry)
#   --out DIR        results root; this run goes to DIR/<task name>/<config>/run-<n>/
#   --config NAME    label for this arm, e.g. direct, reviewed, hierarchy, no-skill
#   --run N          repeat number (default 1)
#   --skill DIR      skill folder to install as a project skill (omit for no skill)
#   --agents DIR     agent definitions to install as project agents (optional)
#   --route TEXT     extra line appended to the prompt, e.g. "Use the code-orchestrator skill in Direct mode."
#   --model ID       main session model (default opus, the alias)
#   --effort LEVEL   main session effort (default high)
#   --max-budget-usd N  hard cap passed to claude -p (default 12)
#   --env K=V        extra environment for the session (repeatable), e.g. PYTHONPATH=src
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
TASKS="" ID="" REPOS="" OUT="" CONFIG="" RUN=1 SKILL="" AGENTS="" ROUTE="" MODEL=opus EFFORT=high BUDGET=12
EXTRA_ENV=()
while [ $# -gt 0 ]; do
  case "$1" in
    --tasks) TASKS=$2 ;; --id) ID=$2 ;; --repos) REPOS=$2 ;; --out) OUT=$2 ;; --config) CONFIG=$2 ;;
    --run) RUN=$2 ;; --skill) SKILL=$2 ;; --agents) AGENTS=$2 ;; --route) ROUTE=$2 ;;
    --model) MODEL=$2 ;; --effort) EFFORT=$2 ;; --max-budget-usd) BUDGET=$2 ;; --env) EXTRA_ENV+=("$2") ;;
    *) echo "unknown option $1" >&2; exit 2 ;;
  esac; shift 2
done
[ -n "$TASKS" ] && [ -n "$ID" ] && [ -n "$REPOS" ] && [ -n "$OUT" ] && [ -n "$CONFIG" ] || { sed -n 2,20p "$0"; exit 2; }

read_task() { python3 - "$TASKS" "$ID" "$1" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); t = [x for x in d.get("evals", d.get("tasks", [])) if str(x["id"]) == sys.argv[2]][0]
k = sys.argv[3]
if k == "repo_dir": print(t.get("repo_dir") or t["files"][0].rstrip("/").split("/")[-1])
elif k == "watch_files": print("\n".join(t.get(k, [])))
else: print(t[k])
PY
}
NAME=$(read_task name); PROMPT=$(read_task prompt); REPO_DIR=$(read_task repo_dir); WATCH=$(read_task watch_files)
D="$OUT/$NAME/$CONFIG/run-$RUN"
rm -rf "$D"; mkdir -p "$D/outputs"
cp -a "$REPOS/$REPO_DIR" "$D/repo" || { echo "no prepared repo at $REPOS/$REPO_DIR" >&2; exit 2; }
git -C "$D/repo" rev-parse HEAD > "$D/base.txt"
if [ -n "$SKILL" ]; then mkdir -p "$D/repo/.claude/skills"; cp -r "$SKILL" "$D/repo/.claude/skills/code-orchestrator"; fi
if [ -n "$AGENTS" ]; then mkdir -p "$D/repo/.claude/agents"; cp "$AGENTS"/*.md "$D/repo/.claude/agents/"; fi
echo ".claude/" >> "$D/repo/.git/info/exclude"
# The exact skill and agent files this run used, by hash.
python3 - "$D/repo/.claude" > "$D/skill-files.sha256" <<'PY'
import hashlib, sys
from pathlib import Path
root = Path(sys.argv[1])
for f in sorted(p for p in root.rglob("*") if p.is_file()):
    print(hashlib.sha256(f.read_bytes()).hexdigest() + "  " + str(f.relative_to(root)))
PY
# Files the session must not read ("watch_files"): set their access time far in the past, so any
# later read moves it (relatime updates the access time when it is older than the modification time).
watch_access() {  # set | report <out file>
  [ -n "$WATCH" ] || return 0
  python3 - "$D/repo" "$1" "${2:-}" "$WATCH" <<'PY'
import datetime, json, os, sys
repo, mode, out, files = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split("\n")
PAST = 946684800  # 2000-01-01T00:00:00Z
res = {}
for f in files:
    p = os.path.join(repo, f)
    if not os.path.exists(p):
        res[f] = {"exists": False}
        continue
    st = os.stat(p)
    if mode == "set":
        os.utime(p, (PAST, st.st_mtime))
    else:
        res[f] = {"exists": True, "read": st.st_atime > PAST + 1,
                  "atime": datetime.datetime.fromtimestamp(st.st_atime, datetime.timezone.utc).isoformat()}
if mode == "report":
    res["_method"] = ("access time set to 2000-01-01 before the session; a later access time means a process read the "
                      "file during the run (relatime). Listing or stat-ing the file does not count as a read.")
    json.dump(res, open(out, "w"), indent=1)
PY
}
watch_access set
SUFFIX=$'\n\n(Context for this run: no one is available to answer questions until you finish, so make sensible calls, record them, and carry on. Keep any plan, notes or report files you create; don\'t delete them at the end.)'
[ -n "$ROUTE" ] && SUFFIX="$SUFFIX"$'\n'"$ROUTE"
printf '%s' "$PROMPT$SUFFIX" > "$D/prompt.txt"
printf '{"task":"%s","config":"%s","run":%s,"model":"%s","effort":"%s","max_budget_usd":%s,"skill":"%s","agents":"%s","route":"%s","claude_version":"%s"}\n' \
  "$NAME" "$CONFIG" "$RUN" "$MODEL" "$EFFORT" "$BUDGET" "${SKILL:+installed}" "${AGENTS:+installed}" "$ROUTE" "$(claude --version 2>/dev/null | head -1)" > "$D/config.json"
START=$(date +%s)
# CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0: claude -p otherwise stops a background agent (such as a
# long review) after 10 idle minutes and drops its result; one pilot run lost its review that way.
( cd "$D/repo" && env CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0 ${EXTRA_ENV[@]+"${EXTRA_ENV[@]}"} timeout 5400 claude -p "$(cat "$D/prompt.txt")" --model "$MODEL" --effort "$EFFORT" \
    --max-budget-usd "$BUDGET" \
    --allowedTools "Bash,Read,Write,Edit,Glob,Grep,Agent,Task,TaskCreate,TaskUpdate,TaskList,TaskGet,TaskOutput,TodoWrite,Skill,NotebookEdit" \
    --output-format stream-json --verbose < /dev/null > "$D/stream.jsonl" 2> "$D/stderr.txt" )
echo "exit=$?" > "$D/exit.txt"
watch_access report "$D/file-access.json"
python3 "$HERE/collect.py" "$D" "$START" "$(date +%s)"
