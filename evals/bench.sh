#!/usr/bin/env bash
# grunt benchmark suite: chore tasks A/B + delegation-accuracy probes,
# run in parallel with a shared live log.
#
#   ./bench.sh [N] [task-filter-regex]     e.g. ./bench.sh 3
#                                               ./bench.sh 1 'commit|probe-debug'
#   PAR=8 ./bench.sh 3                     concurrency (default 6)
#
# Chore tasks run arms A (no plugin) and B (grunt via --plugin-dir), each
# followed by one follow-up turn (context-pollution metric). Probe tasks
# (should NOT delegate) run arm B only, single turn.
# Watch live: tail -f evals/work/live.log
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$ROOT/evals/work"
LIVE="$WORK/live.log"
TASKS="$ROOT/evals/tasks.json"
MODEL=${BENCH_MODEL:-claude-fable-5}
FOLLOWUP="In one sentence, what did that accomplish?"
PAR=${PAR:-6}

# ---------- per-trial worker (invoked by xargs as: bench.sh --run-one "arm|task|n") ----
if [ "${1:-}" = "--run-one" ]; then
  spec="$2"
  arm="${spec%%|*}"; rest="${spec#*|}"; task="${rest%%|*}"; n="${rest#*|}"
  tf=$(python3 -c "
import json
t = [x for x in json.load(open('$TASKS')) if x['name'] == '$task'][0]
print(t['type']); print(t['fixture']); print(t['success']); print(t['prompt'])")
  ttype=$(sed -n 1p <<<"$tf"); fixture=$(sed -n 2p <<<"$tf")
  success=$(sed -n 3p <<<"$tf"); prompt=$(sed -n 4p <<<"$tf")

  TD="$WORK/trials/$arm-$task-$n"
  REPO="$TD/repo"
  rm -rf "$TD"; mkdir -p "$REPO"
  (
    cd "$REPO"
    git init -qb main
    git config user.email eval@grunt.local
    git config user.name "grunt eval"
    python3 "$ROOT/evals/gen_fixture.py" base
    git add -A && git commit -qm "initial"
    if [ "$fixture" = "staged" ]; then
      python3 "$ROOT/evals/gen_fixture.py" change && git add -A
    else
      python3 "$ROOT/evals/gen_fixture.py" "$fixture"
    fi
  )

  SID=$(uuidgen | tr 'A-Z' 'a-z')
  SID2=$(uuidgen | tr 'A-Z' 'a-z')
  args=(--model "$MODEL" --dangerously-skip-permissions)
  [ "$arm" = "B" ] && args+=(--plugin-dir "$ROOT")
  P="[$arm/$task/$n]"

  (cd "$REPO" && env -u CLAUDE_CODE_SUBAGENT_MODEL claude -p "$prompt" "${args[@]}" --session-id "$SID" \
      --output-format stream-json --verbose </dev/null 2>/dev/null \
      | python3 "$ROOT/evals/tail_format.py" "$P" >> "$LIVE") || echo "$P warn: run nonzero exit"

  if [ "$ttype" = "chore" ]; then
    echo "$P ---- follow-up ----" >> "$LIVE"
    (cd "$REPO" && env -u CLAUDE_CODE_SUBAGENT_MODEL claude -p "$FOLLOWUP" "${args[@]}" \
        --resume "$SID" --fork-session --session-id "$SID2" \
        --output-format stream-json --verbose </dev/null 2>/dev/null \
        | python3 "$ROOT/evals/tail_format.py" "$P" >> "$LIVE") || echo "$P warn: follow-up nonzero exit"
  fi

  ok=true
  case "$success" in
    commit) [ "$(git -C "$REPO" rev-list --count HEAD)" -ge 2 ] || ok=false ;;
    file:*) [ -s "$REPO/${success#file:}" ] || ok=false ;;
  esac
  [ "$ok" = "true" ] || echo "$P TASK FAILED"

  printf '{"arm":"%s","task":"%s","type":"%s","trial":%s,"sid":"%s","sid2":"%s","success":%s}\n' \
    "$arm" "$task" "$ttype" "$n" "$SID" "$SID2" "$ok" > "$TD/trial.json"
  exit 0
fi

# ---------- main ------------------------------------------------------------
N=${1:-3}
FILTER=${2:-.}

rm -rf "$WORK/trials"
mkdir -p "$WORK/trials" "$ROOT/evals/snapshots"
: > "$LIVE"
echo "watch with: tail -f $LIVE"

specs=()
while IFS='|' read -r name ttype; do
  echo "$name" | grep -qE "$FILTER" || continue
  for i in $(seq 1 "$N"); do
    if [ "$ttype" = "chore" ]; then
      specs+=("A|$name|$i" "B|$name|$i")
    else
      specs+=("B|$name|$i")
    fi
  done
done < <(python3 -c "
import json
for t in json.load(open('$TASKS')):
    print(t['name'] + '|' + t['type'])")

echo "running ${#specs[@]} trials, $PAR in parallel, model $MODEL"
printf '%s\n' "${specs[@]}" | xargs -P "$PAR" -I{} "$0" --run-one {}

SNAP="$ROOT/evals/snapshots/results.json"
python3 "$ROOT/evals/bench_measure.py" collect "$WORK/trials" --model "$MODEL" --followup "$FOLLOWUP" > "$SNAP"
echo "snapshot: $SNAP"
python3 "$ROOT/evals/bench_measure.py" report "$SNAP" | tee "$ROOT/evals/benchmark.md"
