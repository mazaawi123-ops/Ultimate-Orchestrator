#!/usr/bin/env bash
# orch.sh: the mechanical steps of the code-orchestrator loop, so the planner runs one
# command instead of retyping (and occasionally mistyping) a pipeline.
# Portable: bash 3.2+ (the macOS default), GNU or BSD tools, git 2.20+.
# Run it from anywhere inside the repo; it works on the repo's top level.
set -u

usage() {
  cat <<'EOF'
usage: orch.sh <command> [args]

  stamp
      Before dispatching parallel workers. Fails if the main tree has uncommitted changes;
      otherwise marks "now" in .orchestrator/stamp.
  stray
      When the workers return. Lists every file in the main tree written since the stamp
      (git-ignored files included, .git and worktrees excluded), plus `git status`.
      Exit 1 if anything outside .orchestrator/ changed: a worker left its worktree.
  wt-add <task>
      Creates the worktree .orchestrator/worktrees/<task> on a new branch orch-wt/<task> from
      HEAD, links node_modules/.venv/venv in if the main tree has them, and prints its path.
      Inside the repo, so editing it needs no extra permission; git-ignored with .orchestrator/.
  wt-finish <task>
      After merging. Copies the worktree's .orchestrator/ (its report) to
      .orchestrator/reports/<task>/, removes the worktree, and deletes its branch if merged.
  clean-room [VAR=value ...] -- <test command ...>
      Runs the tests in a fresh detached worktree of HEAD: no .env or other ignored files,
      secret-looking environment variables unset, and each VAR=value set (point service
      URLs at a closed port, e.g. API_URL=http://127.0.0.1:9). Exits with the tests' status.
      For pipelines or &&, pass: -- bash -c '<command>'
  old-tests <BASE> <test path> [...]
      Shows every line deleted from test files that existed at BASE. Exit 1 if there are any.
  diff <BASE> <N>
      Writes the verifier's diff, BASE..HEAD without .orchestrator/, to .orchestrator/diff-<N>.patch.
EOF
}

die() { echo "orch.sh: $*" >&2; exit 2; }

ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || die "not inside a git repo"
cd "$ROOT" || die "cannot cd to $ROOT"

wt_dir() { echo "$ROOT/.orchestrator/worktrees/$1"; }

# Link dependency folders from the main tree into a worktree, and hide the links from git.
# Dependencies are fine to share; secrets (.env) are not, so only these names are linked.
link_deps() {
  local dest=$1 d exclude
  exclude=$(git rev-parse --git-path info/exclude)
  case "$exclude" in /*) ;; *) exclude="$ROOT/$exclude" ;; esac
  mkdir -p "$(dirname "$exclude")"
  for d in node_modules .venv venv; do
    if [ -e "$ROOT/$d" ] && [ ! -e "$dest/$d" ]; then
      ln -s "$ROOT/$d" "$dest/$d"
      grep -qx "/$d" "$exclude" 2>/dev/null || echo "/$d" >> "$exclude"
    fi
  done
}

cmd_stamp() {
  local dirty
  dirty=$(git status --porcelain)
  if [ -n "$dirty" ]; then
    echo "main tree is not clean; commit or restore these before dispatching:" >&2
    echo "$dirty" >&2
    exit 1
  fi
  mkdir -p .orchestrator
  : > .orchestrator/stamp
  # Some filesystems keep coarse timestamps, so a write right after the stamp could share
  # its mtime and look "not newer". Wait a second so every later write is strictly newer.
  sleep 1
  echo "stamped $(date '+%H:%M:%S'); run 'orch.sh stray' when the workers return"
}

cmd_stray() {
  [ -f .orchestrator/stamp ] || die "no .orchestrator/stamp; run 'orch.sh stamp' before dispatching"
  local prune line rel files outside inside status
  prune=(-path ./.git -o -path ./.claude/worktrees)
  # Worktrees nested inside the main tree are the workers' own; skip them.
  while IFS= read -r line; do
    case "$line" in
      "worktree $ROOT/"*) rel=${line#"worktree $ROOT/"}; prune+=(-o -path "./$rel") ;;
    esac
  done < <(git worktree list --porcelain)
  files=$(find . \( "${prune[@]}" \) -prune -o -type f -newer .orchestrator/stamp -print | sed 's|^\./||' | sort)
  outside=$(printf '%s\n' "$files" | grep -v '^\.orchestrator/' | grep -v '^$')
  inside=$(printf '%s\n' "$files" | grep '^\.orchestrator/' | grep -v '^\.orchestrator/stamp$')
  status=$(git status --porcelain)
  if [ -n "$inside" ]; then
    echo "written in .orchestrator/ since the stamp (fine if you wrote them yourself; a worker's report here means it left its worktree):"
    printf '%s\n' "$inside" | sed 's/^/  /'
  fi
  if [ -z "$outside" ] && [ -z "$status" ]; then
    echo "OK: nothing outside .orchestrator/ written in the main tree since the stamp"
    return 0
  fi
  echo "STRAY: the main tree changed while workers ran. Compare each file with the worker's branch, discard it, and log it."
  [ -n "$outside" ] && { echo "files written since the stamp:"; printf '%s\n' "$outside" | sed 's/^/  /' | head -50; }
  [ -n "$status" ] && { echo "git status --porcelain:"; printf '%s\n' "$status" | sed 's/^/  /'; }
  exit 1
}

cmd_wt_add() {
  [ $# -eq 1 ] || die "usage: orch.sh wt-add <task>"
  local task=$1 dir
  dir=$(wt_dir "$task")
  [ -e "$dir" ] && die "$dir already exists"
  git check-ignore -q .orchestrator/worktrees || die ".orchestrator/ isn't git-ignored; add it to .git/info/exclude first"
  mkdir -p "$(dirname "$dir")"
  git show-ref --verify --quiet "refs/heads/orch-wt/$task" && die "branch orch-wt/$task already exists"
  git worktree add -q "$dir" -b "orch-wt/$task" HEAD || die "git worktree add failed"
  mkdir -p "$dir/.orchestrator"
  link_deps "$dir"
  echo "$dir"
}

cmd_wt_finish() {
  [ $# -eq 1 ] || die "usage: orch.sh wt-finish <task>"
  local task=$1 dir left
  dir=$(wt_dir "$task")
  [ -d "$dir" ] || die "no worktree at $dir"
  left=$(git -C "$dir" status --porcelain)
  if [ -n "$left" ]; then
    echo "worktree has uncommitted changes; merge or discard them first:" >&2
    echo "$left" >&2
    exit 1
  fi
  # Reports live in the worktree's git-ignored .orchestrator/, which removal deletes.
  if [ -d "$dir/.orchestrator" ]; then
    mkdir -p ".orchestrator/reports/$task"
    cp -R "$dir/.orchestrator/." ".orchestrator/reports/$task/"
    echo "copied reports to .orchestrator/reports/$task/"
  fi
  git worktree remove "$dir" || die "git worktree remove failed"
  if git branch -d "orch-wt/$task" >/dev/null 2>&1; then
    echo "removed $dir and branch orch-wt/$task"
  else
    echo "removed $dir; kept branch orch-wt/$task because it isn't merged into $(git rev-parse --abbrev-ref HEAD)"
  fi
}

cmd_clean_room() {
  local assigns=() drop=() v upper tmp status
  while [ $# -gt 0 ] && [ "$1" != "--" ]; do
    case "$1" in
      *=*) assigns+=("$1") ;;
      *) die "expected VAR=value or --, got '$1'" ;;
    esac
    shift
  done
  [ "${1:-}" = "--" ] || die "usage: orch.sh clean-room [VAR=value ...] -- <test command ...>"
  shift
  [ $# -gt 0 ] || die "no test command after --"
  # No credentials: collect every variable that looks like one. GIT_* is left alone because
  # git's own settings live there (GIT_CONFIG_KEY_0 is not a secret).
  for v in $(env | sed -n 's/^\([A-Za-z_][A-Za-z0-9_]*\)=.*/\1/p'); do
    upper=$(printf '%s' "$v" | tr '[:lower:]' '[:upper:]')
    case "$upper" in
      GIT_*) ;;
      *KEY*|*TOKEN*|*SECRET*|*PASSWORD*|*PASSWD*|*CREDENTIAL*|*AUTH*|DATABASE_URL|*_DSN) drop+=("$v") ;;
    esac
  done
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/orch-clean.XXXXXX") || die "mktemp failed"
  git worktree add -q --detach "$tmp/repo" HEAD || { rm -rf "$tmp"; die "git worktree add failed"; }
  trap 'git -C "$ROOT" worktree remove --force "$tmp/repo" >/dev/null 2>&1; rm -rf "$tmp"; git -C "$ROOT" worktree prune' EXIT
  link_deps "$tmp/repo"
  echo "clean room: $tmp/repo (HEAD $(git rev-parse --short HEAD))${assigns[0]+, with ${assigns[*]}}; ${#drop[@]} credential-like variable(s) unset"
  (
    for v in ${drop[@]+"${drop[@]}"}; do unset "$v" 2>/dev/null; done
    cd "$tmp/repo" && env ${assigns[@]+"${assigns[@]}"} "$@"
  )
  status=$?
  echo "clean room: exit $status"
  exit $status
}

