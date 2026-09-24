#!/usr/bin/env bash
# The routing pilot: 2 held-out tasks x 3 arms x N repeats, each a real `claude -p` session.
#   A  direct     current skill + agents, told to use Direct mode (one builder, no reviewer)
#   B  reviewed   current skill + agents, told to use Reviewed mode (one builder, one reviewer)
#   C  hierarchy  the previous skill (commit 9192405) + its agents, used as it routes itself
# Every arm gets the same main-session model and effort, the same budget cap, and the same
# reviewer (orch-verifier: Opus, extra-high effort, in both agent sets). Runs start in random order.
#
# usage: run_pilot.sh <prepared pilot repos> <out dir> <old skill dir> [repeats] [parallel]
#   prepare the repos with: bash evals/runner/prepare_repos.sh evals/pilot/tasks.json DIR
#   old skill dir: git archive 9192405 code-orchestrator agents | tar -x -C DIR
set -u
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/../.." && pwd)
REPOS=$1; OUT=$2; OLD=$3; REPEATS=${4:-2}; PAR=${5:-6}
mkdir -p "$OUT"
[ -z "$(git -C "$ROOT" status --porcelain -- code-orchestrator agents)" ] || { echo "commit the skill first, so the pilot names an exact version" >&2; exit 2; }
printf '{"skill_commit":"%s","old_skill_sha256":"%s","claude_version":"%s","started":"%s","repeats":%s}\n' \
  "$(git -C "$ROOT" rev-parse HEAD)" "$(cat "$OLD/code-orchestrator/SKILL.md" | shasum -a 256 | cut -c1-16)" \
  "$(claude --version 2>/dev/null | head -1)" "$(date -u +%FT%TZ)" "$REPEATS" > "$OUT/pilot.json"
jobs=()
for run in $(seq 1 "$REPEATS"); do
  for id in p1 p2; do
    jobs+=("$id|direct|$run|$ROOT/code-orchestrator|$ROOT/agents|Use the code-orchestrator skill in Direct mode (no delegation, no independent review).")
    jobs+=("$id|reviewed|$run|$ROOT/code-orchestrator|$ROOT/agents|Use the code-orchestrator skill in Reviewed mode (you build; one independent review).")
    jobs+=("$id|hierarchy|$run|$OLD/code-orchestrator|$OLD/agents|Use the code-orchestrator skill.")
  done
done
# Randomised order (seeded, so a replay runs in the same order); the order is kept in order.txt.
printf '%s\n' "${jobs[@]}" | python3 -c "import random,sys; l=sys.stdin.read().splitlines(); random.Random(int(sys.argv[1])).shuffle(l); print('\n'.join(l))" "${PILOT_SEED:-1}" > "$OUT/order.txt"
running=0
while IFS= read -r j; do
  IFS='|' read -r id config run skill agents route <<< "$j"
  bash "$ROOT/evals/runner/run_e2e.sh" --tasks "$ROOT/evals/pilot/tasks.json" --id "$id" --repos "$REPOS" --out "$OUT" \
    --config "$config" --run "$run" --skill "$skill" --agents "$agents" --route "$route" \
    --model opus --effort high --max-budget-usd 12 < /dev/null > "$OUT/log.$id.$config.$run" 2>&1 &
  running=$((running + 1))
  if [ "$running" -ge "$PAR" ]; then wait -n; running=$((running - 1)); fi
done < "$OUT/order.txt"
wait
echo "all runs finished: $OUT"
