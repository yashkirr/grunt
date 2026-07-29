#!/usr/bin/env python3
"""Benchmark snapshot tooling (caveman-style: measure once, report from git).

  collect <trials-dir> --model M --followup TEXT   parse transcripts -> snapshot JSON on stdout
  report  <snapshot.json>                          snapshot -> markdown report on stdout

`collect` needs the local ~/.claude transcripts; `report` needs only the
committed snapshot, so numbers can be re-rendered (and reviewed as diffs)
without re-running anything.
"""
import argparse
import glob
import json
import statistics
import subprocess
import sys

from measure import cheap, events, expensive, find_transcript, split_at_marker, sum_usage

ZERO = {"in": 0, "out": 0, "cw": 0, "cr": 0, "cost": 0.0}


def measure_trial(row, followup):
    main = find_transcript(row["sid"])
    if not main:
        return None
    chore_events, _ = split_at_marker(main, marker=followup)
    chore = sum_usage(chore_events)

    sub = dict(ZERO)
    for f in glob.glob(main[: -len(".jsonl")] + "/subagents/*.jsonl"):
        t = cheap(sum_usage(events(f)))
        for k in sub:
            sub[k] += t[k]

    fup = dict(ZERO)
    f2 = find_transcript(row.get("sid2", ""))
    if f2:
        _, after = split_at_marker(f2, marker=followup)
        fup = expensive(sum_usage(after))

    delegated = bool(glob.glob(main[: -len(".jsonl")] + "/subagents/*.jsonl"))
    return {
        "exp": expensive(chore),
        "sub": sub,
        "followup_exp": fup,
        "delegated": delegated,
    }


def cmd_collect(args):
    trials = []
    for path in sorted(glob.glob(f"{args.trials_dir}/*/trial.json")):
        row = json.load(open(path))
        m = measure_trial(row, args.followup)
        if m is None:
            print(f"warn: no transcript for {row}", file=sys.stderr)
            continue
        row.update(m)
        trials.append(row)
    date = subprocess.run(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], capture_output=True, text=True).stdout.strip()
    json.dump({"meta": {"model": args.model, "grunt_model": args.grunt_model,
                        "generated": date, "followup": args.followup}, "trials": trials},
              sys.stdout, indent=1)


def stats(vals):
    if not vals:
        return "-"
    m = statistics.median(vals)
    sd = statistics.stdev(vals) if len(vals) > 1 else 0
    return f"{m:,.0f} ±{sd:,.0f}" if m >= 100 else f"{m:.4f} ±{sd:.4f}"


def in_tokens(d):
    return d["in"] + d["cw"] + d["cr"]


def cmd_report(args):
    snap = json.load(open(args.snapshot))
    trials = snap["trials"]
    chores = [t for t in trials if t["type"] == "chore"]
    probes = [t for t in trials if t["type"] == "probe"]
    tasks = sorted({t["task"] for t in chores})

    def sel(task, arm):
        return [t for t in chores if t["task"] == task and t["arm"] == arm]

    def total_cost(t):
        return t["exp"]["cost"] + t["sub"]["cost"] + t["followup_exp"]["cost"]

    print(f"# grunt benchmark\n")
    gm = snap["meta"].get("grunt_model", "haiku")
    print(f"Model {snap['meta']['model']}, executor {gm}, generated {snap['meta']['generated']}. "
          f"Arm A = no plugin, arm B = grunt. Values: median ±stdev across trials.\n")

    print("## Per-task results\n")
    print("| Task | Metric | Arm A | Arm B |")
    print("|---|---|---:|---:|")
    for task in tasks:
        a, b = sel(task, "A"), sel(task, "B")
        rows = [
            ("expensive-model input tokens, task turn", lambda t: in_tokens(t["exp"])),
            ("cheap-model tokens (subagent)", lambda t: in_tokens(t["sub"]) + t["sub"]["out"]),
            ("expensive-model input tokens, follow-up", lambda t: in_tokens(t["followup_exp"])),
            ("total cost, all models ($)", total_cost),
        ]
        for label, fn in rows:
            print(f"| {task} | {label} | {stats([fn(t) for t in a])} | {stats([fn(t) for t in b])} |")

    print("\n## Scoreboard (all chore trials pooled)\n")
    a_all = [t for t in chores if t["arm"] == "A"]
    b_all = [t for t in chores if t["arm"] == "B"]

    def pooled(rows_, fn):
        return statistics.median([fn(t) for t in rows_]) if rows_ else 0

    pairs = [
        ("Expensive-model input tokens per chore", lambda t: in_tokens(t["exp"])),
        ("Expensive-model cost per chore ($)", lambda t: t["exp"]["cost"]),
        ("Follow-up input tokens", lambda t: in_tokens(t["followup_exp"])),
        ("Total cost per chore ($)", total_cost),
    ]
    print("| Metric (median) | Arm A | Arm B | Delta |")
    print("|---|---:|---:|---:|")
    for label, fn in pairs:
        va, vb = pooled(a_all, fn), pooled(b_all, fn)
        delta = (vb - va) / va * 100 if va else 0
        f = (lambda v: f"{v:,.0f}") if va >= 100 else (lambda v: f"{v:.4f}")
        print(f"| {label} | {f(va)} | {f(vb)} | {delta:+.0f}% |")

    tp = [t for t in b_all if t["delegated"]]
    fp = [t for t in probes if t["delegated"]]
    ok = [t for t in trials if t["success"]]
    print(f"\n## Delegation accuracy\n")
    print(f"- Chores delegated (arm B): **{len(tp)}/{len(b_all)}**")
    print(f"- Probes falsely delegated: **{len(fp)}/{len(probes)}**" +
          (" — " + ", ".join(f"{t['task']}#{t['trial']}" for t in fp) if fp else ""))
    print(f"- Task success (all trials): **{len(ok)}/{len(trials)}**")

    print("\n## What this does NOT measure\n")
    print("- Output fidelity: whether the cheap model's commit message / summary is as *good* — only that the task completed.")
    print("- Latency: delegation adds a subagent round trip.")
    print("- Cross-model behavior: only the snapshot's main model is measured.")
    print("- Subscription-limit weighting: dollar figures use API list prices as a proxy.")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect")
    c.add_argument("trials_dir")
    c.add_argument("--model", required=True)
    c.add_argument("--grunt-model", default="haiku")
    c.add_argument("--followup", required=True)
    r = sub.add_parser("report")
    r.add_argument("snapshot")
    args = p.parse_args()
    cmd_collect(args) if args.cmd == "collect" else cmd_report(args)


if __name__ == "__main__":
    main()
