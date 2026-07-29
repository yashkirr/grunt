#!/usr/bin/env python3
"""Deterministic benchmark fixtures. Run inside the fixture repo.

Modes:
  base    - pre-change source tree (commit this)
  change  - rewrite with docstrings + new functions (~200-line staged diff)
  log     - synthetic app.log (~300 lines, fixed ERROR counts per service)
"""
import pathlib
import sys

mode = sys.argv[1]
src = pathlib.Path("src")
src.mkdir(exist_ok=True)

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
elif mode == "change":
    (src / "mathutils.py").write_text(module(math_fns + new_math_fns, doc=True))
    (src / "strutils.py").write_text(module(str_fns, doc=True))
    (src / "dateutils.py").write_text(module(date_fns, doc=True))
    pathlib.Path("README.md").write_text(
        "# fixture\n\nA tiny utility library used as an experiment fixture.\n\n"
        "## Modules\n\n- mathutils: arithmetic helpers\n- strutils: string helpers\n- dateutils: date helpers\n")
elif mode == "log":
    services = ["auth", "payments", "search"]
    lines = []
    for i in range(300):
        svc = services[i % 3]
        if i % 11 == 0:
            level, msg = "ERROR", f"request failed: upstream timeout after {100 + i}ms"
        elif i % 5 == 0:
            level, msg = "WARN", f"slow response: {50 + i}ms"
        else:
            level, msg = "INFO", f"handled request id=req-{1000 + i}"
        lines.append(f"2026-07-29T10:{i // 60:02d}:{i % 60:02d}Z [{svc}] {level} {msg}")
    pathlib.Path("app.log").write_text("\n".join(lines) + "\n")
else:
    sys.exit(f"unknown mode: {mode}")
