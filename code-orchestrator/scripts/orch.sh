#!/usr/bin/env bash
# orch.sh: mechanical checks for the code-orchestrator skill.
# It freezes the exact candidate being delivered, ties every piece of evidence to that
# candidate, and refuses a "done" result on missing, stale or mismatched evidence.
# Portable: bash 3.2+ (the macOS default), GNU or BSD tools, git 2.20+.
# Run it from anywhere inside the repo; it works on the repo's top level.
set -u

usage() {
  cat <<'EOF'
usage: orch.sh <command> [args]

Run lifecycle
  start <name> [--offline] [-- <test command>]
      Begin a run. Refuses a tree with uncommitted work (exit 4). Stops at an unfinished
      earlier run (exit 3) and archives a finished one. Creates branch orch/<name>,
      git-ignores .orchestrator/, records BASE and, given a test command, the baseline:
      exit code, counts and failing tests, so later failures can be told apart.
  status              Manifest, candidate, recent evidence and repair cycles (for resuming).
  require <review|fresh|offline> ...
  require check <id> ...
                      Completion requirements that `gate` enforces. `check <id>` names a
                      command that must pass on the final candidate: `run <id> -- <command>`.
  ignore <pattern>    Git-ignore a generated path locally (.git/info/exclude), and log it.
  finish <done|partial|blocked> [note]
                      Close the run. `done` runs the gate first and refuses if it fails.
                      Keeps the record; removes finished worker worktrees.

Candidate and evidence
  One rule decides what counts: a check is identified by its kind and label, only its latest
  result counts, and that result must be for the current candidate and passing. Command and
  manual evidence must also be for the current environment (see below); a review is tied to
  the candidate only. Each command's evidence names the checkout it ran in, as it was before
  the command, and is void if the command changed that checkout (HEAD, index, file flags,
  tracked or untracked files), the main checkout or the environment fingerprint.
  check [--label L] [--offline] -- <test command>
                      Freeze the candidate (refuses uncommitted or untracked leftovers), run
                      the tests against it, re-check the tree afterwards, audit test changes,
                      and note git-ignored files the tests could have read. Exit 0 only with
                      no new failures, no leftovers and no unapproved test changes.
  candidate           Freeze the candidate only (clean tree required).
  run <label> [--explore] [--offline] -- <command>
                      Evidence against the candidate: a CI check, lint, a type check. A
                      failing run blocks `done` until a later run of the same label passes.
                      --explore marks a run that never counts, such as a reproduction
                      expected to fail before the fix.
  fresh [--label L] [--offline] [--keep-home] [--keep VAR] [--deps copy|none] [VAR=value ...] -- <command>
                      Run in a fresh checkout of the candidate: no ignored or untracked files,
                      an allowlisted environment and a temporary HOME. Give it the setup too
                      (e.g. -- sh -c 'make generate && pytest'); files the setup generates must
                      be git-ignored (.gitignore or orch.sh ignore). NOT a filesystem sandbox:
                      absolute paths outside the checkout stay readable.
  tests               Audit changes to tests that existed at BASE: deleted lines, added
                      skip/only/xfail markers, runner configuration, fixtures and snapshots,
                      and skipped or executed counts against the baseline.
  approve <path|count:skipped|count:executed> <reason>
                      Approve a deliberate test change, bound to this version of the file or
                      to this exact count movement. A later change needs a new approval.
  diff                Write the review patch BASE..candidate; refuses if the tree doesn't
                      match the candidate.
  record <review|recheck|manual> <pass|fail|pending> [--id <id>] [note]
                      Evidence that isn't a command, against the candidate. A manual check
                      recorded for an earlier candidate must be repeated for the new one.
  waive <run:L|manual:ID|fresh[:L]|review> <reason>
                      Dispose of a check that no longer applies to this candidate. The test
                      check and anything `require`d can't be waived. Waivers are reported.
  repair <reason>     Open a repair cycle. Exit 1 once the budget is spent (default 2, or
                      ORCH_MAX_REPAIR_CYCLES). Advisory: it records and warns; it can't stop
                      a model that ignores it.
  gate                Check the completion requirements for the current candidate.

--offline runs the command without network (Linux: unshare -n; macOS: sandbox-exec) after a
loopback probe proves the block. It exits 5, running nothing, if this host can't enforce it or
the probe doesn't return exactly "verified". Only such runs satisfy `require offline`.

The environment fingerprint covers the OS, git, node and python versions and dependency-lock
metadata. `gate` holds each piece of command and manual evidence to it separately: a check whose
fingerprint differs from the current one, or after which files in dependency folders or
git-ignored inputs were added or modified (by modification time, caches excluded), must be run
again. Rerunning one check never refreshes another. None of this proves which files the tests
actually read: a passing `fresh` run is the proof of a clean candidate.

Parallel workers
  stamp / stray       Before and after parallel dispatch: detect writes to the main tree,
                      git-ignored files included.
  wt-add <task> [--deps copy|none|link]
                      Worktree .orchestrator/worktrees/<task> on branch orch-wt/<task>.
                      Dependency folders are copied (copy-on-write where supported). Links in
                      them, or chains of links, that end in the main checkout are re-pointed to
                      the copy or their targets copied, and a venv's launchers are re-pointed.
                      A link cycle or a link to the checkout's root is refused (so is `fresh`
                      with such a copy). Links to places outside the checkout stay shared and
                      are reported. `link` shares the folders writably.
  wt-finish <task>    Copy the worker's report out, remove the worktree, delete the merged branch.
  caps                What this host can enforce, and what it can't.
EOF
}

die() { echo "orch.sh: $*" >&2; exit 2; }

ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || die "not inside a git repo"
cd "$ROOT" || die "cannot cd to $ROOT"
O=.orchestrator
EV="$O/evidence.tsv"
DEP_DIRS="node_modules .venv venv"
NL=$'\n'

now() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }

# ---------------------------------------------------------------- manifest

mf_get() { [ -f "$O/manifest" ] && sed -n "s/^$1=//p" "$O/manifest" | tail -1; }
mf_set() {
  mkdir -p "$O"; touch "$O/manifest"
  grep -v "^$1=" "$O/manifest" > "$O/manifest.tmp"
  printf '%s=%s\n' "$1" "$(printf '%s' "$2" | tr '\t\n' '  ')" >> "$O/manifest.tmp"
  mv "$O/manifest.tmp" "$O/manifest"
}
need_run() { [ -f "$O/manifest" ] || die "no run here: start one with 'orch.sh start <name>'"; }
base_rev() { mf_get base; }

ensure_ignored() {
  if ! git check-ignore -q "$O/x"; then
    local ex; ex=$(git rev-parse --git-path info/exclude)
    mkdir -p "$(dirname "$ex")"
    echo "$O/" >> "$ex"
  fi
}

# ---------------------------------------------------------------- candidate

leftovers() { git status --porcelain --untracked-files=normal -- . ":(exclude)$O"; }

freeze_candidate() {
  local left
  left=$(leftovers)
  if [ -n "$left" ]; then
    echo "LEFTOVERS: the tree has changes that aren't committed, so there's no exact candidate:"
    printf '%s\n' "$left" | sed 's/^/  /'
    echo "Commit the intended files by name; delete the rest, or 'orch.sh ignore <pattern>' generated ones."
    return 1
  fi
  mkdir -p "$O"
  printf 'commit=%s\ntree=%s\ntime=%s\n' "$(git rev-parse HEAD)" "$(git rev-parse 'HEAD^{tree}')" "$(now)" > "$O/candidate"
  mf_set candidate "$(git rev-parse HEAD)"
  return 0
}
cand() { [ -f "$O/candidate" ] && sed -n "s/^$1=//p" "$O/candidate"; }

# Is the working tree exactly the frozen candidate? Prints the reason when it isn't.
candidate_current() {
  [ -f "$O/candidate" ] || { echo "no candidate frozen yet"; return 1; }
  [ "$(git rev-parse HEAD)" = "$(cand commit)" ] || { echo "HEAD moved since the candidate was frozen"; return 1; }
  [ -z "$(leftovers)" ] || { echo "the tree has uncommitted or untracked changes"; return 1; }
  return 0
}
require_current() {
  local why
  why=$(candidate_current) || die "candidate out of date ($why): run 'orch.sh check' again"
}

# ---------------------------------------------------------------- environment and logs

env_fp() {
  {
    uname -sm; git --version
    command -v node >/dev/null 2>&1 && node --version
    command -v python3 >/dev/null 2>&1 && python3 --version 2>&1
    local f
    for f in node_modules/.package-lock.json node_modules/.yarn-integrity node_modules/.modules.yaml .venv/pyvenv.cfg venv/pyvenv.cfg; do
      [ -f "$f" ] && { echo "$f"; git hash-object "$f"; }
    done
  } 2>/dev/null | git hash-object --stdin | cut -c1-12
}

# One line, tabs removed, credential-looking assignments masked.
show_cmd() {
  printf '%s ' "$@" | tr '\t\n' '  ' | sed -E \
    's/([A-Za-z0-9_]*(KEY|TOKEN|SECRET|PASSWORD|PASSWD|AUTH|CREDENTIAL|key|token|secret|password|passwd|auth|credential)[A-Za-z0-9_]*)=[^ ]*/\1=***/g'
}

