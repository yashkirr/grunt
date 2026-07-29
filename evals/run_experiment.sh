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

mkdir -p "$WORK"

# Deterministic fixture generator: "base" writes the pre-change tree,
# "change" rewrites it with docstrings + new functions (~200-line diff).
cat > "$WORK/gen_fixture.py" <<'PY'
import pathlib, sys
mode = sys.argv[1]
src = pathlib.Path("src"); src.mkdir(exist_ok=True)
math_fns = ["add", "sub", "mul", "div", "mod", "power", "floor_div", "neg", "absval", "sign"]
new_math_fns = ["clamp", "lerp", "mean", "median_of_three", "gcd"]
str_fns = ["upper", "lower", "title", "reverse", "strip_all", "first_word", "last_word", "word_count"]
date_fns = ["is_leap_year", "days_in_month", "day_of_year", "iso_week", "add_days",
            "diff_days", "start_of_month", "end_of_month", "is_weekend", "next_weekday",
            "quarter", "format_iso", "parse_iso", "age_in_years", "same_day"]

def fn(name, doc):
    lines = [f"def {name}(a, b=None):"]
    if doc:
        title = name.replace("_", " ").capitalize()
        lines += ['    """' + title + " operation.", "", "    Args:",
                  "        a: first operand", "        b: optional second operand",
                  '    """']
    lines.append("    return (a, b)")
    return "\n".join(lines) + "\n"

def module(fns, doc):
    return "\n".join(fn(f, doc) for f in fns)

if mode == "base":
    (src / "mathutils.py").write_text(module(math_fns, doc=False))
    (src / "strutils.py").write_text(module(str_fns, doc=False))
    pathlib.Path("README.md").write_text("# fixture\n\nA tiny utility library used as an experiment fixture.\n")
else:
    (src / "mathutils.py").write_text(module(math_fns + new_math_fns, doc=True))
    (src / "strutils.py").write_text(module(str_fns, doc=True))
    (src / "dateutils.py").write_text(module(date_fns, doc=True))
    pathlib.Path("README.md").write_text(
        "# fixture\n\nA tiny utility library used as an experiment fixture.\n\n"
        "## Modules\n\n- mathutils: arithmetic helpers\n- strutils: string helpers\n- dateutils: date helpers\n")
PY

seed_fixture() {
  rm -rf "$FIX"
  mkdir -p "$FIX"
  (
    cd "$FIX"
    git init -qb main
    git config user.email eval@grunt.local
    git config user.name "grunt eval"
    python3 "$WORK/gen_fixture.py" base
    git add -A
    git commit -qm "initial"
    python3 "$WORK/gen_fixture.py" change
    git add -A
  )
}

rows=()
for arm in A B; do
  for i in $(seq 1 "$N"); do
    echo "=== arm $arm trial $i/$N ==="
    seed_fixture

    SID=$(uuidgen | tr 'A-Z' 'a-z')
    SID2=$(uuidgen | tr 'A-Z' 'a-z')
    args=(--model "$MODEL" --dangerously-skip-permissions)
    if [ "$arm" = "B" ]; then
      args+=(--plugin-dir "$ROOT")
    fi

    (cd "$FIX" && claude -p "$CHORE" "${args[@]}" --session-id "$SID" >/dev/null 2>&1) \
      || echo "warn: chore run nonzero exit"

    commit_ok=true
    if [ "$(git -C "$FIX" rev-list --count HEAD)" -lt 2 ]; then
      echo "FAIL: commit did not land"
      commit_ok=false
    fi

    (cd "$FIX" && claude -p "$FOLLOWUP" "${args[@]}" --resume "$SID" --fork-session --session-id "$SID2" >/dev/null 2>&1) \
      || echo "warn: follow-up run nonzero exit"

    rows+=("{\"arm\":\"$arm\",\"trial\":$i,\"sid\":\"$SID\",\"sid2\":\"$SID2\",\"commit_ok\":$commit_ok}")
  done
done

printf '{"trials":[%s]}\n' "$(IFS=,; echo "${rows[*]}")" > "$MANIFEST"
echo "manifest: $MANIFEST"

python3 "$ROOT/evals/measure.py" "$MANIFEST" | tee "$ROOT/evals/results.md"
