#!/usr/bin/env bash
# Frozen-patch reviewer check for the absolute-word rule in references/reviewer-brief.md.
#
# The candidate (records/frozen-review/candidate.patch) is the first candidate the Reviewed
# release run on 781715f sent for review: it makes up a missed Friday run on Saturday, although
# the request says "never on Saturday or Sunday". That run's reviewer rated this an observation.
# Each arm dispatches the same orch-verifier (Opus, extra-high effort) on the same candidate with
# the same brief, except for one sentence:
#   old-wording  the brief as the 781715f run's builder wrote it
#   new-wording  the same brief with the reviewer-brief sentence added after that run
# Arms run one after another. Whatever a reviewer leaves in /tmp is moved aside before the next.
#
# usage: frozen_review.sh <schedule repo> <out dir> [--prepare-only] [arm ...]
#   schedule repo: a clone of https://github.com/dbader/schedule containing commit 82a43db
#   arms default to: new-wording old-wording
set -u
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/../.." && pwd)
REC=$ROOT/evals/results/records/frozen-review
BASE=82a43db1b938d8fdf60103bd41f329e06c8d3651
SRC=$1; OUT=$2; shift 2
PREPARE_ONLY=0; [ "${1:-}" = --prepare-only ] && { PREPARE_ONLY=1; shift; }
ARMS=("$@"); [ ${#ARMS[@]} -gt 0 ] || ARMS=(new-wording old-wording)
KEEP='^(claude|environment-manager|env-manager|hsperfdata|node-compile-cache|pytest-of-root|cc-socks|code-sign|codesign|mcp-config|editor-|orch-weekday-venv|tmp)'
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd -P)
for arm in "${ARMS[@]}"; do
  d=$OUT/$arm; rm -rf "$d"; mkdir -p "$d"
  git clone -q "$SRC" "$d/repo" && git -C "$d/repo" checkout -q -b orch/weekday "$BASE" || exit 2
  git -C "$d/repo" apply --index "$REC/candidate.patch" || exit 2
  git -C "$d/repo" -c user.name=Claude -c user.email=noreply@anthropic.com commit -q \
    -m "Add every().weekday to run jobs Monday to Friday only"
  cand=$(git -C "$d/repo" rev-parse HEAD); patch=$d/repo/.orchestrator/review/candidate-${cand:0:12}.patch
  mkdir -p "$(dirname "$patch")" "$d/repo/.claude/agents"
  git -C "$d/repo" diff "$BASE" "$cand" > "$patch"
  cp "$ROOT"/agents/*.md "$d/repo/.claude/agents/"
  printf '.claude/\n.orchestrator/\n' >> "$d/repo/.git/info/exclude"
  sed -e "s#{REPO}#$d/repo#g" -e "s#{CANDIDATE}#$cand#g" -e "s#{PATCH}#$patch#g" "$REC/brief-$arm.txt" > "$d/brief.txt"
  [ "$PREPARE_ONLY" = 1 ] && { echo "$arm prepared: $d (candidate $cand)"; continue; }
  start=$(date +%s); ls /tmp > "$d/tmp-before.txt"
  ( cd "$d/repo" && timeout 1800 claude -p "$(cat "$d/brief.txt")" --agent orch-verifier --model opus --effort xhigh \
      --max-budget-usd 3 --allowedTools "Bash,Read,Glob,Grep" --output-format stream-json --verbose \
      < /dev/null > "$d/stream.jsonl" 2> "$d/stderr.txt" )
  echo "exit=$?" > "$d/exit.txt"; echo "$(( $(date +%s) - start ))" > "$d/wall_seconds"
  mkdir -p "$OUT/tmp-leftovers/$arm"
  ls /tmp | grep -vxFf "$d/tmp-before.txt" | grep -vE "$KEEP" | while read -r n; do mv "/tmp/$n" "$OUT/tmp-leftovers/$arm/"; done
  echo "$arm done: $(cat "$d/exit.txt"), $(cat "$d/wall_seconds")s"
done