next_seq() {
  local n=0
  [ -f "$EV" ] && n=$(($(wc -l < "$EV") - 1))
  printf '%03d' $((n + 1))
}

ev_append() {
  # seq time kind label commit tree exit status secs envfp counts log command net role
  # net: "offline-verified:<method>" only when the loopback probe proved network blocking, else "-".
  # role: "explore" for exploratory runs, which never count towards completion, else "-".
  if [ ! -f "$EV" ]; then
    mkdir -p "$O"
    printf 'seq\ttime\tkind\tlabel\tcommit\ttree\texit\tstatus\tsecs\tenvfp\tcounts\tlog\tcommand\tnet\trole\n' > "$EV"
  fi
  local row=("$@")
  while [ ${#row[@]} -lt 15 ]; do row+=("-"); done
  local IFS=$'\t'
  printf '%s\n' "${row[*]}" >> "$EV"
}

# Test-runner summaries: prints "passed failed skipped ran runner", with ? where unknown.
# Heuristic: pytest, unittest, TAP (node --test, tape), jest, vitest, go test -v, cargo.
parse_counts() {
  awk '
    function grab(s, re,   m) { if (match(s, re)) { m = substr(s, RSTART, RLENGTH); gsub(/[^0-9]/, "", m); return m + 0 } return -1 }
    function add(a, b) { return (b < 0) ? a : ((a < 0) ? b : a + b) }
    BEGIN { pp=pf=pe=ps=-1; ur=us=uf=ue=-1; tp=tf=ts=-1; tskip=0; jp=jf=js=-1; vp=vf=vs=-1; cp=cf=ci=-1; gp=gf=gs=0 }
    /[0-9]+ (passed|failed|skipped|errors?|xfailed|deselected)/ && / in [0-9.]+s/ {
      py=1; pp=grab($0,"[0-9]+ passed"); pf=grab($0,"[0-9]+ failed"); pe=grab($0,"[0-9]+ errors?")
      ps=add(grab($0,"[0-9]+ skipped"), grab($0,"[0-9]+ xfailed"))
    }
    /^Ran [0-9]+ tests? in/ { ut=1; ur=grab($0,"Ran [0-9]+") }
    /^(OK|FAILED)( \(|$)/ { us=grab($0,"skipped=[0-9]+"); uf=grab($0,"failures=[0-9]+"); ue=grab($0,"errors=[0-9]+") }
    /^# pass +[0-9]+/ { tap=1; tp=grab($0,"[0-9]+") }
    /^# fail +[0-9]+/ { tf=grab($0,"[0-9]+") }
    /^# (skipped|skip) +[0-9]+/ { ts=grab($0,"[0-9]+") }
    /^ *ok [0-9]+ .*# (SKIP|skip)/ { tskip++ }
    /^Tests: / { jest=1; jp=grab($0,"[0-9]+ passed"); jf=grab($0,"[0-9]+ failed"); js=grab($0,"[0-9]+ skipped") }
    /^ *Tests +[0-9]+ / { vit=1; vp=grab($0,"[0-9]+ passed"); vf=grab($0,"[0-9]+ failed"); vs=grab($0,"[0-9]+ skipped") }
    /^ *--- PASS:/ { go=1; gp++ } /^ *--- FAIL:/ { go=1; gf++ } /^ *--- SKIP:/ { go=1; gs++ }
    /^test result: / { cargo=1; cp=add(cp,grab($0,"[0-9]+ passed")); cf=add(cf,grab($0,"[0-9]+ failed")); ci=add(ci,grab($0,"[0-9]+ ignored")) }
    function out(p, f, s, r, name) {
      printf "%s %s %s %s %s\n", (p<0?"?":p), (f<0?"?":f), (s<0?"?":s), (r<0?"?":r), name; done=1
    }
    END {
      if (py)          { f=add(pf,pe); out((pp<0?0:pp), (f<0?0:f), (ps<0?0:ps), add((pp<0?0:pp),(f<0?0:f)), "pytest") }
      else if (ut)     { f=add(uf,ue); f=(f<0?0:f); s=(us<0?0:us); out(ur-f-s, f, s, ur, "unittest") }
      else if (tap)    { s=(ts<0?tskip:ts); out(tp, (tf<0?0:tf), s, add(tp,(tf<0?0:tf)), "tap") }
      else if (jest)   { out((jp<0?0:jp), (jf<0?0:jf), (js<0?0:js), add((jp<0?0:jp),(jf<0?0:jf)), "jest") }
      else if (vit)    { out((vp<0?0:vp), (vf<0?0:vf), (vs<0?0:vs), add((vp<0?0:vp),(vf<0?0:vf)), "vitest") }
      else if (cargo)  { out(cp, cf, ci, add(cp,cf), "cargo") }
      else if (go)     { out(gp, gf, gs, gp+gf, "go") }
      if (!done) print "? ? ? ? unknown"
    }' "$1"
}

# Failing-test identifiers, one per line (heuristic, same runners as parse_counts).
failures_of() {
  awk '
    /^FAILED / { s=$0; sub(/^FAILED /,"",s); sub(/ - .*$/,"",s); print "pytest:" s; next }
    /^ERROR / && /::/ { s=$0; sub(/^ERROR /,"",s); sub(/ - .*$/,"",s); print "pytest:" s; next }
    /^(FAIL|ERROR): / { s=$0; sub(/^(FAIL|ERROR): /,"",s); print "unittest:" s; next }
    /^ *not ok [0-9]+/ && !/# (TODO|todo|SKIP|skip)/ { s=$0; sub(/^ *not ok [0-9]+ *(- )?/,"",s); print "tap:" s; next }
    /^ *--- FAIL: / { s=$0; sub(/^ *--- FAIL: /,"",s); sub(/ \(.*$/,"",s); print "go:" s; next }
    /^test .* \.\.\. FAILED$/ { s=$0; sub(/^test /,"",s); sub(/ \.\.\. FAILED$/,"",s); print "cargo:" s; next }
  ' "$1" | sort -u
}

# ---------------------------------------------------------------- inputs outside the candidate

# Git-ignored files and folders that tests could read but the candidate doesn't contain.
# Dependency folders and well-known caches are left out; everything else counts, including
# generated files, local settings and in-place build outputs.
CACHE_RE='(^|/)(__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache|\.tox|\.nox|\.eggs|htmlcov|\.nyc_output|\.cache|\.parcel-cache|\.turbo|\.gradle|\.idea|\.vscode|target)(/|$)|(^|/)[^/]*\.egg-info(/|$)|\.py[co]$|(^|/)\.coverage[^/]*$|(^|/)\.DS_Store$|\.log$|\.sw[a-p]$'
ignored_inputs() {
  git ls-files --others --ignored --exclude-standard --directory 2>/dev/null |
    grep -vE "^($O|node_modules|\.venv|venv)(/|$)" | grep -vE "$CACHE_RE" | LC_ALL=C sort
}

# Files in dependency folders or git-ignored inputs (the recorded list and the current one) added
# or modified after a stamp (by modification time; caches excluded). Prints up to three.
changed_since() {  # stamp file
  local roots=() d p
  for d in $DEP_DIRS; do [ -e "$d" ] && roots+=("$d"); done
  while IFS= read -r p; do p=${p%/}; [ -n "$p" ] && [ -e "$p" ] && roots+=("$p"); done \
    < <({ cat "$O/ignored-inputs" 2>/dev/null; ignored_inputs; } | LC_ALL=C sort -u)
  [ ${#roots[@]} -gt 0 ] || return 0
  find "${roots[@]}" \( -name __pycache__ -o -path '*node_modules/.cache' -o -path '*node_modules/.vite' \) -prune \
    -o -type f -newer "$1" -print 2>/dev/null | head -3
}

# ---------------------------------------------------------------- offline enforcement

offline_method() {
  case "$(uname -s)" in
    Linux)
      if unshare -cn true 2>/dev/null; then echo "unshare -cn"
      elif unshare -rn true 2>/dev/null; then echo "unshare -rn"; fi ;;
    Darwin)
      if command -v sandbox-exec >/dev/null 2>&1 &&
         sandbox-exec -p '(version 1)(allow default)(deny network*)' /usr/bin/true 2>/dev/null; then
        echo "sandbox-exec"
      fi ;;
  esac
}

wrap_offline() {  # method, then the command
  local m=$1; shift
  case "$m" in
    "unshare -cn") unshare -cn "$@" ;;
    "unshare -rn") unshare -rn "$@" ;;
    sandbox-exec) sandbox-exec -p '(version 1)(allow default)(deny network*)' "$@" ;;
    *) return 99 ;;
  esac
}

# Proves the wrapper blocks a loopback connection that works without it. Prints exactly
# "verified", or "unverified: <why>" or "FAILED: <why>". ORCH_TEST_PROBE_RESULT can force a
# non-verified outcome for the helper's own tests; it can never force "verified".
probe_offline() {
  local m=$1 dir port i pid
  case "${ORCH_TEST_PROBE_RESULT:-}" in "unverified: "*|"FAILED: "*) echo "$ORCH_TEST_PROBE_RESULT"; return ;; esac
  dir=$(mktemp -d "${TMPDIR:-/tmp}/orch-probe.XXXXXX") || { echo "unverified: mktemp failed"; return; }
  if command -v python3 >/dev/null 2>&1; then
    python3 -c 'import socket,sys,time
