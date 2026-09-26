#!/usr/bin/env bash
# Install the code-orchestrator skill and its five agents for your user account.
# Usage, from this repo's folder:  bash install.sh
set -eu
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p ~/.claude/skills ~/.claude/agents
rm -rf ~/.claude/skills/code-orchestrator
cp -R "$here/code-orchestrator" ~/.claude/skills/
cp "$here"/agents/*.md ~/.claude/agents/
echo "Installed:"
echo "  ~/.claude/skills/code-orchestrator"
for f in "$here"/agents/*.md; do echo "  ~/.claude/agents/$(basename "$f")"; done
echo "Pick the main session's model with /model and /effort; each agent's model is set in its file."
