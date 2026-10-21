#!/usr/bin/env python3
"""Build the editable PGFPlots figure that summarizes Experiments A, B and C (v13).

Python 3.9+, standard library. PDF output additionally needs pdflatex.
All plotted values are read from the archived CSV files; none is hard-coded.
"""
import argparse
import csv
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PREAMBLE = r"""\documentclass[tikz,border=5pt]{standalone}
\usepackage[T1]{fontenc}
\usepackage{pgfplots}
\usepgfplotslibrary{groupplots}
\pgfplotsset{compat=1.18}
\definecolor{allowblue}{RGB}{0,88,138}
\definecolor{denyred}{RGB}{163,41,47}
\definecolor{certorange}{RGB}{166,95,0}
\begin{document}
\begin{tikzpicture}
"""
END = "\\end{tikzpicture}\n\\end{document}\n"
H_REF = "8"           # horizon at which the sampled and exhaustive populations are compared


def rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def pct(numerator, denominator):
    return "%.1f" % (100.0 * numerator / denominator)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extensions", type=Path, default=ROOT / "data_extensions")
    parser.add_argument("--sampled", type=Path, default=ROOT / "data_sampled")
    parser.add_argument("--output", type=Path, default=ROOT / "figures")
    parser.add_argument("--compile", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    coverage = rows(args.extensions / "separator_coverage.csv")
    exhaustive = rows(args.extensions / "small_programs_summary.csv")
    sampled = rows(args.sampled / "sampled_programs_summary.csv")

    # Panel (a): coverage of the simplest checkable sets, by number of states.
    cov = {}
    for r in coverage:
        if r["norm"] in ("safety", "confidentiality"):
            cov.setdefault(r["norm"], []).append((r["states"], r["coverage_percent"]))

    # Panels (b) and (c): the exhaustive population (length <= 4) followed by the
    # sampled populations (lengths 6, 8, 10, 12), all at horizon H_REF.
    groups = []   # (label, {norm: row at H_REF})
    ex = {r["norm"]: r for r in exhaustive if r["horizon"] == H_REF}
    groups.append((r"$\leq 4$", ex))
    for length in sorted({int(r["length"]) for r in sampled}):
        groups.append((str(length), {r["norm"]: r for r in sampled
                                     if int(r["length"]) == length and r["horizon"] == H_REF}))
    labels = [g[0] for g in groups]
    fp_rate = {norm: [] for norm in ("safety", "confidentiality")}
    cert_share = {norm: [] for norm in ("safety", "confidentiality")}
    for label, byn in groups:
        for norm in ("safety", "confidentiality"):
            r = byn[norm]
            programs = int(r["programs"])
            resolved = programs - int(r["unresolved"])
            fp_rate[norm].append((label, "%.1f" % (10000.0 * int(r["false_permissions"]) / programs)))
            cert_share[norm].append((label, pct(int(r["certified"]), resolved)))

    def series(points):
        return " ".join("(%s,%s)" % p for p in points)

    symbolic = ",".join(labels)
    source = PREAMBLE + r"""\begin{groupplot}[
 group style={group size=3 by 1,horizontal sep=1.55cm},
 width=5.6cm,height=5.2cm,grid=major,grid style={gray!15},
 tick label style={font=\footnotesize},label style={font=\footnotesize},
 title style={font=\small},
 legend style={font=\footnotesize,draw=none,fill=none},
 every axis plot/.append style={thick,mark size=2pt}]
\nextgroupplot[title={(a) Simple checkable sets},xlabel={Number of states},
 ylabel={Permitted models admitted (\%)},ymin=0,ymax=100,xtick={3,4,5},
 legend pos=north east]
\addplot+[color=allowblue,mark=*,solid] coordinates {""" + series(cov["safety"]) + r"""};
\addlegendentry{Safety}
\addplot+[color=denyred,mark=square*,dashed] coordinates {""" + series(cov["confidentiality"]) + r"""};
\addlegendentry{Confidentiality}
\nextgroupplot[title={(b) Late violations (horizon 8)},xlabel={Program length},
 ylabel={False permissions per 10{,}000},ymin=0,symbolic x coords={""" + symbolic + r"""},xtick=data,
 legend pos=north west]
\addplot+[color=allowblue,mark=*,solid] coordinates {""" + series(fp_rate["safety"]) + r"""};
\addlegendentry{Safety}
\addplot+[color=denyred,mark=square*,dashed] coordinates {""" + series(fp_rate["confidentiality"]) + r"""};
\addlegendentry{Confidentiality}
\nextgroupplot[title={(c) Sound certificates (horizon 8)},xlabel={Program length},
 ylabel={Resolved programs certified (\%)},ymin=0,ymax=100,symbolic x coords={""" + symbolic + r"""},xtick=data,
 legend style={at={(0.97,0.5)},anchor=east}]
\addplot+[color=allowblue,mark=*,solid] coordinates {""" + series(cert_share["safety"]) + r"""};
\addlegendentry{Safety}
\addplot+[color=denyred,mark=square*,dashed] coordinates {""" + series(cert_share["confidentiality"]) + r"""};
\addlegendentry{Confidentiality}
\end{groupplot}
""" + END
    path = args.output / "experiments.tex"
    path.write_text(source, encoding="utf-8")
    if args.compile:
        engine = shutil.which("pdflatex")
        if not engine:
            raise SystemExit("pdflatex is required for --compile")
        proc = subprocess.run([engine, "-interaction=nonstopmode", "-halt-on-error", path.name],
                              cwd=str(args.output), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if proc.returncode:
            raise SystemExit(proc.stdout.decode("utf-8", errors="replace"))
    print(path.name + (" and PDF" if args.compile else ""))
    for norm in ("safety", "confidentiality"):
        print(norm, "false permissions per 10,000 at H=%s:" % H_REF, fp_rate[norm])
        print(norm, "certified share at H=%s:" % H_REF, cert_share[norm])


if __name__ == "__main__":
    main()
