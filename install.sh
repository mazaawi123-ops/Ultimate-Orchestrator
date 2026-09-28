#!/usr/bin/env bash
# Install the code-orchestrator skill, with its five agents, for your user account.
# Usage, from this repo's folder:  bash install.sh
set -eu
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p ~/.claude/skills
rm -rf ~/.claude/skills/code-orchestrator
cp -R "$here/code-orchestrator" ~/.claude/skills/
echo "Installed:"
echo "  ~/.claude/skills/code-orchestrator (the agents ship inside it, in agents/)"
bash ~/.claude/skills/code-orchestrator/scripts/install-agents.sh
echo "Pick the main session's model with /model and /effort; each agent's model is set in its file."