s=socket.socket(); s.bind(("127.0.0.1",0)); s.listen(5); s.settimeout(8)
open(sys.argv[1],"w").write(str(s.getsockname()[1]))
end=time.time()+8
while time.time()<end:
    try: c,_=s.accept(); c.close()
    except Exception: break' "$dir/port" 2>/dev/null &
    pid=$!
  elif command -v node >/dev/null 2>&1; then
    node -e 'const s=require("net").createServer(c=>c.end()).listen(0,"127.0.0.1",()=>{require("fs").writeFileSync(process.argv[1],String(s.address().port))});setTimeout(()=>process.exit(0),8000)' "$dir/port" 2>/dev/null &
    pid=$!
  else
    rm -rf "$dir"; echo "unverified: no python3 or node to run the probe listener"; return
  fi
  i=0; while [ ! -s "$dir/port" ] && [ $i -lt 50 ]; do sleep 0.1; i=$((i + 1)); done
  port=$(cat "$dir/port" 2>/dev/null)
  if [ -z "$port" ]; then kill "$pid" 2>/dev/null; rm -rf "$dir"; echo "unverified: probe listener didn't start"; return; fi
  if ! bash -c "exec 3<>/dev/tcp/127.0.0.1/$port" 2>/dev/null; then
    kill "$pid" 2>/dev/null; rm -rf "$dir"; echo "unverified: this bash can't open /dev/tcp connections"; return
  fi
  if wrap_offline "$m" bash -c "exec 3<>/dev/tcp/127.0.0.1/$port" 2>/dev/null; then
    kill "$pid" 2>/dev/null; rm -rf "$dir"; echo "FAILED: a loopback connection succeeded inside '$m'"; return
  fi
  kill "$pid" 2>/dev/null; rm -rf "$dir"; echo "verified"
}

# Sets OFFLINE_M and OFFLINE_NOTE, or exits 5 unless network isolation is enforced and the
# probe result is exactly "verified". An unavailable, inconclusive or failed probe never passes.
offline_or_die() {
  OFFLINE_M=$(offline_method)
  [ -n "$OFFLINE_M" ] || { echo "orch.sh: --offline can't be enforced on this host (no usable 'unshare -n' or 'sandbox-exec'). Run in a sandbox that blocks network (a container with --network none, or the host's sandboxed shell), or drop --offline and report the run as NOT network-isolated." >&2; exit 5; }
  local v; v=$(probe_offline "$OFFLINE_M")
  if [ "$v" != verified ]; then
    echo "orch.sh: --offline refused: isolation via '$OFFLINE_M' couldn't be proven ($v). Nothing was run. Use a sandbox that blocks network, or drop --offline and report the run as NOT network-isolated." >&2
    exit 5
  fi
  OFFLINE_NOTE="network isolated ($OFFLINE_M, verified by loopback probe)"
}

# ---------------------------------------------------------------- command evidence

# The identity of a checkout: HEAD, the index, per-file flags (assume-unchanged, skip-worktree)
# and its status (tracked changes and untracked files that aren't ignored).
co_state() {
  printf 'HEAD %s\n' "$(git -C "$1" rev-parse HEAD 2>/dev/null)"
  printf 'index %s\n' "$(git -C "$1" ls-files -s 2>/dev/null | git hash-object --stdin)"
  printf 'flags %s\n' "$(git -C "$1" ls-files -v 2>/dev/null | grep -v '^H ' | git hash-object --stdin)"
  git -C "$1" status --porcelain --untracked-files=normal -- . ":(exclude)$O" 2>/dev/null
}
# What changed between two co_state outputs, one line per kind of change.
co_diff() {
  [ "$(printf '%s\n' "$1" | sed -n 1p)" = "$(printf '%s\n' "$2" | sed -n 1p)" ] || echo "HEAD moved"
  [ "$(printf '%s\n' "$1" | sed -n 2p)" = "$(printf '%s\n' "$2" | sed -n 2p)" ] || echo "the index changed"
  [ "$(printf '%s\n' "$1" | sed -n 3p)" = "$(printf '%s\n' "$2" | sed -n 3p)" ] || echo "file flags changed (assume-unchanged or skip-worktree)"
  printf '%s\n' "$2" | sed -n '4,$p'
}

# run_capture <kind> <label> <compare-baseline 0|1> <offline method or -> <workdir> -- cmd...
# Sets RC and STATUS; appends an evidence row. The row names the checkout the command ran in, as
# it was before the command; the command is void if it changed that checkout, the main one or
# the environment fingerprint while running.
run_capture() {
  local kind=$1 label=$2 cmpbase=$3 om=$4 wd=$5; shift 5; [ "${1:-}" = "--" ] && shift
  local seq log t0 t1 counts new cur head tree fp0 fp1 wd0 wd1 m0 m1 moved=""
  seq=$(next_seq); mkdir -p "$O/logs" "$O/stamps"; log="$O/logs/$seq-$label.log"
  head=$(git -C "$wd" rev-parse HEAD); tree=$(git -C "$wd" rev-parse 'HEAD^{tree}')
  fp0=$(env_fp); wd0=$(co_state "$wd"); [ "$wd" = "$ROOT" ] || m0=$(co_state "$ROOT")
  t0=$(date +%s)
  if [ "$om" = "-" ]; then ( cd "$wd" && "$@" ) > "$log" 2>&1
  else ( cd "$wd" && wrap_offline "$om" "$@" ) > "$log" 2>&1; fi
  RC=$?
  t1=$(date +%s)
  touch "$O/stamps/$seq"
  fp1=$(env_fp); wd1=$(co_state "$wd")
  if [ "$wd1" != "$wd0" ] || [ -n "$(printf '%s\n' "$wd1" | sed -n '4,$p')" ]; then moved=$(co_diff "$wd0" "$wd1"); fi
  if [ "$wd" != "$ROOT" ]; then
    m1=$(co_state "$ROOT")
    [ "$m1" = "$m0" ] || moved="$moved${moved:+$NL}main checkout: $(co_diff "$m0" "$m1" | tr '\n' ' ')"
  fi
  counts=$(parse_counts "$log")
  STATUS=pass; NEWFAIL=""
  if [ $RC -ne 0 ]; then
    STATUS=fail
    if [ "$cmpbase" = 1 ] && [ -f "$O/baseline/failures.txt" ]; then
      cur=$(failures_of "$log")
      new=$(printf '%s\n' "$cur" | grep -v '^$' | sort -u | comm -23 - "$O/baseline/failures.txt")
      if [ -n "$cur" ] && [ -z "$new" ]; then STATUS=known-failures; else NEWFAIL=${new:-"(unidentified: exit $RC)"}; fi
    fi
  fi
  if [ -n "$moved" ]; then STATUS=dirty-after
  elif [ "$fp1" != "$fp0" ]; then STATUS=env-changed; fi
  local net=-; [ "$om" = "-" ] || net="offline-verified:$om"
  ev_append "$seq" "$(now)" "$kind" "$label" "$head" "$tree" \
    "$RC" "$STATUS" "$((t1 - t0))" "$fp1" "$(echo "$counts" | tr ' ' '/')" "$log" "$(show_cmd "$@")" "$net" "${ROLE:--}"
  echo "== $kind '$label': exit $RC, $STATUS, $((t1 - t0))s, counts passed/failed/skipped/ran/runner = $(echo "$counts" | tr ' ' '/')"
  tail -12 "$log" | sed 's/^/  | /'
  echo "  log: $log"
  if [ -n "$NEWFAIL" ]; then echo "  new failures (not in the baseline):"; printf '%s\n' "$NEWFAIL" | head -20 | sed 's/^/    /'; fi
  if [ "$STATUS" = known-failures ]; then echo "  every failure was already failing at BASE (see .orchestrator/baseline/failures.txt): disclose them"; fi
  if [ "$STATUS" = dirty-after ]; then
    echo "  DIRTY AFTER: the command changed the checkout it ran in, so this evidence is void:"; printf '%s\n' "$moved" | head -20 | sed 's/^/    /'
    echo "  Files a setup step generates on purpose must be git-ignored (orch.sh ignore <pattern>); source and tests must not change."
  fi
  if [ "$STATUS" = env-changed ]; then echo "  ENVIRONMENT CHANGED while it ran (fingerprint $fp0 -> $fp1), so it isn't clear which environment it tested: run it again"; fi
}

# ---------------------------------------------------------------- test-change audit

