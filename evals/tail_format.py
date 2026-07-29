#!/usr/bin/env python3
"""Turn `claude -p --output-format stream-json` into a human-readable tail.

Usage: claude -p ... --output-format stream-json | python3 tail_format.py [prefix]
"""
import json
import sys

PREFIX = (sys.argv[1] + " ") if len(sys.argv) > 1 else ""


def block_line(b):
    t = b.get("type")
    if t == "text" and b.get("text", "").strip():
        return "  ● " + b["text"].strip().replace("\n", "\n    ")
    if t == "tool_use":
        arg = json.dumps(b.get("input", {}))
        if len(arg) > 160:
            arg = arg[:160] + "…"
        return f"  → {b.get('name')} {arg}"
    return None


for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        e = json.loads(line)
    except json.JSONDecodeError:
        continue
    t = e.get("type")
    if t == "system" and e.get("subtype") == "init":
        print(f"{PREFIX}[session {e.get('session_id', '?')[:8]} model={e.get('model', '?')}]", flush=True)
    elif t == "assistant":
        for b in (e.get("message") or {}).get("content", []):
            out = block_line(b)
            if out:
                print(PREFIX + out, flush=True)
    elif t == "result":
        cost = e.get("total_cost_usd")
        dur = e.get("duration_ms", 0) / 1000
        print(f"{PREFIX}[done in {dur:.0f}s" + (f", ~${cost:.4f}]" if cost is not None else "]"), flush=True)
