#!/usr/bin/env bash
# Install this skill's five agents where Claude Code loads them. Claude Code reads agents from
# ~/.claude/agents (every project) or <repo>/.claude/agents (one project), not from inside a
# skill, so they ship in this skill's agents/ folder and are copied out once.
# usage: install-agents.sh [--project <repo>]      (default: ~/.claude/agents)
set -eu
here=$(cd "$(dirname "$0")/.." && pwd)
dest=~/.claude/agents
if [ "${1:-}" = --project ]; then
  [ -n "${2:-}" ] || { echo "usage: install-agents.sh [--project <repo>]" >&2; exit 2; }
  dest="$2/.claude/agents"
fi
mkdir -p "$dest"
for f in "$here"/agents/*.md; do
  n=$(basename "$f")
  if [ -f "$dest/$n" ] && cmp -s "$f" "$dest/$n"; then s=unchanged
  elif [ -e "$dest/$n" ] || [ -L "$dest/$n" ]; then s=updated
  else s=installed; fi
  [ "$s" = unchanged ] || { rm -f "$dest/$n"; cp "$f" "$dest/$n"; }
  echo "  $s: $dest/$n"
done
echo "Claude Code picks them up for the next agent it starts."