is_test_path() {
  case "$1" in
    */test/*|test/*|*/tests/*|tests/*|*/__tests__/*|__tests__/*|*/spec/*|spec/*|*/specs/*|specs/*) return 0 ;;
  esac
  case "${1##*/}" in
    test_*.py|*_test.py|conftest.py|*_test.go|*.test.*|*.spec.*|*_spec.rb|*Test.java|*Tests.java|*Test.kt|*Tests.cs) return 0 ;;
  esac
  return 1
}
is_runner_config() {
  case "${1##*/}" in
    pytest.ini|tox.ini|setup.cfg|pyproject.toml|conftest.py|noxfile.py|package.json|Makefile|.mocharc*|mocha.opts|.nycrc*|ava.config.*|jest.config.*|vitest.config.*|vite.config.*|karma.conf.*|playwright.config.*|cypress.config.*|phpunit.xml*|Cargo.toml|.github) return 0 ;;
  esac
  case "$1" in .github/workflows/*) return 0 ;; esac
  return 1
}
is_fixture() {
  case "$1" in
    */__snapshots__/*|*.snap|*/fixtures/*|fixtures/*|*/fixture/*|*/testdata/*|testdata/*|*/test-data/*) return 0 ;;
  esac
  return 1
}
approved() {  # key -> prints the reason and returns 0 when approved
  [ -f "$O/approved-test-changes" ] || return 1
  awk -v p="$1" '$1 == p { $1=""; sub(/^ +/,""); print ($0 == "" ? "approved" : $0); found=1; exit } END { exit !found }' "$O/approved-test-changes"
}
# Approval keys bind an approval to one version of a file, or to one exact count movement,
# so a later, different change isn't covered by an earlier reason.
blob_key() { local b; b=$(git rev-parse -q --verify "$1:$2" 2>/dev/null) && echo "$2@$(echo "$b" | cut -c1-12)" || echo "$2@deleted"; }
SKIP_RE='@(unittest\.)?skip|pytest\.mark\.(skip|xfail)|pytest\.(skip|xfail)\(|skipIf|skipUnless|skipTest\(|SkipTest([^A-Za-z0-9_]|$)|expectedFailure|__test__ *= *False|\.skip\(|\.only\(|\.todo\(|(^|[^A-Za-z0-9_.])(xit|xdescribe|xtest|fit|fdescribe|pending)\(|skip *: *(true|[^,}]*[A-Za-z"'"'"'])|t\.Skip|@Disabled|@Ignore|#\[ignore\]'

# Prints findings; sets UNAPPROVED to the number of flags that aren't approved.
audit_tests() {
  local base=$1 to=$2 st path added deleted why r n=0 u=0
  UNAPPROVED=0
  echo "== test-change audit, $base..${to:0:12}"
  while IFS=$'\t' read -r st path; do
    [ -z "$path" ] && continue
    why=""
    if git cat-file -e "$base:$path" 2>/dev/null; then
      if is_test_path "$path"; then
        if [ "$st" = D ]; then why="existing test file deleted"
        else
          deleted=$(git diff --no-renames "$base" "$to" -- "$path" | grep '^-' | grep -v '^---')
          added=$(git diff --no-renames "$base" "$to" -- "$path" | grep '^+' | grep -v '^+++' | grep -E "$SKIP_RE")
          [ -n "$deleted" ] && why="$(printf '%s' "$deleted" | grep -c .) line(s) deleted or changed"
          [ -n "$added" ] && why="${why:+$why; }skip/only/xfail marker added"
        fi
      fi
      if [ -z "$why" ] && is_runner_config "$path"; then why="test runner or discovery configuration changed"; fi
      if [ -z "$why" ] && is_fixture "$path"; then why="existing fixture or snapshot changed"; fi
    elif is_test_path "$path" && git show "$to:$path" 2>/dev/null | grep -qE "$SKIP_RE"; then
      why="new test file contains skip/only/xfail markers"
    fi
    [ -z "$why" ] && continue
    n=$((n + 1))
    if r=$(approved "$(blob_key "$to" "$path")"); then echo "  approved  $path: $why ($r)"
    else u=$((u + 1)); echo "  FLAG      $path: $why"
      git diff --no-renames "$base" "$to" -- "$path" | grep -E '^[-+]' | grep -vE '^(\+\+\+|---)' | head -8 | sed 's/^/              /'
      if approved "$path" >/dev/null || grep -q "^$path@" "$O/approved-test-changes" 2>/dev/null; then
        echo "              (an earlier approval doesn't cover this version: 'orch.sh approve $path <reason>')"
      fi
    fi
  done < <(git diff --no-renames --name-status "$base" "$to")
  # Counts against the baseline, from the latest check on this candidate.
  local bc cc
  bc=$(cat "$O/baseline/counts" 2>/dev/null)
  cc=$(awk -F'\t' -v c="$(cand commit)" '$3=="check" && $5==c { x=$11 } END { print x }' "$EV" 2>/dev/null | tr '/' ' ')
  if [ -n "$bc" ] && [ -n "$cc" ]; then
    set -- $bc; local bs=$3 br=$4 brn=$5
    set -- $cc; local cs=$3 cr=$4 crn=$5
    if [ "$brn" = unknown ] || [ "$crn" = unknown ] || [ "$bs" = "?" ] || [ "$cs" = "?" ]; then
      echo "  counts: the runner's summary couldn't be read, so skipped/executed changes weren't measured"
    else
      if [ "$cs" -gt "$bs" ]; then n=$((n + 1))
        if r=$(approved "count:skipped=$bs->$cs"); then echo "  approved  skipped tests rose from $bs at BASE to $cs ($r)"
        else u=$((u + 1)); echo "  FLAG      skipped tests rose from $bs at BASE to $cs"; fi
      fi
      if [ "$cr" -lt "$br" ]; then n=$((n + 1))
        if r=$(approved "count:executed=$br->$cr"); then echo "  approved  executed tests fell from $br at BASE to $cr ($r)"
        else u=$((u + 1)); echo "  FLAG      executed tests fell from $br at BASE to $cr"; fi
      fi
    fi
  elif [ -z "$bc" ]; then echo "  counts: no baseline recorded (start with '-- <test command>'), so skipped/executed changes weren't measured"
  fi
  [ $n -eq 0 ] && echo "  OK: no changes to existing tests, runner configuration or fixtures"
  [ $u -gt 0 ] && echo "  $u unapproved flag(s). A flag is a signal to review, not proof: approve a deliberate change with 'orch.sh approve <path|count:skipped|count:executed> <reason>' (bound to this exact version or count), and revert the rest."
  UNAPPROVED=$u
}

# ---------------------------------------------------------------- dependencies

cow_copy() {
  case "$(uname -s)" in
    Darwin) cp -Rc "$1" "$2" 2>/dev/null || { rm -rf "$2"; cp -R "$1" "$2"; } ;;
    *) cp -R --reflink=auto "$1" "$2" 2>/dev/null || { rm -rf "$2"; cp -R "$1" "$2"; } ;;
  esac
}
# Follows a chain of links, resolving each hop physically. Sets FIRST (where the first hop points)
# and END (where the chain ends: an existing path, or where a dangling link points). Returns 1 on
# a cycle.
link_end() {
  local p=$1 t td d n=0
  FIRST=""; END=""
  while [ -L "$p" ]; do
    n=$((n + 1)); [ $n -le 40 ] || return 1
    t=$(readlink "$p") || return 1
    case "$t" in /*) ;; *) t="${p%/*}/$t" ;; esac
    td=${t%/*}; [ -n "$td" ] || td=/
    if d=$(cd "$td" 2>/dev/null && pwd -P); then p="${d%/}/${t##*/}"; else p=$t; [ -n "$FIRST" ] || FIRST=$p; END=$p; return 0; fi
    [ -n "$FIRST" ] || FIRST=$p
  done
  [ -d "$p" ] && p=$(cd "$p" && pwd -P)
  END=$p
}

