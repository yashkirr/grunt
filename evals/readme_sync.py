#!/usr/bin/env python3
"""Regenerate the benchmark numbers embedded in README.md from committed eval
artifacts, so the README can never drift from the data.

Sources:
  evals/snapshots/results.json       -> headline, scoreboard, routing accuracy
  evals/quality.md                   -> judge verdict + objective pass rates
  evals/snapshots/results-sonnet.json + evals/quality-sonnet.md (optional)
                                     -> executor comparison table

The generated text lands between `<!-- bench:NAME -->` / `<!-- /bench:NAME -->`
marker pairs in README.md; everything outside the markers is hand-written.

Usage:
  python3 evals/readme_sync.py           rewrite README in place
  python3 evals/readme_sync.py --check   exit 1 if README is stale (for CI)
"""
import json
import pathlib
import re
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
README = ROOT / "README.md"


def in_tokens(d):
    return d["in"] + d["cw"] + d["cr"]


def total_cost(t):
    return t["exp"]["cost"] + t["sub"]["cost"] + t["followup_exp"]["cost"]


def med(rows, fn):
    return statistics.median([fn(t) for t in rows]) if rows else 0


def load_snap(name):
    p = ROOT / "evals" / "snapshots" / name
    if not p.exists():
        return None
    snap = json.load(open(p))
    return snap if snap.get("trials") else None


def quality_numbers(name):
    p = ROOT / "evals" / name
    if not p.exists():
        return None
    text = p.read_text()
    w = re.search(r"\*\*Grunt wins (\d+)/(\d+), ties (\d+)/\d+, loses (\d+)/\d+", text)
    if not w or int(w.group(2)) == 0:
        return None
    j = re.search(r"Blind pairwise judge: (\S+?)\.", text)
    o = re.search(r"Objective pass rate: baseline (\d+)/(\d+), grunt (\d+)/(\d+)", text)
    return {
        "wins": int(w.group(1)), "n": int(w.group(2)),
        "ties": int(w.group(3)), "losses": int(w.group(4)),
        "judge": j.group(1) if j else "unknown",
        "obj": tuple(int(x) for x in o.groups()) if o else None,
    }


def split_arms(snap):
    chores = [t for t in snap["trials"] if t["type"] == "chore"]
    probes = [t for t in snap["trials"] if t["type"] == "probe"]
    a = [t for t in chores if t["arm"] == "A"]
    b = [t for t in chores if t["arm"] == "B"]
    return chores, probes, a, b


def pct(a, b):
    return f"{(b - a) / a * 100:+.0f}%" if a else "n/a"


def block_headline(snap):
    chores, probes, a, b = split_arms(snap)
    delta = (med(a, lambda t: in_tokens(t["exp"])) - med(b, lambda t: in_tokens(t["exp"]))) \
        / med(a, lambda t: in_tokens(t["exp"])) * 100
    tp = sum(1 for t in b if t["delegated"])
    fp = sum(1 for t in probes if t["delegated"])
    return (f"Measured on real sessions: **{delta:.0f}% less expensive-model input per "
            f"chore**, **{tp}/{len(b)} chores routed correctly, {fp}/{len(probes)} false "
            f"positives**.")


