#!/usr/bin/env bash
# grunt A/B experiment: does delegating a chore to a haiku subagent cut
# expensive-model token burn?
#
# Arm A: claude (fable) commits a staged change itself.
# Arm B: same, with the grunt plugin loaded via --plugin-dir.
# Both arms then get one follow-up turn to measure context pollution.
#
# Usage: ./run_experiment.sh [N]   (default N=5 trials per arm)
set -uo pipefail

N=${1:-5}
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$ROOT/evals/work"
FIX="$WORK/fixture-repo"
MODEL=claude-fable-5
CHORE="Commit the staged changes with a clear message."
FOLLOWUP="In one sentence, what did that commit change?"
MANIFEST="$WORK/manifest.json"
LIVE="$WORK/live.log"

mkdir -p "$WORK"
: > "$LIVE"
echo "watch with: tail -f $LIVE"

seed_fixture() {
  rm -rf "$FIX"
  mkdir -p "$FIX"
  (
    cd "$FIX"
    git init -qb main
    git config user.email eval@grunt.local
    git config user.name "grunt eval"
    python3 "$ROOT/evals/gen_fixture.py" base
    git add -A
    git commit -qm "initial"
    python3 "$ROOT/evals/gen_fixture.py" change
    git add -A
  )
}

rows=()
for arm in A B; do
  for i in $(seq 1 "$N"); do
    echo "=== arm $arm trial $i/$N ==="
    echo "" >> "$LIVE"
    echo "════ arm $arm trial $i/$N — chore ════" >> "$LIVE"
    seed_fixture

    SID=$(uuidgen | tr 'A-Z' 'a-z')
    SID2=$(uuidgen | tr 'A-Z' 'a-z')
    args=(--model "$MODEL" --dangerously-skip-permissions)
    if [ "$arm" = "B" ]; then
      args+=(--plugin-dir "$ROOT")
    fi

    (cd "$FIX" && claude -p "$CHORE" "${args[@]}" --session-id "$SID" \
        --output-format stream-json --verbose 2>/dev/null \
        | python3 "$ROOT/evals/tail_format.py" >> "$LIVE") \
      || echo "warn: chore run nonzero exit"

    commit_ok=true
    if [ "$(git -C "$FIX" rev-list --count HEAD)" -lt 2 ]; then
      echo "FAIL: commit did not land"
      commit_ok=false
    fi

    echo "──── arm $arm trial $i/$N — follow-up ────" >> "$LIVE"
    (cd "$FIX" && claude -p "$FOLLOWUP" "${args[@]}" --resume "$SID" --fork-session --session-id "$SID2" \
        --output-format stream-json --verbose 2>/dev/null \
        | python3 "$ROOT/evals/tail_format.py" >> "$LIVE") \
      || echo "warn: follow-up run nonzero exit"

    rows+=("{\"arm\":\"$arm\",\"trial\":$i,\"sid\":\"$SID\",\"sid2\":\"$SID2\",\"commit_ok\":$commit_ok}")
  done
done

printf '{"trials":[%s]}\n' "$(IFS=,; echo "${rows[*]}")" > "$MANIFEST"
echo "manifest: $MANIFEST"

python3 "$ROOT/evals/measure.py" "$MANIFEST" | tee "$ROOT/evals/results.md"
