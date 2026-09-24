#!/usr/bin/env bash
# Clone every task repo at its pinned commit into DIR/<repo_dir> (branch main) and run its setup.
# usage: prepare_repos.sh <tasks.json> <DIR>
# Setup installs test dependencies with pip/npm into the current environment.
set -eu
TASKS=$1; DIR=$2; mkdir -p "$DIR"
python3 - "$TASKS" <<'PY' | while IFS=$'\t' read -r repo url commit setup; do
import json, sys
for t in json.load(open(sys.argv[1]))["tasks"]:
    print("\t".join([t["repo_dir"], t["url"], t["commit"], " && ".join(t["setup"]) or "true"]))
PY
  dest="$DIR/$repo"
  if [ -d "$dest/.git" ] && [ "$(git -C "$dest" rev-parse HEAD)" = "$commit" ]; then echo "ready: $dest"; continue; fi
  rm -rf "$dest"; mkdir -p "$dest"
  git -C "$dest" init -q -b main
  git -C "$dest" fetch -q --depth 1 "$url" "$commit"
  git -C "$dest" checkout -q -B main FETCH_HEAD
  (cd "$dest" && bash -c "$setup")
  [ -z "$(git -C "$dest" status --porcelain)" ] || { echo "setup left the tree dirty in $dest" >&2; git -C "$dest" status --short >&2; exit 1; }
  echo "prepared: $dest at $commit"
done
