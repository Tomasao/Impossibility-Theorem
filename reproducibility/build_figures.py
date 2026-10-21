#!/usr/bin/env python3
"""Build editable English PGFPlots figures from the archived CSV data.

Python 3.9+, standard library. PDF output additionally needs pdflatex.
No plotting values are hard-coded: all plotted counts come from CSV files.
"""
import argparse
import csv
import shutil
import subprocess
from pathlib import Path

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


def rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def coords(data, x, y):
    return " ".join("(%s,%s)" % (r[x], r[y]) for r in data)


def plots(data, x, legend=False):
    pieces = []
    for field, label, style in [
        ("false_permissions", "False permissions", "color=allowblue,mark=*,solid"),
        ("false_prohibitions", "False prohibitions", "color=denyred,mark=square*,dashdotted"),
        ("certificate_unknown", "Uncertified", "color=certorange,mark=triangle*,dashed"),
    ]:
        pieces.append(r"\addplot+[%s,thick,mark size=2pt] coordinates {%s};" %
                      (style, coords(data, x, field)))
        if legend:
            pieces.append(r"\addlegendentry{%s}" % label)
    return "\n".join(pieces)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path,
                        default=Path(__file__).resolve().parent / "data")
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parent / "figures")
    parser.add_argument("--compile", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    finite = rows(args.data / "finite_summary.csv")
    labels = dict(safety="Safety", confidentiality="Confidentiality", response="Response")
    finite_source = PREAMBLE + r"""\pgfkeys{/pgf/number format/1000 sep={}}
\begin{axis}[width=15cm,height=6.4cm,ybar,bar width=18pt,
 symbolic x coords={Safety,Confidentiality,Response},xtick=data,
 enlarge x limits=0.24,ymin=0,ymax=2850,
 ylabel={Number of models},grid=major,grid style={gray!15},
 legend style={at={(0.5,1.04)},anchor=south,legend columns=2,draw=none},
 nodes near coords,every node near coord/.append style={font=\small},
 tick label style={font=\small},label style={font=\small}]
"""
    for field, color, label in [("permitted", "allowblue", "Permitted"),
                                ("forbidden", "denyred", "Forbidden")]:
        points = " ".join("(%s,%s)" % (labels[r["norm"]], r[field]) for r in finite)
        finite_source += r"\addplot+[fill=%s,draw=%s] coordinates {%s};" % (color, color, points)
        finite_source += "\n" + r"\addlegendentry{%s}" % label + "\n"
    finite_source += "\\end{axis}\n" + END
    safety = rows(args.data / "safety_summary.csv")
    conf = rows(args.data / "confidentiality_summary.csv")
    response = rows(args.data / "response_summary.csv")
    bounded_source = PREAMBLE + r"""\begin{groupplot}[
 group style={group size=1 by 3,vertical sep=1.9cm},
 width=15cm,height=4.6cm,xmode=log,log basis x=2,
 axis lines=left,ymin=0,grid=major,grid style={gray!15},
 ylabel={Number of cases},title style={font=\small},
 tick label style={font=\small},label style={font=\small},
 legend style={at={(0.5,1.28)},anchor=south,legend columns=3,draw=none,font=\small}]
\nextgroupplot[title={(a) Safety: 14 candidates},ymax=16,ytick={0,4,8,12,16},
 xmin=4,xmax=4096,xtick={4,16,64,256,1024,4096},
 xticklabels={4,16,64,256,1024,4096},xlabel={Horizon (virtual transitions)}]
""" + plots(safety, "horizon", legend=True) + "\n" + r"""\nextgroupplot[
 title={(b) Confidentiality: 25 candidates},ymax=26,ytick={0,5,10,15,20,25},
 xmin=4,xmax=4096,xtick={4,16,64,256,1024,4096},
 xticklabels={4,16,64,256,1024,4096},xlabel={Horizon (virtual transitions)}]
""" + plots(conf, "horizon") + "\n" + r"""\nextgroupplot[
 title={(c) Response: 25 candidates; horizon 64},ymax=26,ytick={0,5,10,15,20,25},
 xmin=1,xmax=2048,xtick={1,4,16,64,256,1024,2048},
 xticklabels={1,4,16,64,256,1024,2048},xlabel={Number of tested inputs}]
""" + plots(response, "input_count") + "\n\\end{groupplot}\n" + END
    files = [("finite_models", finite_source), ("bounded_observation", bounded_source)]
    for name, source in files:
        path = args.output / (name + ".tex")
        path.write_text(source, encoding="utf-8")
        if args.compile:
            engine = shutil.which("pdflatex")
            if not engine:
                raise SystemExit("pdflatex is required for --compile")
            proc = subprocess.run([engine, "-interaction=nonstopmode", "-halt-on-error",
                                   path.name], cwd=str(args.output),
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if proc.returncode:
                raise SystemExit(proc.stdout.decode("utf-8", errors="replace"))
        print(path.name + (" and PDF" if args.compile else ""))


if __name__ == "__main__":
    main()