# A copied dependency folder can still contain links, or chains of links, that end in the main
# checkout, and a copied venv's launchers name the original venv. Each such link is re-pointed to
# the copy's own counterpart when there is one, or what it ends at is copied; the folder is
# scanned again until no link ends in the main checkout. A link cycle, a link to the checkout's
# root, or a chain that still leads back after 8 passes is refused (returns 1). Links to places
# outside the checkout are reported: writes through them are shared.
isolate_copy() {  # copied dependency dir, destination checkout root
  local dd=$1 droot rootp l i rel end pass=0 repointed=0 copied=0 outside example any f
  local tl te tf
  droot=$(cd "$2" && pwd -P) || return 1; rootp=$(cd "$ROOT" && pwd -P) || return 1
  while :; do
    pass=$((pass + 1)); tl=(); te=(); tf=(); outside=0; example=""
    while IFS= read -r l; do
      link_end "$l" || { echo "  REFUSED: ${l#"$droot"/} is part of a link cycle, so where writes through it go can't be settled"; return 1; }
      case "$END" in
        "$droot"|"$droot"/*) ;;
        "$rootp") echo "  REFUSED: ${l#"$droot"/} leads to the main checkout's root"; return 1 ;;
        "$rootp"/*) tl+=("$l"); te+=("$END"); tf+=("$FIRST") ;;
        *) case "$l" in */bin/python*|*/bin/node*) ;; *) outside=$((outside + 1)); [ -n "$example" ] || example="${l#"$droot"/} -> $END" ;; esac ;;
      esac
    done < <(find "$dd" -type l 2>/dev/null)
    [ ${#tl[@]} -gt 0 ] || break
    [ $pass -le 8 ] || { echo "  REFUSED: links in ${dd##*/} still lead into the main checkout after 8 passes (e.g. ${tl[0]#"$droot"/} -> ${te[0]})"; return 1; }
    # Fix the links whose first hop leaves the copy; links that reach them through the copy follow.
    any=0; for i in "${!tl[@]}"; do case "${tf[$i]}" in "$droot"|"$droot"/*) ;; *) any=1 ;; esac; done
    for i in "${!tl[@]}"; do
      l=${tl[$i]}; end=${te[$i]}; rel=${end#"$rootp"/}
      if [ $any = 1 ]; then case "${tf[$i]}" in "$droot"|"$droot"/*) continue ;; esac; fi
      if { [ -e "$droot/$rel" ] || [ -L "$droot/$rel" ]; } && link_end "$droot/$rel" && case "$END" in "$droot"|"$droot"/*) true ;; *) false ;; esac; then
        ln -sfn "$droot/$rel" "$l"; repointed=$((repointed + 1))
      elif [ -e "$end" ]; then rm -f "$l"; cow_copy "$end" "$l"; copied=$((copied + 1))
      else ln -sfn "$droot/$rel" "$l"; repointed=$((repointed + 1)); fi
    done
  done
  [ $((repointed + copied)) -gt 0 ] && echo "  re-pointed $repointed and copied the targets of $copied link(s) in ${dd##*/} that led back into the main checkout"
  [ $outside -gt 0 ] && echo "  NOTE: $outside link(s) in ${dd##*/} point outside the checkout (e.g. $example): writes through them are shared"
  for f in "$dd"/bin/*; do
    [ -f "$f" ] && [ ! -L "$f" ] || continue
    case "${f##*/}" in activate*) ;; *) [ "$(head -c 2 "$f" 2>/dev/null)" = "#!" ] || continue ;; esac
    grep -qF "$ROOT/${dd##*/}" "$f" 2>/dev/null || continue
    sed "s$(printf '\001')$ROOT/${dd##*/}$(printf '\001')$droot/${dd##*/}$(printf '\001')g" "$f" > "$f.orch-tmp" && cat "$f.orch-tmp" > "$f"; rm -f "$f.orch-tmp"
  done
}

place_deps() {  # dest mode
  local dest=$1 mode=$2 d ex
  ex=$(git rev-parse --git-path info/exclude); case "$ex" in /*) ;; *) ex="$ROOT/$ex" ;; esac
  mkdir -p "$(dirname "$ex")"
  for d in $DEP_DIRS; do
    [ -e "$ROOT/$d" ] && [ ! -e "$dest/$d" ] || continue
    case "$mode" in
      none) continue ;;
      link) ln -s "$ROOT/$d" "$dest/$d"; echo "  WARNING: $d is a writable link to the main tree's; writes there change it for everyone" ;;
      *) cow_copy "$ROOT/$d" "$dest/$d"; echo "  copied $d"
         if ! isolate_copy "$dest/$d" "$dest"; then
           rm -rf "$dest/$d"
           echo "  $d was not placed. Use --deps none and install it in the checkout, or --deps link to share it, writes included."
           return 1
         fi
         if [ "$d" != node_modules ] && grep -rlsF "$ROOT" "$dest/$d"/lib/python*/site-packages/*.pth "$dest/$d"/lib/python*/site-packages/__editable__* >/dev/null 2>&1; then
           echo "  WARNING: $d has an editable install pointing at the main checkout: imports load the main tree's source. Run with PYTHONPATH set to the worktree's source, or reinstall there."
         fi ;;
    esac
    grep -qx "/$d" "$ex" 2>/dev/null || echo "/$d" >> "$ex"
  done
}

# ---------------------------------------------------------------- commands

cmd_start() {
  local name="" offline=0 left st from base rid
  while [ $# -gt 0 ] && [ "$1" != "--" ]; do
    case "$1" in --offline) offline=1 ;; -*) die "unknown option $1" ;; *) [ -z "$name" ] && name=$1 || die "one name only" ;; esac
    shift
  done
  [ -n "$name" ] || die "usage: orch.sh start <name> [--offline] [-- <test command>]"
  if [ -f "$O/manifest" ]; then
    st=$(mf_get status)
    case "$st" in
      done|partial|blocked)
        rid=$(mf_get run_id); rid=${rid:-earlier}
        [ -d "$O/worktrees" ] && [ -n "$(ls -A "$O/worktrees" 2>/dev/null)" ] && die "the finished run still has worktrees in $O/worktrees; finish or remove them first"
        mkdir -p "$O/runs/$rid"
        for e in "$O"/* "$O"/.[!.]*; do [ -e "$e" ] || continue; case "${e##*/}" in runs|worktrees) ;; *) mv "$e" "$O/runs/$rid/" ;; esac; done
        echo "archived the finished run ($st) to $O/runs/$rid/" ;;
      *)
        echo "EARLIER RUN FOUND (status: ${st:-unknown}, branch: $(git rev-parse --abbrev-ref HEAD)). Read it with 'orch.sh status'."
        echo "Same request and its branch unmoved: resume from where its evidence stops. Otherwise ask the user which run to keep."
        cmd_status_inner; exit 3 ;;
    esac
  elif [ -f "$O/plan.md" ]; then
    echo "EARLIER RUN FOUND: $O/plan.md exists from an older version of this skill. Read it; resume or ask."; exit 3
  fi
  left=$(leftovers)
  if [ -n "$left" ]; then
    echo "UNCOMMITTED CHANGES: ask the user whether to commit them, stash them, or build on top."
    printf '%s\n' "$left"; exit 4
  fi
  ensure_ignored
  from=$(git rev-parse --abbrev-ref HEAD)
  git show-ref --verify --quiet "refs/heads/orch/$name" && die "branch orch/$name already exists: resume it or choose another name"
  git checkout -q -b "orch/$name" || die "could not create branch orch/$name"
  base=$(git rev-parse HEAD)
  mkdir -p "$O"
  : > "$O/manifest"
  mf_set run_id "$(date -u +%Y%m%dT%H%M%SZ)-$name"; mf_set name "$name"; mf_set branch "orch/$name"
  mf_set from "$from"; mf_set base "$base"; mf_set status active; mf_set created "$(now)"
  mf_set repair_cycles 0; mf_set requires ""
  echo "$base" > "$O/base"
  echo "run started: branch orch/$name from $from at BASE=$base"
  if [ "${1:-}" = "--" ]; then
    shift
    [ $# -gt 0 ] || die "no test command after --"
    local om="-"
    if [ $offline = 1 ]; then offline_or_die; om=$OFFLINE_M; echo "baseline: $OFFLINE_NOTE"; fi
    mkdir -p "$O/baseline"
    run_capture baseline baseline 0 "$om" "$ROOT" -- "$@"
    failures_of "$(awk -F'\t' 'END{print $12}' "$EV")" > "$O/baseline/failures.txt"
    parse_counts "$(awk -F'\t' 'END{print $12}' "$EV")" > "$O/baseline/counts"
    mf_set baseline_exit "$RC"
    [ -s "$O/baseline/failures.txt" ] && { echo "  known failures at BASE (every brief lists them):"; sed 's/^/    /' "$O/baseline/failures.txt" | head -30; }
    [ "$RC" -ne 0 ] && [ ! -s "$O/baseline/failures.txt" ] && echo "  the baseline failed but no failing tests could be identified: read the log before building"
  fi
  echo "tracked files ($(git ls-files | wc -l | tr -d ' ')):"
  git ls-files | head -100
}

cmd_status_inner() {
  echo "== manifest"; sed 's/^/  /' "$O/manifest"
  if [ -f "$O/candidate" ]; then
    local why; why=$(candidate_current) && echo "== candidate $(cand commit) (current)" || echo "== candidate $(cand commit) (STALE: $why)"
  fi
  [ -f "$EV" ] && { echo "== last evidence"; tail -6 "$EV" | awk -F'\t' '{ printf "  %s %-9s %-14s %s exit=%s %s\n", $1, $3, $4, substr($5,1,10), $7, $8 }'; }
  [ -f "$O/request.md" ] && echo "== request: $O/request.md" || echo "== request: not saved ($O/request.md)"
  return 0
}
cmd_status() { need_run; cmd_status_inner; }

cmd_require() {
  need_run; local r cur rq
  if [ "${1:-}" = check ]; then
    shift; [ $# -gt 0 ] || die "usage: orch.sh require check <id> [<id> ...]"
    rq=$(mf_get required_checks)
    for r in "$@"; do
      case "$r" in *[!A-Za-z0-9._-]*|"") die "check ids use letters, digits, '.', '_' and '-': $r" ;; esac
      case ",$rq," in *",$r,"*) ;; *) rq="${rq:+$rq,}$r" ;; esac
    done
    mf_set required_checks "$rq"; echo "required checks: $rq (each needs a passing 'orch.sh run <id> -- <command>' on the final candidate)"
    return 0
  fi
  cur=$(mf_get requires)
  for r in "$@"; do
    case "$r" in review|fresh|offline) case ",$cur," in *",$r,"*) ;; *) cur="${cur:+$cur,}$r" ;; esac ;; *) die "unknown requirement '$r' (review, fresh, offline, or: check <id>...)" ;; esac
  done
  mf_set requires "$cur"; echo "requires: ${cur:-nothing beyond a passing check}"
}

