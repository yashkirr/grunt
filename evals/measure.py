#!/usr/bin/env python3
"""Measure per-model token usage for the grunt A/B experiment.

Usage: measure.py <manifest.json>

Manifest rows: {"arm": "A"|"B", "trial": N, "sid": <chore session id>,
"sid2": <follow-up session id>, "commit_ok": bool}. Emits a markdown report
to stdout. Reads transcripts from ~/.claude/projects/*/<sid>.jsonl and
subagent transcripts from ~/.claude/projects/*/<sid>/subagents/*.jsonl.
"""
import glob
import json
import os
import statistics
import sys

FOLLOWUP_MARKER = "In one sentence, what did that commit change?"

# $ per MTok by model-id prefix: (input, output, cache_write, cache_read).
# API list prices as of 2026-07; proxy for subscription-limit burn.
PRICES = {
    "claude-fable": (10.0, 50.0, 12.5, 1.0),
    "claude-opus": (5.0, 25.0, 6.25, 0.5),
    "claude-sonnet": (3.0, 15.0, 3.75, 0.3),
    "claude-haiku": (1.0, 5.0, 1.25, 0.1),
}

EXPENSIVE_PREFIX = "claude-fable"


def price(model):
    for prefix, p in PRICES.items():
        if model.startswith(prefix):
            return p
    return (0.0, 0.0, 0.0, 0.0)


def events(path):
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def sum_usage(evts):
    """Sum usage per model. Dedupes on message id: one assistant message can
    span several JSONL lines, each repeating the same usage block."""
    seen = set()
    totals = {}
    for e in evts:
        m = e.get("message") or {}
        u = m.get("usage") or {}
        if e.get("type") != "assistant" or not m.get("model") or not u:
            continue
        if m.get("id") in seen:
            continue
        seen.add(m.get("id"))
        t = totals.setdefault(m["model"], {"in": 0, "out": 0, "cw": 0, "cr": 0, "cost": 0.0})
        i = u.get("input_tokens", 0)
        o = u.get("output_tokens", 0)
        cw = u.get("cache_creation_input_tokens", 0)
        cr = u.get("cache_read_input_tokens", 0)
        pi, po, pw, pr = price(m["model"])
        t["in"] += i
        t["out"] += o
        t["cw"] += cw
        t["cr"] += cr
        t["cost"] += (i * pi + o * po + cw * pw + cr * pr) / 1e6
    return totals


def find_transcript(sid):
    hits = glob.glob(os.path.expanduser(f"~/.claude/projects/*/{sid}.jsonl"))
    return hits[0] if hits else None


def split_at_marker(path):
    """Return (events before follow-up prompt, events from it onward)."""
    lines = list(events(path))
    idx = None
    for i, e in enumerate(lines):
        if e.get("type") == "user" and not e.get("toolUseResult"):
            content = (e.get("message") or {}).get("content")
            if content is not None and FOLLOWUP_MARKER in json.dumps(content):
                idx = i
    if idx is None:
        return lines, []
    return lines[:idx], lines[idx:]


def expensive(totals):
    agg = {"in": 0, "out": 0, "cw": 0, "cr": 0, "cost": 0.0}
    for model, t in totals.items():
        if model.startswith(EXPENSIVE_PREFIX):
            for k in agg:
                agg[k] += t[k]
    return agg


def cheap(totals):
    agg = {"in": 0, "out": 0, "cw": 0, "cr": 0, "cost": 0.0}
    for model, t in totals.items():
        if not model.startswith(EXPENSIVE_PREFIX):
            for k in agg:
                agg[k] += t[k]
    return agg


