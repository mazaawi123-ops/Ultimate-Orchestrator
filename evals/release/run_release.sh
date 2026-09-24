#!/usr/bin/env bash
# Release validation: real `claude -p` sessions of the committed skill on the release tasks.
#
# usage: run_release.sh <prepared repos> <out dir> <task id> [<task id> ...]
#   prepare the repos with: bash evals/runner/prepare_repos.sh evals/release/tasks.json DIR
#   (the production tasks' setup writes a synthetic .env.production holding a canary string)
# Each task runs with its own route line, Opus at high effort and a $12 cap. out dir gets
# release.json (skill commit, Claude Code version, the hash of every skill and agent file) and
# <task name>/release/run-1/. Then: python3 evals/release/check_release.py <out dir> --black <black 20.8b1>
set -u
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/../.." && pwd)
REPOS=$1; OUT=$2; shift 2
[ $# -gt 0 ] || { sed -n 2,10p "$0"; exit 2; }
[ -z "$(git -C "$ROOT" status --porcelain -- code-orchestrator agents)" ] || { echo "commit the skill first, so the release names an exact version" >&2; exit 2; }
mkdir -p "$OUT"
python3 - "$ROOT" "$(claude --version 2>/dev/null | head -1)" > "$OUT/release.json" <<'PY'
import datetime, hashlib, json, subprocess, sys
from pathlib import Path
root = Path(sys.argv[1])
files = {str(f.relative_to(root)): hashlib.sha256(f.read_bytes()).hexdigest()
         for d in ("code-orchestrator", "agents") for f in sorted((root / d).rglob("*")) if f.is_file()}
print(json.dumps({"skill_commit": subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
                  "claude_version": sys.argv[2], "started": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                  "skill_files_sha256": files}, indent=1))
PY
for id in "$@"; do
  route=$(python3 -c "import json,sys; print([t for t in json.load(open(sys.argv[1]))['tasks'] if t['id']==sys.argv[2]][0]['route'])" "$HERE/tasks.json" "$id")
  bash "$ROOT/evals/runner/run_e2e.sh" --tasks "$HERE/tasks.json" --id "$id" --repos "$REPOS" --out "$OUT" --config release \
    --run 1 --skill "$ROOT/code-orchestrator" --agents "$ROOT/agents" --route "$route" --model opus --effort high \
    --max-budget-usd 12 < /dev/null > "$OUT/log.$id" 2>&1
  echo "$id finished: $(tail -1 "$OUT/log.$id")"
done