cmd_ignore() {
  [ $# -eq 1 ] || die "usage: orch.sh ignore <pattern>"
  local ex; ex=$(git rev-parse --git-path info/exclude); mkdir -p "$(dirname "$ex")"
  grep -qxF "$1" "$ex" 2>/dev/null || echo "$1" >> "$ex"
  [ -f "$O/manifest" ] && mf_set locally_ignored "$(mf_get locally_ignored) $1"
  echo "ignored locally (not committed): $1"
}

cmd_candidate() { need_run; freeze_candidate || exit 1; echo "candidate: $(cand commit) tree $(cand tree)"; }

cmd_check() {
  need_run
  local label=check om="-"
  while [ $# -gt 0 ] && [ "$1" != "--" ]; do
    case "$1" in --label) label=$2; shift ;; --offline) offline_or_die; om=$OFFLINE_M; echo "tests: $OFFLINE_NOTE" ;; *) die "unknown option $1" ;; esac; shift
  done
  [ "${1:-}" = "--" ] || die "usage: orch.sh check [--label L] [--offline] -- <test command>"
  shift; [ $# -gt 0 ] || die "no test command after --"
  freeze_candidate || exit 1
  echo "candidate: $(cand commit)"
  run_capture check "$label" 1 "$om" "$ROOT" -- "$@"
  local status=$STATUS
  ignored_inputs > "$O/ignored-inputs"
  if [ -s "$O/ignored-inputs" ]; then
    echo "  note: git-ignored files the candidate doesn't contain were present, so the tests could have read them:"
    head -8 "$O/ignored-inputs" | sed 's/^/    /'
    echo "  the gate will want a fresh-checkout run: orch.sh fresh -- <setup and tests>"
  fi
  audit_tests "$(base_rev)" "$(cand commit)"
  case "$status" in pass|known-failures) [ "$UNAPPROVED" -eq 0 ] && exit 0 ;; esac
  exit 1
}

cmd_run() {
  need_run
  [ $# -ge 1 ] || die "usage: orch.sh run <label> [--explore] [--offline] -- <command>"
  local label=$1 om="-"; shift
  case "$label" in -*|*[!A-Za-z0-9._-]*) die "labels use letters, digits, '.', '_' and '-': $label" ;; esac
  ROLE=-
  while [ $# -gt 0 ] && [ "$1" != "--" ]; do
    case "$1" in --offline) offline_or_die; om=$OFFLINE_M; echo "$OFFLINE_NOTE" ;; --explore) ROLE=explore ;; *) die "unknown option $1" ;; esac; shift
  done
  [ "${1:-}" = "--" ] || die "usage: orch.sh run <label> [--explore] [--offline] -- <command>"
  shift; [ $# -gt 0 ] || die "no command after --"
  require_current
  run_capture run "$label" 0 "$om" "$ROOT" -- "$@"
  [ "$ROLE" = explore ] && echo "  exploratory: recorded, but it doesn't count towards completion either way"
  [ "$STATUS" = pass ] && exit 0; exit 1
}

ENV_ALLOW="PATH LANG LC_ALL LC_CTYPE TERM TZ USER LOGNAME SHELL VIRTUAL_ENV JAVA_HOME GOPATH GOROOT GOFLAGS CARGO_HOME RUSTUP_HOME NVM_DIR PYENV_ROOT ASDF_DIR ASDF_DATA_DIR"

cmd_fresh() {
  need_run
  local keephome=0 keeps="" deps=copy om="-" assigns=() envs=() v tmp note label=fresh
  while [ $# -gt 0 ] && [ "$1" != "--" ]; do
    case "$1" in
      --offline) offline_or_die; om=$OFFLINE_M ;;
      --keep-home) keephome=1 ;;
      --keep) keeps="$keeps $2"; shift ;;
      --deps) deps=$2; shift ;;
      --label) label=$2; shift; case "$label" in *[!A-Za-z0-9._-]*|"") die "labels use letters, digits, '.', '_' and '-'" ;; esac ;;
      *=*) assigns+=("$1") ;;
      *) die "unknown option '$1'" ;;
    esac; shift
  done
  [ "${1:-}" = "--" ] || die "usage: orch.sh fresh [options] [VAR=value ...] -- <command>"
  shift; [ $# -gt 0 ] || die "no command after --"
  require_current
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/orch-fresh.XXXXXX") || die "mktemp failed"
  git worktree add -q --detach "$tmp/repo" "$(cand commit)" || { rm -rf "$tmp"; die "git worktree add failed"; }
  trap 'git -C "$ROOT" worktree remove --force "$tmp/repo" >/dev/null 2>&1; rm -rf "$tmp"; git -C "$ROOT" worktree prune' EXIT
  mkdir -p "$tmp/home" "$tmp/tmp"
  place_deps "$tmp/repo" "$deps" || die "fresh refused: the dependencies can't be copied without writes reaching the main checkout (see above); nothing was run"
  for v in $ENV_ALLOW $keeps; do
    if [ -n "${!v+x}" ]; then envs+=("$v=${!v}"); fi
  done
  [ $keephome = 1 ] && envs+=("HOME=$HOME") || envs+=("HOME=$tmp/home")
  envs+=("TMPDIR=$tmp/tmp")
  local secretish
  secretish=$(git ls-tree -r --name-only "$(cand commit)" | grep -E '(^|/)(\.env(\..*)?|id_rsa|id_ed25519|.*\.pem|credentials[^/]*\.json)$' | head -5)
  [ -n "$secretish" ] && { echo "  note: tracked files that look like secrets are part of the candidate, so the run can read them:"; printf '%s\n' "$secretish" | sed 's/^/    /'; }
  note="fresh checkout of $(cand commit | cut -c1-12); environment: allowlist of ${#envs[@]} variables$( [ $keephome = 1 ] && echo ', real HOME' || echo ', temporary HOME'); filesystem: NOT sandboxed"
  if [ "$om" = "-" ]; then note="$note; network: NOT isolated"; else note="$note; $OFFLINE_NOTE"; fi
  echo "$note"
  run_capture fresh "$label" 1 "$om" "$tmp/repo" -- env -i "${envs[@]}" ${assigns[@]+"${assigns[@]}"} "$@"
  case "$STATUS" in pass|known-failures) exit 0 ;; esac
  exit 1
}

cmd_tests() {
  need_run
  local to; to=$(git rev-parse HEAD)
  [ -n "$(leftovers)" ] && echo "note: the tree has uncommitted changes; this audits committed work only"
  audit_tests "$(base_rev)" "$to"
  [ "$UNAPPROVED" -eq 0 ] && exit 0; exit 1
}

cmd_diff() {
  need_run; require_current
  local c s f
  c=$(cand commit); s=$(echo "$c" | cut -c1-12)
  mkdir -p "$O/review"
  f="$O/review/candidate-$s.patch"
  git diff -U10 "$(base_rev)" "$c" -- . ":(exclude)$O" > "$f" || die "git diff failed"
  git diff --stat "$(base_rev)" "$c" -- . ":(exclude)$O" > "$O/review/candidate-$s.stat"
  ev_append "$(next_seq)" "$(now)" review-diff diff "$c" "$(cand tree)" 0 pass 0 "$(env_fp)" "" "$f" "orch.sh diff"
  echo "$ROOT/$f ($(wc -l < "$f" | tr -d ' ') lines; BASE $(base_rev | cut -c1-12)..candidate $s)"
  [ -s "$f" ] || echo "WARNING: the patch is empty: the candidate doesn't differ from BASE"
}

cmd_record() {
  need_run
  local u="usage: orch.sh record <review|recheck|manual> <pass|fail|pending> [--id <id>] [note]"
  [ $# -ge 2 ] || die "$u"
  local kind=$1 res=$2 id=""; shift 2
  case "$kind" in review|recheck|manual) ;; *) die "kind must be review, recheck or manual" ;; esac
  case "$res" in pass|fail|pending) ;; *) die "result must be pass, fail or pending" ;; esac
  if [ "${1:-}" = "--id" ]; then [ $# -ge 2 ] || die "$u"; id=$2; shift 2; fi
  case "$kind" in
    review|recheck) id=review ;;
    manual) id=${id:-$*}; [ -n "$id" ] || die "a manual check needs an id: record manual <result> --id <id> [note]" ;;
  esac
  id=$(printf '%s' "$id" | tr '\t\n' '  ')
  require_current
  local seq; seq=$(next_seq); mkdir -p "$O/stamps"; touch "$O/stamps/$seq"
  ev_append "$seq" "$(now)" "$kind" "$id" "$(cand commit)" "$(cand tree)" - "$res" 0 "$(env_fp)" "" "" "record: $(printf '%s' "$*" | tr '\t\n' '  ')"
  echo "recorded $kind '$id' $res for candidate $(cand commit | cut -c1-12)"
}

