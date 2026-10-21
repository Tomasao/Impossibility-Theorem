#!/usr/bin/env python3
"""build_fig1_data.py -- write the bounded-test marks of Figure 1(c) into fig1_concept.tex.

Reads the Goldbach-search rows of Simulation 3 (sim3_open_problem_results.csv) and
replaces the block between the AUTO-GENERATED markers in fig1_concept.tex with one
\GoldbachTest{k}{verdict} line per tested horizon H = 10^k.  No value is typed by hand.

Usage (from figures_v14/):
    python build_fig1_data.py
    python build_fig1_data.py --csv data/sim3_open_problem_results.csv --tex fig1_concept.tex
Standard library only.  The script is idempotent: re-running it rewrites the same block.
"""
import argparse
import csv
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BEGIN = "% >>> BEGIN AUTO-GENERATED: Goldbach bounded tests"
END = "% <<< END AUTO-GENERATED: Goldbach bounded tests"


def build_block(rows, csv_name, program):
    out = [BEGIN,
           f"% written by build_fig1_data.py from {csv_name} (program = {program}); do not edit by hand"]
    for r in sorted(rows, key=lambda r: int(r["horizon"])):
        H = int(r["horizon"])
        k = round(math.log10(H))
        if 10 ** k != H:
            sys.exit(f"horizon {H} is not an exact power of ten; the timeline assumes H = 10^k")
        verdict = r["bounded_test_verdict"].strip()
        if verdict not in ("permitted", "forbidden"):
            sys.exit(f"unexpected verdict {verdict!r} at H = {H}")
        bad = r["bad_observed"].strip().lower() == "true"
        if bad != (verdict == "forbidden"):
            sys.exit(f"verdict {verdict!r} inconsistent with bad_observed = {r['bad_observed']} at H = {H}")
        out.append(f"\\GoldbachTest{{{k}}}{{{verdict}}}% H = {H}, bad_observed = {r['bad_observed'].strip()}")
    kmax = max(round(math.log10(int(r["horizon"]))) for r in rows)
    out.insert(2, f"\\def\\GoldbachKmax{{{kmax}}}% largest tested exponent k (H = 10^k)")
    out.append(END)
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", default=str(HERE.parent / "reproducibility" / "sim3_open_problem_results.csv"))
    ap.add_argument("--tex", default=str(HERE / "fig1_concept.tex"))
    ap.add_argument("--program", default="goldbach_search")
    a = ap.parse_args()
    with open(a.csv, newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["program"] == a.program]
    if not rows:
        sys.exit(f"no rows for program {a.program!r} in {a.csv}")
    block = build_block(rows, Path(a.csv).name, a.program)
    tex = Path(a.tex).read_text()
    pat = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)
    if len(pat.findall(tex)) != 1:
        sys.exit(f"expected exactly one AUTO-GENERATED block in {a.tex}")
    Path(a.tex).write_text(pat.sub(lambda m: block, tex, count=1))
    verdicts = sorted({r["bounded_test_verdict"] for r in rows})
    print(f"fig1(c): wrote {len(rows)} bounded tests for {a.program} "
          f"(H = {min(int(r['horizon']) for r in rows)}..{max(int(r['horizon']) for r in rows)}; "
          f"verdicts = {verdicts}) into {Path(a.tex).name}")


if __name__ == "__main__":
    main()
