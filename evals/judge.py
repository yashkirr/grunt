#!/usr/bin/env python3
"""Qualitative layer for the benchmark: is the cheap model's output as GOOD?

Two checks over artifacts left in evals/work/trials/ by bench.sh:
1. Blind pairwise judge: arm A vs arm B artifact per (task, trial), shuffled
   to anonymous X/Y, judged by JUDGE_MODEL (default claude-fable-5).
2. Objective ground truth: log-filter counts are deterministic (recomputed
   here); commit subjects checked against Conventional Commits.

Usage: python3 judge.py [trials_dir]   -> writes markdown to stdout
"""
import concurrent.futures
import json
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
TRIALS = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "work" / "trials"
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "claude-fable-5")
TASKS = {t["name"]: t for t in json.load(open(ROOT / "tasks.json"))}

CONVENTIONAL = re.compile(r"^(feat|fix|chore|docs|refactor|test|style|perf|build|ci)(\(.+\))?: \S")


def git_msg(repo):
    r = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%B"],
                       capture_output=True, text=True)
    return r.stdout.strip()


def artifact(task, repo):
    if task == "commit":
        return git_msg(repo)
    if task == "changelog":
        p = repo / "CHANGELOG.md"
        body = p.read_text() if p.exists() else "(missing CHANGELOG.md)"
        return f"CHANGELOG.md:\n{body}\n\ncommit message:\n{git_msg(repo)}"
    if task == "pr-desc":
        p = repo / "PR.md"
        return p.read_text() if p.exists() else "(missing PR.md)"
    if task == "log-filter":
        p = repo / "errors.md"
        return p.read_text() if p.exists() else "(missing errors.md)"
    return None


def judge_pair(task, trial, a_text, b_text):
    # Blind shuffle: which arm plays X varies per (task, trial); the same
    # value un-maps the verdict below, so mapping is always consistent.
    a_is_x = (hash(f"{task}-{trial}") % 2 == 0)
    x, y = (a_text, b_text) if a_is_x else (b_text, a_text)
    prompt = f"""You are blind-judging two attempts at the same task. You do not know what produced either.

THE TASK GIVEN: {TASKS[task]["prompt"]}

ATTEMPT X:
{x}

ATTEMPT Y:
{y}

Judge on: factual correctness, completeness for the task, convention/format quality, and appropriate concision. Ties are fine when both are adequate. Reply with exactly two lines:
WINNER: X or Y or TIE
REASON: one sentence"""
    r = subprocess.run(["claude", "-p", prompt, "--model", JUDGE_MODEL],
                       capture_output=True, text=True, timeout=300)
    m = re.search(r"WINNER:\s*(X|Y|TIE)", r.stdout, re.I)
    verdict = m.group(1).upper() if m else "PARSE_FAIL"
    reason = ""
    rm = re.search(r"REASON:\s*(.+)", r.stdout)
    if rm:
        reason = rm.group(1).strip()
    if verdict in ("X", "Y"):
        winner = "A" if (verdict == "X") == a_is_x else "B"
    else:
        winner = verdict
    return {"task": task, "trial": trial, "winner": winner, "reason": reason}


def expected_log_counts():
    counts = {"auth": 0, "payments": 0, "search": 0}
    services = ["auth", "payments", "search"]
    for i in range(300):
        if i % 11 == 0:
            counts[services[i % 3]] += 1
    return counts


def objective_checks():
    rows = []
    truth = expected_log_counts()
    for d in sorted(TRIALS.iterdir()):
        if not (d / "trial.json").exists():
            continue
        row = json.load(open(d / "trial.json"))
        repo = d / "repo"
        task, arm, trial = row["task"], row["arm"], row["trial"]
        if task in ("commit", "changelog"):
            subj = git_msg(repo).splitlines()[0] if git_msg(repo) else ""
            ok = bool(CONVENTIONAL.match(subj)) and len(subj) <= 72
            rows.append((task, arm, trial, "conventional subject", ok, subj[:60]))
        elif task == "log-filter":
            text = artifact(task, repo)
            ok = all(str(n) in text for n in truth.values())
            rows.append((task, arm, trial, f"correct counts {truth}", ok, ""))
    return rows


def main():
    pairs = {}
    for d in sorted(TRIALS.iterdir()):
        tj = d / "trial.json"
        if not tj.exists():
            continue
        row = json.load(open(tj))
        if row["type"] != "chore":
            continue
        text = artifact(row["task"], d / "repo")
        pairs.setdefault((row["task"], row["trial"]), {})[row["arm"]] = text

    jobs = [(t, n, arms["A"], arms["B"]) for (t, n), arms in sorted(pairs.items())
            if arms.get("A") and arms.get("B")]
    print(f"judging {len(jobs)} pairs with {JUDGE_MODEL}...", file=sys.stderr)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(lambda j: judge_pair(*j), jobs))

    print("# grunt quality evaluation\n")
    print(f"Blind pairwise judge: {JUDGE_MODEL}. A = baseline (expensive model did the chore), "
          f"B = grunt (cheap model did it). Arm order anonymized per pair.\n")
    wins = {"A": 0, "B": 0, "TIE": 0}
    print("| Task | Trial | Better artifact | Judge's reason |")
    print("|---|---|---|---|")
    for r in sorted(results, key=lambda r: (r["task"], r["trial"])):
        wins[r["winner"]] = wins.get(r["winner"], 0) + 1
        label = {"A": "baseline", "B": "grunt", "TIE": "tie"}.get(r["winner"], r["winner"])
        print(f"| {r['task']} | {r['trial']} | {label} | {r['reason']} |")
    n = len(results)
    print(f"\n**Grunt wins {wins['B']}/{n}, ties {wins.get('TIE', 0)}/{n}, "
          f"loses {wins['A']}/{n}.**\n")

    print("## Objective checks (ground truth, no judge)\n")
    print("| Task | Arm | Trial | Check | Pass | Note |")
    print("|---|---|---|---|---|---|")
    obj = objective_checks()
    for task, arm, trial, check, ok, note in obj:
        print(f"| {task} | {arm} | {trial} | {check} | {'✅' if ok else '❌'} | {note} |")
    a_ok = sum(1 for t in obj if t[1] == "A" and t[4])
    a_n = sum(1 for t in obj if t[1] == "A")
    b_ok = sum(1 for t in obj if t[1] == "B" and t[4])
    b_n = sum(1 for t in obj if t[1] == "B")
    print(f"\nObjective pass rate: baseline {a_ok}/{a_n}, grunt {b_ok}/{b_n}.")


if __name__ == "__main__":
    main()