cmd_approve() {
  need_run
  [ $# -ge 2 ] || die "usage: orch.sh approve <path|count:skipped|count:executed> <reason>"
  local what=$1 key bc cc reason; shift
  reason=$(printf '%s' "$*" | tr '\t\n' '  ')
  case "$what" in
    count:skipped|count:executed)
      require_current
      bc=$(cat "$O/baseline/counts" 2>/dev/null)
      cc=$(awk -F'\t' -v c="$(cand commit)" '$3=="check" && $5==c { x=$11 } END { print x }' "$EV" 2>/dev/null | tr '/' ' ')
      [ -n "$bc" ] && [ -n "$cc" ] || die "approving a count needs a baseline and a check of this candidate first"
      set -- $bc; local bs=$3 br=$4; set -- $cc; local cs=$3 cr=$4
      if [ "$what" = count:skipped ]; then key="count:skipped=$bs->$cs"; else key="count:executed=$br->$cr"; fi ;;
    *) git cat-file -e "HEAD:$what" 2>/dev/null || git cat-file -e "$(base_rev):$what" 2>/dev/null || die "$what is neither in HEAD nor at BASE"
       key=$(blob_key HEAD "$what") ;;
  esac
  printf '%s  %s\n' "$key" "$reason" >> "$O/approved-test-changes"
  echo "approved $key: $reason"
}

# A waiver disposes of a check that no longer applies to this candidate, with a reason the
# report must carry. The test check, a required review and any required check can't be waived.
cmd_waive() {
  need_run
  [ $# -ge 2 ] || die "usage: orch.sh waive <run:<label>|manual:<id>|fresh[:<label>]> <reason>"
  local id=$1; shift
  case "$id" in
    run:?*) case ",$(mf_get required_checks)," in *",${id#run:},"*) die "${id#run:} is a required check; it can't be waived. Finish partial if it can't pass." ;; esac ;;
    manual:?*) ;;
    fresh|fresh:?*) case ",$(mf_get requires)," in *,fresh,*|*,offline,*) die "a fresh or offline run is required for this run; it can't be waived" ;; esac ;;
    review) case ",$(mf_get requires)," in *,review,*) die "a review is required for this run; it can't be waived" ;; esac ;;
    *) die "only run:, manual:, fresh and an unrequired review can be waived; the test check can't" ;;
  esac
  require_current
  ev_append "$(next_seq)" "$(now)" waive "$id" "$(cand commit)" "$(cand tree)" - waived 0 "$(env_fp)" "" "" "waive: $(printf '%s' "$*" | tr '\t\n' '  ')"
  echo "waived $id for candidate $(cand commit | cut -c1-12): $*"
}

cmd_repair() {
  need_run
  local n max
  n=$(( $(mf_get repair_cycles || echo 0) + 1 ))
  max=${ORCH_MAX_REPAIR_CYCLES:-$(mf_get max_repair_cycles)}; max=${max:-2}
  if [ "$n" -gt "$max" ]; then
    echo "REPAIR BUDGET SPENT: $max whole repair cycle(s) used. Stop: diagnose the cause (missing requirement, environment, capability, flaky test, wrong fix) and finish as partial or blocked, or ask the user."
    exit 1
  fi
  mf_set repair_cycles "$n"
  ev_append "$(next_seq)" "$(now)" repair "cycle-$n" "$(git rev-parse HEAD)" "$(git rev-parse 'HEAD^{tree}')" - open 0 "$(env_fp)" "" "" "$(show_cmd "$@")"
  echo "repair cycle $n of $max opened: $*"
}

# One rule for every piece of evidence. A check's identity is its kind and label ("check:unit",
# "run:format", "fresh:fresh", "manual:<id>"; reviews and re-checks share "review"). Only its latest
# result counts, and that result must be for the current candidate and passing. Exploratory runs
# never count. A waiver, with its reason, disposes of an identity that isn't required.
# Prints problems (one per line). Returns 0 when there are none.
gate_problems() {
  local why c t fp req rq saved now_inputs out seq id changed
  why=$(candidate_current) || { echo "candidate: $why"; return 1; }
  c=$(cand commit); t=$(cand tree); fp=$(env_fp)
  req=$(mf_get requires); rq=$(mf_get required_checks)
  saved=$(cat "$O/ignored-inputs" 2>/dev/null | tr '\n' ' ')
  [ -f "$EV" ] || { echo "no evidence recorded: run orch.sh check -- <tests>"; return 0; }
  # Command and manual evidence is tied to the environment it ran in as well as the candidate: its
  # fingerprint must match the current one, and dependency folders and ignored inputs must not
  # have changed after it ran. Reviews are tied to the candidate only: they judge the code against
  # the request, and the environment is covered by the command evidence.
  out=$(awk -F'\t' -v c="$c" -v t="$t" -v fp="$fp" -v req=",$req," -v rq=",$rq," -v inputs="$saved" '
    function ident(k, l) { return (k == "review" || k == "recheck") ? "review" : k ":" l }
    function ok(id) { return ls[id] == "pass" || (ls[id] == "known-failures" && id ~ /^(check|fresh):/) }
    function cur(id) { return lc[id] == c && lt[id] == t }
    function required(id,   x) {
      if (id ~ /^check:/) return 1
      if (id == "review") return index(req, ",review,") > 0
      if (id ~ /^run:/) { x = substr(id, 5); return index(rq, "," x ",") > 0 }
      if (id ~ /^fresh/) return index(req, ",fresh,") > 0 || index(req, ",offline,") > 0
      return 0
    }
    NR == 1 { next }
    $3 == "baseline" || $3 == "review-diff" || $3 == "repair" { next }
    $3 == "waive" { if ($5 == c && $6 == t) waived[$4] = 1; next }
    $15 == "explore" { next }
    { id = ident($3, $4)
      if (!(id in lc)) ids[++n] = id
      lc[id] = $5; lt[id] = $6; ls[id] = $8; lq[id] = $1; le[id] = $10; lnet[id] = $14 }
    END {
      for (i = 1; i <= n; i++) {
        id = ids[i]
        if (cur(id) && ok(id)) {
          if (id ~ /^check:/) anycheck = 1
          if (id ~ /^(check|run|fresh|manual):/) {
            if (le[id] != fp) print "environment changed since " id " ran (fingerprint " le[id] " -> " fp "): run it again"
            else print "STAMP\t" lq[id] "\t" id
          }
          if (id ~ /^fresh:/) freshok = 1
          if (id ~ /^(check|fresh):/ && lnet[id] ~ /^offline-verified:/) offok = 1
          continue
        }
        if (waived[id] && !required(id)) continue
        hint = required(id) ? "" : ", or waive it with a reason if it no longer applies"
        if (!cur(id)) print id " was last recorded for an earlier candidate (" substr(lc[id], 1, 12) "): run it again for this one" hint
        else if (ls[id] == "dirty-after") print id " (" lq[id] ") changed the checkout it ran in, so it is void: run it again"
        else if (ls[id] == "env-changed") print id " (" lq[id] ") changed the environment fingerprint while running, so it is void: run it again"
        else print id " latest result (" lq[id] ") is " ls[id] ": fix it and run it again" hint
      }
      if (!anycheck) print "no passing check for this candidate: run orch.sh check -- <tests>"
      if (index(req, ",review,") && !("review" in lc)) print "review required: none recorded for this candidate"
      if (index(req, ",fresh,") && !freshok) print "fresh-checkout run required: none passing for this candidate"
      if (index(req, ",offline,") && !offok) print "offline run required: no passing check --offline or fresh --offline with verified isolation for this candidate"
      m = split(rq, r, ",")
      for (k = 1; k <= m; k++) if (r[k] != "" && !(("run:" r[k]) in lc)) print "required check " r[k] ": no result recorded (orch.sh run " r[k] " -- <command>)"
      if (inputs != "" && !freshok && !waived["fresh"] && !index(req, ",fresh,"))
        print "git-ignored files the candidate does not contain were present during the check (" inputs "): prove it works without them with orch.sh fresh -- <setup and tests>, or waive fresh with a reason if they are not inputs"
    }' "$EV")
  printf '%s\n' "$out" | grep -v '^STAMP	' | grep -v '^$'
  now_inputs=$(ignored_inputs | tr '\n' ' ')
  [ "$now_inputs" = "$saved" ] || echo "git-ignored inputs changed since the latest check (now: ${now_inputs:-none}): run check again"
  # Oldest first: once one item has no later changes, no newer item can have any.
  while IFS=$'\t' read -r _ seq id; do
    [ -n "$seq" ] || continue
    if [ ! -f "$O/stamps/$seq" ]; then echo "$id ($seq) has no timestamp (an older helper recorded it): run it again"; continue; fi
    changed=$(changed_since "$O/stamps/$seq" | tr '\n' ' ')
    [ -n "$changed" ] || break
    echo "files in dependency folders or ignored inputs changed after $id ran (e.g. $changed): run it again"
  done < <(printf '%s\n' "$out" | grep '^STAMP	' | sort -t "$(printf '\t')" -k2,2n)
  audit_tests "$(base_rev)" "$c" > "$O/.gate-audit" 2>&1
  [ "$UNAPPROVED" -eq 0 ] || echo "test-change audit: $UNAPPROVED unapproved flag(s) (orch.sh tests)"
  return 0
}

cmd_gate() {
  need_run
  local p
  p=$(gate_problems)
  if [ -z "$p" ]; then
    echo "GATE: PASS for candidate $(cand commit)"
    awk -F'\t' -v c="$(cand commit)" '$5==c && $3!="review-diff" { printf "  %-9s %-18s exit=%s %s%s %s\n", $3, $4, $7, $8, ($15=="explore" ? " (exploratory)" : ""), ($3=="waive" ? $13 : $12) }' "$EV"
    grep -q . "$O/baseline/failures.txt" 2>/dev/null && awk -F'\t' -v c="$(cand commit)" '$3=="check" && $5==c && $8=="known-failures" { f=1 } END { exit !f }' "$EV" && echo "  disclose: pre-existing failures remain (see $O/baseline/failures.txt)"
    awk -F'\t' -v c="$(cand commit)" '$3=="waive" && $5==c { f=1 } END { exit !f }' "$EV" && echo "  disclose: waived checks and their reasons, above"
    exit 0
  fi
  echo "GATE: FAIL"; printf '%s\n' "$p" | sed 's/^/  - /'
  exit 1
}

cmd_finish() {
  need_run
  [ $# -ge 1 ] || die "usage: orch.sh finish <done|partial|blocked> [note]"
  local st=$1; shift
  case "$st" in
    done) local p; p=$(gate_problems); [ -z "$p" ] || { echo "REFUSED: the gate fails, so this run isn't done:"; printf '%s\n' "$p" | sed 's/^/  - /'; echo "Fix it, or finish as partial or blocked."; exit 1; } ;;
    partial|blocked) ;;
    *) die "status must be done, partial or blocked" ;;
  esac
  local t
  for t in "$O"/worktrees/*; do
    [ -d "$t" ] || continue
    if [ -z "$(git -C "$t" status --porcelain 2>/dev/null)" ]; then ( cmd_wt_finish "${t##*/}" ) || true; else echo "kept $t: it has uncommitted changes"; fi
  done
  mf_set status "$st"; mf_set finished "$(now)"; mf_set note "$*"
  {
    echo "# Run $(mf_get run_id): $st"
    echo "- base: $(base_rev)"; echo "- candidate: $(cand commit)"; echo "- branch: $(mf_get branch)"
    echo "- repair cycles: $(mf_get repair_cycles)"; echo "- note: $*"
    echo; echo "## Evidence for the candidate"
    awk -F'\t' -v c="$(cand commit)" 'NR==1 || $5==c { print "    " $1 "  " $3 "  " $4 "  exit=" $7 "  " $8 ($15=="explore" ? " (exploratory)" : "") "  " ($3=="waive" ? $13 : $12) }' "$EV" 2>/dev/null
    [ -s "$O/approved-test-changes" ] && { echo; echo "## Approved test changes"; sed 's/^/    /' "$O/approved-test-changes"; }
  } > "$O/summary.md"
  echo "run finished: $st. Record kept: $O/manifest, $O/evidence.tsv, $O/logs/, $O/summary.md"
}