cmd_old_tests() {
  [ $# -ge 2 ] || die "usage: orch.sh old-tests <BASE> <test path> [...]"
  local base=$1 add del path found=0
  shift
  git rev-parse --verify --quiet "$base^{commit}" >/dev/null || die "unknown BASE '$base'"
  while IFS=$'\t' read -r add del path; do
    [ -z "$path" ] && continue
    [ "$del" = "0" ] && continue
    git cat-file -e "$base:$path" 2>/dev/null || continue   # file is new since BASE
    found=1
    echo "== $path: $del line(s) deleted or changed since BASE"
    git diff --no-renames "$base"..HEAD -- "$path" | grep '^-' | grep -v '^---' | sed 's/^/  /'
  done < <(git diff --no-renames --numstat "$base"..HEAD -- "$@")
  if [ $found -eq 0 ]; then
    echo "OK: no lines deleted from tests that existed at BASE"
    return 0
  fi
  echo "Read each line above. A changed import is fine; a removed, changed or loosened assertion or test the plan doesn't allow goes back to its worker."
  exit 1
}

cmd_diff() {
  [ $# -eq 2 ] || die "usage: orch.sh diff <BASE> <N>"
  mkdir -p .orchestrator
  git diff -U10 "$1"..HEAD -- . ':!.orchestrator' > ".orchestrator/diff-$2.patch" || die "git diff failed"
  echo "$ROOT/.orchestrator/diff-$2.patch ($(wc -l < ".orchestrator/diff-$2.patch" | tr -d ' ') lines)"
}

[ $# -ge 1 ] || { usage; exit 2; }
sub=$1
shift
case "$sub" in
  stamp) cmd_stamp "$@" ;;
  stray) cmd_stray "$@" ;;
  wt-add) cmd_wt_add "$@" ;;
  wt-finish) cmd_wt_finish "$@" ;;
  clean-room) cmd_clean_room "$@" ;;
  old-tests) cmd_old_tests "$@" ;;
  diff) cmd_diff "$@" ;;
  -h|--help|help) usage ;;
  *) usage; exit 2 ;;
esac
