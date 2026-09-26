#!/usr/bin/env bash
# Model comparison for the skill's four delegated roles: which model does each role best, at
# what cost. Each cell is one real `claude -p --agent` session: the role's agent file with the
# candidate model's frontmatter, on a fixed task with an objective grader
# (model_matrix_grade.py).
#
#   role        task                                                     repo
#   reviewer    the frozen candidate that runs a missed Friday job on    schedule @ BASE
#               Saturday, with the current reviewer brief (verdict must
#               be FAIL, the case blocking)
#   worker      windowed(strict=) as a worker brief (the pilot's hidden   more-itertools @ BASE
#               checks grade it)
#   mechanical  rename one private helper everywhere (deterministic       schedule @ BASE
#               checks)
#   researcher  four questions with computed ground truth, read-only     schedule @ BASE
#
#   model    frontmatter
#   fable    model: claude-fable-5-1, effort: xhigh
#   opus     model: claude-opus-5-5,  effort: medium
#   sonnet   model: sonnet, effort: high for the reviewer, medium otherwise (the skill's current settings)
#   haiku    model: haiku (Haiku 4.5 takes no effort setting)
#
# usage: model_matrix.sh <schedule repo> <more-itertools repo> <out dir> [--prepare-only]
#                        [--roles r,r,...] [--models m,m,...]
#   the repos are prepared clones at the pinned commits (evals/runner/prepare_repos.sh with
#   evals/release/tasks.json and evals/pilot/tasks.json). Roles run in parallel; within a
#   role, models run one after another, cheapest first. Whatever a session leaves in /tmp is
#   moved aside before the next one.
set -u
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/../.." && pwd)
REC=$ROOT/evals/results/records/frozen-review; BRIEFS=$HERE/model-matrix
SCHED=$1; MORE=$2; OUT=$3; shift 3
ROLES="reviewer worker mechanical researcher"; MODELS="haiku sonnet opus fable"; PREPARE=0
while [ $# -gt 0 ]; do
  case "$1" in --prepare-only) PREPARE=1 ;; --roles) ROLES=${2//,/ }; shift ;; --models) MODELS=${2//,/ }; shift ;; *) echo "unknown option $1" >&2; exit 2 ;; esac; shift
done
BASE_SCHED=82a43db1b938d8fdf60103bd41f329e06c8d3651
BASE_MORE=b5e3886a37209bb880f17d82fbf4ba00ece0e41e
KEEP='^(claude|environment-manager|env-manager|hsperfdata|node-compile-cache|pytest-of-root|cc-socks|code-sign|codesign|mcp-config|editor-|orch-weekday-venv|tmp)'
[ -z "$(git -C "$ROOT" status --porcelain -- agents code-orchestrator)" ] || { echo "commit the skill and agents first, so the comparison names an exact version" >&2; exit 2; }
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd -P)
printf '{"skill_commit":"%s","claude_version":"%s","started":"%s"}\n' "$(git -C "$ROOT" rev-parse HEAD)" \
  "$(claude --version 2>/dev/null | head -1)" "$(date -u +%FT%TZ)" > "$OUT/matrix.json"

model_lines() {  # model role
  case "$1" in
    fable) echo "model: claude-fable-5-1"; echo "effort: xhigh" ;;
    opus) echo "model: claude-opus-5-5"; echo "effort: medium" ;;
    sonnet) echo "model: sonnet"; if [ "$2" = reviewer ]; then echo "effort: high"; else echo "effort: medium"; fi ;;
    haiku) echo "model: haiku" ;;
    *) echo "unknown model $1" >&2; exit 2 ;;
  esac
}
role_cfg() {  # role -> BASE_AGENT DISALLOWED MAXTURNS TOOLS CAP REPO BRIEF
  case "$1" in
    reviewer) BASE_AGENT=orch-verifier; DISALLOWED="Agent, Edit, Write, NotebookEdit"; MAXTURNS=80; TOOLS="Bash,Read,Glob,Grep"; CAP=6; SRC=$SCHED; BRIEF=$REC/brief-new-wording.txt ;;
    worker) BASE_AGENT=orch-worker; DISALLOWED="Agent"; MAXTURNS=150; TOOLS="Bash,Read,Write,Edit,Glob,Grep,TodoWrite"; CAP=8; SRC=$MORE; BRIEF=$BRIEFS/worker.txt ;;
    mechanical) BASE_AGENT=orch-mechanic; DISALLOWED="Agent"; MAXTURNS=120; TOOLS="Bash,Read,Write,Edit,Glob,Grep,TodoWrite"; CAP=3; SRC=$SCHED; BRIEF=$BRIEFS/mechanical.txt ;;
    researcher) BASE_AGENT=orch-researcher; DISALLOWED="Agent, Edit, Write, NotebookEdit"; MAXTURNS=60; TOOLS="Bash,Read,Glob,Grep"; CAP=3; SRC=$SCHED; BRIEF=$BRIEFS/researcher.txt ;;
    *) echo "unknown role $1" >&2; exit 2 ;;
  esac
}
agent_body() { awk 'f==2 { print } /^---$/ { f++ }' "$ROOT/agents/$1.md"; }

