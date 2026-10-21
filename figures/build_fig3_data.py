#!/usr/bin/env python3
"""build_fig3_data.py -- write the Simulation 1 data of Figure 3(c) into fig3_selfreference.tex.

Reads sim1_adversary_results.csv (columns checker, T, checker_cost_steps, correct, ...)
and replaces the two AUTO-GENERATED blocks of fig3_selfreference.tex:
  'fig3 axis'  -- axis limits and ticks (derived from the data range) and the limits
                  of the shaded region "cost below the budget T" (the line cost = T);
  'fig3 plots' -- for each of four checkers: one \addplot of (T, checker_cost_steps),
                  per-point markers (filled circle = right verdict, cross = wrong verdict,
                  taken from the 'correct' column), and a direct label at the line's end
                  whose "right/wrong at all n budgets" text is computed from the data.
No plotted number is typed by hand.  Before writing, the script checks the claims that
the figure makes (panel title and shaded region) against every row of the CSV and stops
with an error if any claim would be false.

Usage (from figures_v14/):
    python build_fig3_data.py
    python build_fig3_data.py --csv data/sim1_adversary_results.csv --tex fig3_selfreference.tex
Standard library only.  Idempotent.
"""
import argparse
import csv
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent

# (checker name in the CSV, plain-language description used in the direct label)
CHECKERS = [
    ("simulate_full_T", r"simulates all $T$ steps"),
    ("simulate_half_T", r"simulates $T/2$ steps"),
    ("simulate_sqrt_T", r"simulates $\sqrt{T}$ steps"),
    ("static_no_bad_call", r"reads the text only"),
]
FOCAL = "simulate_full_T"      # the checker that spends the whole budget
PAD_X = 2 ** 0.25              # quarter-octave padding of the T axis
PAD_Y = 10 ** 0.2              # 0.2-decade padding of the cost axis


def fmt(v):
    return f"{v:.6g}"


def replace_block(tex, name, body):
    begin = f"% >>> BEGIN AUTO-GENERATED: {name}"
    end = f"% <<< END AUTO-GENERATED: {name}"
    pat = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
    if len(pat.findall(tex)) != 1:
        sys.exit(f"expected exactly one AUTO-GENERATED block '{name}'")
    stamp = "% written by build_fig3_data.py from sim1_adversary_results.csv; do not edit by hand"
    return pat.sub(lambda m: "\n".join([begin, stamp, body, end]), tex, count=1)


def load(path):
    data = defaultdict(list)
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            data[r["checker"]].append((int(r["T"]), int(r["checker_cost_steps"]),
                                       r["correct"].strip().lower() == "true"))
    for k in data:
        data[k].sort()
    return data


def check_claims(data):
    """Claims printed in Figure 3(c); every one must hold on every row."""
    problems = []
    if FOCAL not in data:
        problems.append(f"{FOCAL} missing")
    else:
        if not all(ok for _, _, ok in data[FOCAL]):
            problems.append(f"{FOCAL} is not right at every budget")
        if not all(cost >= T for T, cost, _ in data[FOCAL]):
            problems.append(f"{FOCAL} does not spend the whole budget at every T")
    for name, rows in data.items():          # 'only' ranges over every checker in the CSV
        if name != FOCAL and any(ok for _, _, ok in rows):
            problems.append(f"{name} is right at some budget, so 'only ... is right' is false")
    for name, _ in CHECKERS:                  # plotted wrong checkers lie in the shaded region
        if name != FOCAL and not all(cost < T for T, cost, _ in data.get(name, [])):
            problems.append(f"{name} has a point with cost >= T, outside 'cost below the budget T'")
    budgets = {tuple(T for T, _, _ in data[n]) for n, _ in CHECKERS if n in data}
    if len(budgets) != 1:
        problems.append("the plotted checkers were not run on the same budgets")
    if problems:
        sys.exit("Figure 3(c) claims contradicted by the data:\n  " + "\n  ".join(problems))


def axis_block(data):
    Ts = sorted({T for n, _ in CHECKERS for T, _, _ in data[n]})
    costs = [c for n, _ in CHECKERS for _, c, _ in data[n]]
    xmin, xmax = min(Ts) / PAD_X, max(Ts) * PAD_X
    ymin, ymax = min(costs) / PAD_Y, max(costs) * PAD_Y
    decades = [10 ** k for k in range(math.ceil(math.log10(ymin)), math.floor(math.log10(ymax)) + 1)]
    xt = ",".join(str(T) for T in Ts)
    yt = ",".join(str(d) for d in decades)
    return "\n".join([
        r"\pgfplotsset{fig3 data axis/.style={xmin=%s, xmax=%s, ymin=%s, ymax=%s," % tuple(map(fmt, (xmin, xmax, ymin, ymax))),
        r"  xtick={%s}, xticklabels={%s}," % (xt, xt),
        r"  ytick={%s}, yticklabels={%s}}}" % (yt, yt),
        r"\def\FigThreeXmin{%s}\def\FigThreeXmax{%s}\def\FigThreeYmin{%s}" % tuple(map(fmt, (xmin, xmax, ymin))),
    ])


def plots_block(data):
    out = []
    for name, desc in CHECKERS:
        rows = data[name]
        n, k = len(rows), sum(ok for _, _, ok in rows)
        if k == n:
            style, colour, summary = "focal", "allowblue", f"right at all {n} budgets"
        elif k == 0:
            style, colour, summary = "other", "denyred", f"wrong at all {n} budgets"
        else:
            style, colour, summary = "series,draw=gray", "gray", f"right at {k} of {n} budgets"
        coords = " ".join(f"({T},{c})" for T, c, _ in rows)
        right = " ".join(f"({T},{c})" for T, c, ok in rows if ok)
        wrong = " ".join(f"({T},{c})" for T, c, ok in rows if not ok)
        out.append(f"% {name}: {n} budgets, right at {k}")
        out.append(f"\\addplot[{style}] coordinates {{{coords}}};")
        if right:
            out.append(f"\\addplot[rightmark] coordinates {{{right}}};")
        if wrong:
            out.append(f"\\addplot[wrongmark] coordinates {{{wrong}}};")
        T_last, c_last, _ = rows[-1]
        out.append(f"\\node[serieslabel,text={colour}] at (axis cs:{T_last},{c_last}) {{{desc}: {summary}}};")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", default=str(HERE.parent / "reproducibility" / "sim1_adversary_results.csv"))
    ap.add_argument("--tex", default=str(HERE / "fig3_selfreference.tex"))
    a = ap.parse_args()
    data = load(a.csv)
    missing = [n for n, _ in CHECKERS if n not in data]
    if missing:
        sys.exit(f"checkers missing from {a.csv}: {missing}")
    check_claims(data)
    tex = Path(a.tex).read_text()
    tex = replace_block(tex, "fig3 axis", axis_block(data))
    tex = replace_block(tex, "fig3 plots", plots_block(data))
    Path(a.tex).write_text(tex)
    for name, _ in CHECKERS:
        rows = data[name]
        print(f"fig3(c): {name:19s} T={rows[0][0]}..{rows[-1][0]}  cost={rows[0][1]}..{rows[-1][1]}  "
              f"right at {sum(ok for *_, ok in rows)}/{len(rows)}")
    print(f"fig3(c): claims checked against all {sum(len(v) for v in data.values())} rows "
          f"({len(data)} checkers); wrote {Path(a.tex).name}")


if __name__ == "__main__":
    main()