def block_scoreboard(snap, sonnet_snap, sonnet_quality):
    chores, probes, a, b = split_arms(snap)
    tasks = sorted({t["task"] for t in chores})
    n = max((t["trial"] for t in chores), default=0)
    pn = max((t["trial"] for t in probes), default=0)
    meta = snap["meta"]
    ok = sum(1 for t in snap["trials"] if t["success"])
    tp = sum(1 for t in b if t["delegated"])
    fp = sum(1 for t in probes if t["delegated"])

    rows = [
        ("Expensive-model input tokens per chore", lambda t: in_tokens(t["exp"]),
         lambda v: f"{v:,.0f}"),
        ("Expensive-model cost per chore", lambda t: t["exp"]["cost"],
         lambda v: f"${v:.3f}"),
        ("Total cost, all models", total_cost, lambda v: f"${v:.3f}"),
    ]
    lines = [
        f"{len(tasks)} chore tasks ({', '.join(tasks)}) × 2 arms × {n} trials, plus "
        f"{len({t['task'] for t in probes})} non-chore probes × {pn} trials: "
        f"**{len(snap['trials'])} real headless `claude -p` sessions** on "
        f"`{meta['model']}` (executor: {meta.get('grunt_model', 'haiku')}), snapshot "
        f"{meta['generated'][:10]}. Per-model token counts are parsed from the session "
        f"transcripts; dollar figures use API list prices as a proxy for limit burn.",
        "",
        "| Metric (median, all chores) | Baseline | With grunt |",
        "|---|---:|---:|",
    ]
    for label, fn, fmt in rows:
        va, vb = med(a, fn), med(b, fn)
        lines.append(f"| {label} | {fmt(va)} | {fmt(vb)} (**{pct(va, vb)}**) |")
    lines += [
        "",
        f"**Routing: {tp}/{len(b)} chores delegated, {fp}/{len(probes)} non-chore probes "
        f"falsely delegated, {ok}/{len(snap['trials'])} tasks completed.** (Completed means "
        "the commit landed or the file was written — correctness is measured separately "
        "below.)",
    ]

    if sonnet_snap:
        _, _, _, sb = split_arms(sonnet_snap)
        lines += [
            "",
            "### Executor comparison (arm B, same task suite)",
            "",
            "| Executor | Expensive input/chore | Total cost/chore | Blind judge vs baseline |",
            "|---|---:|---:|---|",
        ]
        for label, arm_rows, q in (
            ("haiku", b, quality_numbers("quality.md")),
            (sonnet_snap["meta"].get("grunt_model", "sonnet"), sb, sonnet_quality),
        ):
            verdict = (f"{q['wins']} wins / {q['ties']} ties / {q['losses']} losses"
                       if q else "not judged")
            lines.append(f"| {label} | {med(arm_rows, lambda t: in_tokens(t['exp'])):,.0f} | "
                         f"${med(arm_rows, total_cost):.3f} | {verdict} |")
    return "\n".join(lines)


def block_quality(q):
    if not q:
        return "_No quality judging on the current snapshot yet — run `python3 evals/judge.py`._"
    out = (f"A blind pairwise judge ({q['judge']}, arm order anonymized) preferred the "
           f"baseline's artifacts **{q['losses']}/{q['n']}**, with **{q['ties']} ties and "
           f"{q['wins']} grunt wins**.")
    if q["obj"]:
        ba, bn, ga, gn = q["obj"]
        out += (f" On objective ground-truth checks both arms are close: baseline "
                f"{ba}/{bn}, grunt {ga}/{gn} (deterministic log ERROR counts; Conventional "
                f"Commits subjects regex-checked).")
    return out


def replace(text, name, content):
    pat = re.compile(rf"(<!-- bench:{name} -->\n).*?(\n<!-- /bench:{name} -->)", re.S)
    if not pat.search(text):
        sys.exit(f"error: marker bench:{name} missing from README.md")
    return pat.sub(lambda m: m.group(1) + content + m.group(2), text, count=1)


def main():
    snap = load_snap("results.json")
    if not snap:
        sys.exit("error: evals/snapshots/results.json missing or empty")
    sonnet_snap = load_snap("results-sonnet.json")
    sonnet_quality = quality_numbers("quality-sonnet.md")

    text = README.read_text()
    new = text
    new = replace(new, "headline", block_headline(snap))
    new = replace(new, "scoreboard", block_scoreboard(snap, sonnet_snap, sonnet_quality))
    new = replace(new, "quality", block_quality(quality_numbers("quality.md")))

    if "--check" in sys.argv:
        if new != text:
            sys.exit("README.md is stale — run: python3 evals/readme_sync.py")
        print("README.md in sync")
        return
    if new != text:
        README.write_text(new)
        print("README.md updated")
    else:
        print("README.md already in sync")


if __name__ == "__main__":
    main()