prepare_cell() {  # role model
  local role=$1 model=$2 d=$OUT/$1/$2 base cand patch
  role_cfg "$role"
  rm -rf "$d"; mkdir -p "$d"
  git clone -q "$SRC" "$d/repo" || return 1
  case "$role" in
    reviewer)
      git -C "$d/repo" checkout -q -b orch/weekday "$BASE_SCHED" && git -C "$d/repo" apply --index "$REC/candidate.patch" || return 1
      git -C "$d/repo" -c user.name=Claude -c user.email=noreply@anthropic.com commit -q -m "Add every().weekday to run jobs Monday to Friday only"
      cand=$(git -C "$d/repo" rev-parse HEAD); patch=$d/repo/.orchestrator/review/candidate-${cand:0:12}.patch
      mkdir -p "$(dirname "$patch")"; git -C "$d/repo" diff "$BASE_SCHED" "$cand" > "$patch"
      sed -e "s#{REPO}#$d/repo#g" -e "s#{CANDIDATE}#$cand#g" -e "s#{PATCH}#$patch#g" "$BRIEF" > "$d/brief.txt"
      echo "$BASE_SCHED" > "$d/base.txt" ;;
    worker)
      git -C "$d/repo" checkout -q -b orch-wt/windowed-strict "$BASE_MORE" || return 1
      sed -e "s#{REPO}#$d/repo#g" "$BRIEF" > "$d/brief.txt"; echo "$BASE_MORE" > "$d/base.txt" ;;
    mechanical)
      git -C "$d/repo" checkout -q -b orch-wt/rename "$BASE_SCHED" || return 1
      sed -e "s#{REPO}#$d/repo#g" "$BRIEF" > "$d/brief.txt"; echo "$BASE_SCHED" > "$d/base.txt" ;;
    researcher)
      git -C "$d/repo" checkout -q "$BASE_SCHED" 2>/dev/null || git -C "$d/repo" checkout -q --detach "$BASE_SCHED" || return 1
      sed -e "s#{REPO}#$d/repo#g" "$BRIEF" > "$d/brief.txt"; echo "$BASE_SCHED" > "$d/base.txt" ;;
  esac
  git -C "$d/repo" config user.name Claude; git -C "$d/repo" config user.email noreply@anthropic.com
  printf '.claude/\n.orchestrator/\n' >> "$d/repo/.git/info/exclude"
  mkdir -p "$d/repo/.claude/agents"
  { echo "---"; echo "name: cmp-$role-$model"; echo "description: \"$role role, $model candidate (model comparison)\""
    model_lines "$model" "$role"; echo "disallowedTools: $DISALLOWED"; echo "maxTurns: $MAXTURNS"; echo "---"
    agent_body "$BASE_AGENT"; } > "$d/repo/.claude/agents/cmp-$role-$model.md"
  cp "$d/repo/.claude/agents/cmp-$role-$model.md" "$d/agent.md"
}

run_cell() {  # role model
  local role=$1 model=$2 d=$OUT/$1/$2 start
  role_cfg "$role"
  start=$(date +%s); ls /tmp > "$d/tmp-before.txt"
  ( cd "$d/repo" && env CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0 timeout 2400 claude -p "$(cat "$d/brief.txt")" \
      --agent "cmp-$role-$model" --max-budget-usd "$CAP" --allowedTools "$TOOLS" \
      --output-format stream-json --verbose < /dev/null > "$d/stream.jsonl" 2> "$d/stderr.txt" )
  echo "exit=$?" > "$d/exit.txt"; echo "$(( $(date +%s) - start ))" > "$d/wall_seconds"
  mkdir -p "$OUT/tmp-leftovers/$role-$model"
  ls /tmp | grep -vxFf "$d/tmp-before.txt" | grep -vE "$KEEP" | while read -r n; do mv "/tmp/$n" "$OUT/tmp-leftovers/$role-$model/" 2>/dev/null; done
  echo "$role/$model: $(cat "$d/exit.txt"), $(cat "$d/wall_seconds")s"
}

run_role() {  # role
  local role=$1 m
  for m in $MODELS; do
    prepare_cell "$role" "$m" || { echo "$role/$m: prepare failed" >&2; continue; }
    [ "$PREPARE" = 1 ] && { echo "$role/$m prepared: $OUT/$role/$m"; continue; }
    run_cell "$role" "$m"
  done
}
for r in $ROLES; do run_role "$r" > "$OUT/log.$r" 2>&1 & done
wait
cat "$OUT"/log.*
echo "done: $OUT"