def measure_trial(row):
    main = find_transcript(row["sid"])
    if not main:
        return None
    chore_events, _ = split_at_marker(main)
    chore = sum_usage(chore_events)

    sub_totals = {}
    subdir = main[: -len(".jsonl")] + "/subagents"
    for f in glob.glob(f"{subdir}/*.jsonl"):
        for model, t in sum_usage(events(f)).items():
            agg = sub_totals.setdefault(model, {"in": 0, "out": 0, "cw": 0, "cr": 0, "cost": 0.0})
            for k in agg:
                agg[k] += t[k]

    followup = {"in": 0, "out": 0, "cw": 0, "cr": 0, "cost": 0.0}
    f2 = find_transcript(row.get("sid2", ""))
    if f2:
        _, after = split_at_marker(f2)
        followup = expensive(sum_usage(after))

    return {
        "chore_exp": expensive(chore),
        "chore_cheap": cheap(chore),
        "sub_cheap": cheap(sub_totals) if sub_totals else {"in": 0, "out": 0, "cw": 0, "cr": 0, "cost": 0.0},
        "delegated": bool(sub_totals),
        "followup_exp": followup,
    }


def med(vals):
    return statistics.median(vals) if vals else 0


def fmt_tok(n):
    return f"{n:,.0f}"


def main():
    manifest = json.load(open(sys.argv[1]))
    arms = {}
    failures = []
    for row in manifest["trials"]:
        if not row.get("commit_ok", True):
            failures.append(f"arm {row['arm']} trial {row['trial']}: commit did not land (excluded)")
            continue
        m = measure_trial(row)
        if m is None:
            failures.append(f"arm {row['arm']} trial {row['trial']}: transcript not found (excluded)")
            continue
        m["trial"] = row["trial"]
        arms.setdefault(row["arm"], []).append(m)

    print("# grunt A/B results\n")
    print(f"Arm A = baseline (fable does the chore). Arm B = grunt plugin (fable delegates to haiku). Trials measured: "
          + ", ".join(f"{k}={len(v)}" for k, v in sorted(arms.items())) + "\n")

    if failures:
        print("Excluded trials:\n")
        for f in failures:
            print(f"- {f}")
        print()

    if "B" in arms:
        n_del = sum(1 for m in arms["B"] if m["delegated"])
        print(f"Delegation success (arm B): {n_del}/{len(arms['B'])} trials spawned a cheap-model subagent.\n")

    def col(arm, key, sub):
        return [m[key][sub] for m in arms.get(arm, [])]

    def cost_total(m):
        return m["chore_exp"]["cost"] + m["chore_cheap"]["cost"] + m["sub_cheap"]["cost"] + m["followup_exp"]["cost"]

    rows = [
        ("Fable input tokens, chore turn (in+cw+cr)",
         lambda a: med([m["chore_exp"]["in"] + m["chore_exp"]["cw"] + m["chore_exp"]["cr"] for m in arms.get(a, [])]), fmt_tok),
        ("Fable output tokens, chore turn", lambda a: med(col(a, "chore_exp", "out")), fmt_tok),
        ("Haiku tokens, subagent (in+cw+cr+out)",
         lambda a: med([m["sub_cheap"]["in"] + m["sub_cheap"]["cw"] + m["sub_cheap"]["cr"] + m["sub_cheap"]["out"] for m in arms.get(a, [])]), fmt_tok),
        ("Fable input tokens, follow-up turn (in+cw+cr)",
         lambda a: med([m["followup_exp"]["in"] + m["followup_exp"]["cw"] + m["followup_exp"]["cr"] for m in arms.get(a, [])]), fmt_tok),
        ("Fable cost, chore turn ($, API-price proxy)", lambda a: med(col(a, "chore_exp", "cost")), lambda v: f"{v:.4f}"),
        ("Fable cost, follow-up turn ($)", lambda a: med(col(a, "followup_exp", "cost")), lambda v: f"{v:.4f}"),
        ("Total cost, all models ($)", lambda a: med([cost_total(m) for m in arms.get(a, [])]), lambda v: f"{v:.4f}"),
    ]

    print("| Metric (median) | Arm A baseline | Arm B grunt |")
    print("|---|---:|---:|")
    for label, fn, fmt in rows:
        print(f"| {label} | {fmt(fn('A'))} | {fmt(fn('B'))} |")

    print("\nPer-trial fable chore-turn cost ($):\n")
    for arm in sorted(arms):
        vals = ", ".join(f"{m['chore_exp']['cost']:.4f}" for m in arms[arm])
        print(f"- Arm {arm}: {vals}")


if __name__ == "__main__":
    main()