cmd_stamp() {
  local dirty; dirty=$(leftovers)
  if [ -n "$dirty" ]; then echo "main tree is not clean; commit or restore these before dispatching:" >&2; echo "$dirty" >&2; exit 1; fi
  mkdir -p "$O"; : > "$O/stamp"
  # Coarse filesystem timestamps: wait so every later write is strictly newer than the stamp.
  sleep 1
  echo "stamped $(date '+%H:%M:%S'); run 'orch.sh stray' when the workers return"
}

cmd_stray() {
  [ -f "$O/stamp" ] || die "no $O/stamp; run 'orch.sh stamp' before dispatching"
  local prune line rel files outside inside status
  prune=(-path ./.git -o -path ./.claude/worktrees -o -path "./$O/worktrees")
  while IFS= read -r line; do
    case "$line" in "worktree $ROOT/"*) rel=${line#"worktree $ROOT/"}; prune+=(-o -path "./$rel") ;; esac
  done < <(git worktree list --porcelain)
  files=$(find . \( "${prune[@]}" \) -prune -o -type f -newer "$O/stamp" -print | sed 's|^\./||' | sort)
  outside=$(printf '%s\n' "$files" | grep -v "^$O/" | grep -v '^$')
  inside=$(printf '%s\n' "$files" | grep "^$O/" | grep -v "^$O/stamp$")
  status=$(leftovers)
  [ -n "$inside" ] && { echo "written in $O/ since the stamp (fine if you wrote them; a worker's report here means it left its worktree):"; printf '%s\n' "$inside" | sed 's/^/  /'; }
  if [ -z "$outside" ] && [ -z "$status" ]; then echo "OK: nothing outside $O/ written in the main tree since the stamp"; return 0; fi
  echo "STRAY: the main tree changed while workers ran. Compare each file with the worker's branch, discard it, and log it."
  [ -n "$outside" ] && { echo "files written since the stamp:"; printf '%s\n' "$outside" | sed 's/^/  /' | head -50; }
  [ -n "$status" ] && { echo "git status:"; printf '%s\n' "$status" | sed 's/^/  /'; }
  exit 1
}

cmd_wt_add() {
  local task="" deps=copy dir
  while [ $# -gt 0 ]; do case "$1" in --deps) deps=$2; shift ;; *) task=$1 ;; esac; shift; done
  [ -n "$task" ] || die "usage: orch.sh wt-add <task> [--deps copy|none|link]"
  case "$deps" in copy|none|link) ;; *) die "--deps must be copy, none or link" ;; esac
  dir="$ROOT/$O/worktrees/$task"
  [ -e "$dir" ] && die "$dir already exists"
  ensure_ignored
  git show-ref --verify --quiet "refs/heads/orch-wt/$task" && die "branch orch-wt/$task already exists"
  mkdir -p "$(dirname "$dir")"
  git worktree add -q "$dir" -b "orch-wt/$task" HEAD || die "git worktree add failed"
  mkdir -p "$dir/$O"
  if ! place_deps "$dir" "$deps"; then
    git worktree remove --force "$dir" >/dev/null 2>&1; git branch -D "orch-wt/$task" >/dev/null 2>&1
    die "wt-add refused: the dependencies can't be copied without writes reaching the main checkout (see above); no worktree was created"
  fi
  echo "$dir"
}

cmd_wt_finish() {
  [ $# -eq 1 ] || die "usage: orch.sh wt-finish <task>"
  local task=$1 dir left
  dir="$ROOT/$O/worktrees/$task"
  [ -d "$dir" ] || die "no worktree at $dir"
  left=$(git -C "$dir" status --porcelain)
  [ -z "$left" ] || { echo "worktree has uncommitted changes; merge or discard them first:" >&2; echo "$left" >&2; exit 1; }
  if [ -d "$dir/$O" ]; then mkdir -p "$O/reports/$task"; cp -R "$dir/$O/." "$O/reports/$task/"; echo "copied reports to $O/reports/$task/"; fi
  git worktree remove --force "$dir" || die "git worktree remove failed"
  if git branch -d "orch-wt/$task" >/dev/null 2>&1; then echo "removed $dir and branch orch-wt/$task"
  else echo "removed $dir; kept branch orch-wt/$task because it isn't merged into $(git rev-parse --abbrev-ref HEAD)"; fi
}

cmd_caps() {
  local m v
  echo "host: $(uname -sm); $(bash --version | head -1 | sed 's/ (.*//'); $(git --version)"
  m=$(offline_method)
  if [ -n "$m" ]; then v=$(probe_offline "$m"); echo "offline (--offline): $m, probe: $v$( [ "$v" = verified ] && echo ' (usable)' || echo ' (refused: --offline exits 5)')"
  else echo "offline (--offline): NOT available here; runs can't be network-isolated by this helper"; fi
  case "$(uname -s)" in
    Darwin) echo "dependency copies: copy-on-write via cp -c where the filesystem supports it (APFS)" ;;
    *) echo "dependency copies: cp --reflink=auto (copy-on-write on btrfs/xfs, full copy elsewhere)" ;;
  esac
  echo "not enforced by this helper: filesystem reads outside the checkout; process limits; model or tool permissions"
}

[ $# -ge 1 ] || { usage; exit 2; }
sub=$1; shift
case "$sub" in
  start) cmd_start "$@" ;;
  status) cmd_status "$@" ;;
  require) cmd_require "$@" ;;
  ignore) cmd_ignore "$@" ;;
  finish) cmd_finish "$@" ;;
  candidate) cmd_candidate "$@" ;;
  check) cmd_check "$@" ;;
  run) cmd_run "$@" ;;
  fresh) cmd_fresh "$@" ;;
  clean-room) echo "note: clean-room is now 'fresh'. It is a fresh-checkout run, not a sandbox." >&2; cmd_fresh "$@" ;;
  tests|old-tests) cmd_tests ;;
  diff) cmd_diff ;;
  record) cmd_record "$@" ;;
  approve) cmd_approve "$@" ;;
  waive) cmd_waive "$@" ;;
  repair) cmd_repair "$@" ;;
  gate) cmd_gate ;;
  stamp) cmd_stamp ;;
  stray) cmd_stray ;;
  wt-add) cmd_wt_add "$@" ;;
  wt-finish) cmd_wt_finish "$@" ;;
  caps) cmd_caps ;;
  -h|--help|help) usage ;;
  *) usage; exit 2 ;;
esac
