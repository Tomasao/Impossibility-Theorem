#!/usr/bin/env python3
"""build_fig4.py -- Figure 4 of v14: what bounded tests get wrong on 2.2 M random plans.

  (a) safety: % of unsafe plans that the bounded test permits, by program length L
      (rows, 4..24 instructions) and horizon H (columns, 4..4096 steps); log colour
      scale, grey = none, value printed in every cell;
  (b) confidentiality: % of compliant plans wrongly forbidden vs H, one line per L
      (light -> dark blue = L 4 -> 24), direct labels for L = 4 and L = 24;
  (c) the horizon a bounded safety test needs: median, 99th and 99.9th percentile of
      the first-violation step vs L (lines with markers); maximum as faint markers.

Inputs (default directory data/, next to this script):
  sim2_landscape.csv          Simulation 2 counts per (length, horizon)
  sim2_required_horizon.csv   percentiles of the first-violation step per length
  sim4_plateau_breakdown.csv  composition of the confidentiality plateau (caption numbers)
  sim2_first_bad_meta.json    OPTIONAL first-violation histograms; if present, the claim
                              "99 % of violations by the p99 step" is verified exactly
Outputs (next to this script):
  fig4_simulations.pdf, fig4_simulations.png (300 dpi, about 180 mm wide)
  fig4_numbers.json           every number a caption may quote, computed from the inputs

Every panel title is checked against every row of the data before drawing; the script
stops with an error if a title would be false.  After saving, a bounding-box overlap
check of all text (figure-style skill, section 9.1) is run and reported.
Usage (from figures_v14/):  python build_fig4.py [--data data] [--out .]
Requires numpy, pandas, matplotlib (tested with matplotlib 3.x).
"""
import argparse
import json
import logging
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, LogNorm, to_rgb

HERE = Path(__file__).resolve().parent
MM = 1 / 25.4
BASE, SECOND, TICK = 8, 7, 6          # role-mapped size ladder (titles/labels, annotations, ticks)
BLUE_DARK = "#00588A"                 # allowblue of the TikZ figures, RGB(0,88,138)


def apply_style():
    """Mirror of figure-style apply_figure_style(sizes=(8, 7, 6)), serif CM fonts to match TeX."""
    mpl.rcParams.update({
        "font.family": "serif", "font.serif": ["cmr10", "DejaVu Serif"],
        "mathtext.fontset": "cm", "axes.formatter.use_mathtext": True, "axes.unicode_minus": False,
        "font.size": BASE, "axes.labelsize": BASE, "axes.titlesize": BASE,
        "legend.fontsize": SECOND, "xtick.labelsize": TICK, "ytick.labelsize": TICK,
        "axes.linewidth": 0.6, "xtick.direction": "out", "ytick.direction": "out",
        "xtick.major.size": 3, "ytick.major.size": 3, "xtick.minor.size": 1.6, "ytick.minor.size": 1.6,
        "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "xtick.minor.width": 0.5, "ytick.minor.width": 0.5,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False,
        "legend.frameon": False, "figure.dpi": 200, "savefig.dpi": 300, "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02, "axes.titleweight": "normal", "axes.titlelocation": "left",
        "lines.linewidth": 1.2, "patch.linewidth": 0.6, "pdf.fonttype": 42, "ps.fonttype": 42,
    })


# ----------------------------------------------------------------------------- data
def load(data_dir):
    d = Path(data_dir)
    land = pd.read_csv(d / "sim2_landscape.csv")
    req = pd.read_csv(d / "sim2_required_horizon.csv").sort_values("length")
    plateau = pd.read_csv(d / "sim4_plateau_breakdown.csv")
    hist_path = d / "sim2_first_bad_meta.json"
    hist = json.loads(hist_path.read_text()) if hist_path.exists() else None
    return land, req, plateau, hist


def derive(land, req, plateau, hist):
    """All plotted values and all claims, computed from the inputs only."""
    for col in ("safety_forbidden", "conf_permitted"):        # truth labels must not depend on H
        if not (land.groupby("length")[col].nunique() == 1).all():
            sys.exit(f"{col} varies with the horizon; the denominators are ill-defined")
    lengths = sorted(land.length.unique())
    horizons = sorted(land.horizon.unique())
    saf = 100 * land.pivot(index="length", columns="horizon", values="safety_false_permissions") \
        / land.groupby("length").safety_forbidden.first().values[:, None]
    conf = 100 * land.pivot(index="length", columns="horizon", values="conf_false_prohibitions") \
        / land.groupby("length").conf_permitted.first().values[:, None]
    saf_counts = land.pivot(index="length", columns="horizon", values="safety_false_permissions")
    conf_counts = land.pivot(index="length", columns="horizon", values="conf_false_prohibitions")

    # (a) smallest horizon from which no length has a false permission
    zero_from = [H for H in horizons if (saf_counts.loc[:, [h for h in horizons if h >= H]] == 0).all().all()]
    if not zero_from:
        sys.exit("panel (a) title: some false permission remains at the largest horizon")
    h_clear = min(zero_from)
    if not (saf_counts.loc[:, [h for h in horizons if h < h_clear]] > 0).any().any():
        sys.exit("panel (a) title: no false permission at any short horizon")
    # cross-check with the required-horizon table
    if not (req.set_index("length").min_errorfree_horizon_tested.max() == h_clear):
        sys.exit("panel (a): smallest error-free horizon disagrees with sim2_required_horizon.csv")
    if not (req.set_index("length").unsafe_programs == land.groupby("length").safety_forbidden.first()).all():
        sys.exit("unsafe-program counts disagree between the two Simulation 2 tables")

    # (b) the error is never removed: positive at every (L, H), in particular at the largest H
    if not (conf_counts > 0).all().all():
        sys.exit("panel (b) title: some (length, horizon) has no wrongly forbidden plan")

    # (c) the 99th-percentile step never decreases with length and ends higher than it starts
    p99 = req.p99.to_numpy()
    if not (np.all(np.diff(p99) >= 0) and p99[-1] > p99[0]):
        sys.exit("panel (c) title: the 99th percentile does not grow with length")
    coverage = None
    if hist is not None:
        coverage = {}
        for m in hist:
            h = {int(k): v for k, v in m["first_bad_hist"].items()}
            steps = np.repeat(list(h.keys()), list(h.values()))
            r = req.set_index("length").loc[m["length"]]
            if len(steps) != r.unsafe_programs:
                sys.exit(f"histogram size disagrees with unsafe_programs at L = {m['length']}")
            coverage[int(m["length"])] = dict(p50=float(np.mean(steps <= r.median_first_bad)),
                                              p99=float(np.mean(steps <= r.p99)),
                                              p999=float(np.mean(steps <= r.p999)))
        catches_99 = all(c["p99"] >= 0.99 for c in coverage.values())
    else:
        catches_99 = None
    title_c = ("The horizon that catches 99% of\nviolations grows with length" if catches_99
               else "The 99th-percentile violation step\ngrows with length")

    # numbers a caption may quote (sim4 plateau composition included)
    pl = plateau.groupby("horizon")[["false_prohibitions", "both_publish_forever",
                                     "compliant_both_halted_within_H",
                                     "compliant_both_halted_within_H_errors"]].sum()
    numbers = dict(
        programs_per_length=int(land.programs.iloc[0]), lengths=[int(x) for x in lengths],
        horizons=[int(x) for x in horizons], programs_total=int(land.groupby("length").programs.first().sum()),
        unsafe_per_length={int(k): int(v) for k, v in land.groupby("length").safety_forbidden.first().items()},
        compliant_per_length={int(k): int(v) for k, v in land.groupby("length").conf_permitted.first().items()},
        safety_unresolved_per_length={int(k): int(v) for k, v in land.groupby("length").safety_unresolved.first().items()},
        conf_unresolved_per_length={int(k): int(v) for k, v in land.groupby("length").conf_unresolved.first().items()},
        a_horizon_with_no_false_permission=int(h_clear),
        a_max_pct=float(saf.to_numpy().max()), a_min_nonzero_pct=float(saf.to_numpy()[saf.to_numpy() > 0].min()),
        b_min_pct=float(conf.to_numpy().min()), b_max_pct=float(conf.to_numpy().max()),
        b_pct_at_max_horizon={int(L): float(conf.loc[L, max(horizons)]) for L in lengths},
        c_median_range=[int(req.median_first_bad.min()), int(req.median_first_bad.max())],
        c_p99_range=[int(req.p99.min()), int(req.p99.max())],
        c_p999_range=[int(req.p999.min()), int(req.p999.max())],
        c_max_range=[int(req.max_first_bad.min()), int(req.max_first_bad.max())],
        c_percentile_method="numpy.percentile(method='lower') (from the lineage of sim2_required_horizon.csv)",
        c_coverage_by_length=coverage,
        sim4_by_horizon={int(H): {k: int(v) for k, v in row.items()} for H, row in pl.iterrows()},
        titles=dict(a=f"Safety: short horizons let unsafe plans\nthrough; none get through at $H \\geq {h_clear}$",
                    b="Confidentiality: longer horizons\nnever remove this error", c=title_c),
    )
    return dict(lengths=lengths, horizons=horizons, saf=saf, conf=conf, req=req,
                h_clear=h_clear, title_c=title_c, numbers=numbers)


# ----------------------------------------------------------------------------- drawing
def fmt_cell(v):
    if v == 0:
        return "0"
    if v >= 10:
        return f"{v:.0f}"
    if v >= 1:
        return f"{v:.1f}"
    if v >= 0.005:
        return f"{v:.2f}"
    return "<0.01"


def rel_lum(rgb):
    c = np.array(rgb, float)
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = sorted([rel_lum(a), rel_lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def pick_text(bg):
    cb, cw = contrast(bg, (0, 0, 0)), contrast(bg, (1, 1, 1))
    return ("black", cb) if cb >= cw else ("white", cw)


def add_axes_mm(fig, W, H, left, bottom, width, height):
    return fig.add_axes([left / W, bottom / H, width / W, height / H])


def panel_letter(fig, ax, letter, dx_mm, W):
    """Bold '(a)' to the left of a left-aligned two-line title (outside the axes)."""
    x0 = ax.get_position().x0 - dx_mm / W
    ax.text(x0, 1.0, f"({letter})", transform=mpl.transforms.blended_transform_factory(fig.transFigure, ax.transAxes),
            fontsize=BASE + 1, fontfamily="cmb10", va="bottom", ha="left")


def repel(values, min_gap):
    """Spread label positions (sorted ascending in display units) to at least min_gap apart."""
    order = np.argsort(values)
    pos = np.array(values, float)[order]
    for i in range(1, len(pos)):
        pos[i] = max(pos[i], pos[i - 1] + min_gap)
    out = np.empty_like(pos)
    out[order] = pos
    return out


def make_figure(D):
    W, H = 182.0, 74.0
    fig = plt.figure(figsize=(W * MM, H * MM))
    axA = add_axes_mm(fig, W, H, 11.0, 12.0, 50.6, 50.0)
    axCB = add_axes_mm(fig, W, H, 63.2, 12.0, 2.2, 50.0)
    axB = add_axes_mm(fig, W, H, 89.5, 12.0, 32.0, 50.0)
    axC = add_axes_mm(fig, W, H, 139.5, 12.0, 27.0, 50.0)
    lengths, horizons = D["lengths"], D["horizons"]

    # ---------------- (a) heatmap
    saf = D["saf"].loc[lengths, horizons].to_numpy()
    nz = saf[saf > 0]
    vmin = 10 ** math.floor(math.log10(nz.min()))
    vmax = 10 ** math.ceil(math.log10(nz.max()))
    base_cmap = plt.get_cmap("YlOrRd")
    cmap = LinearSegmentedColormap.from_list("ylorrd_trunc", base_cmap(np.linspace(0.12, 0.92, 256)))
    cmap.set_bad("#dddddd")
    norm = LogNorm(vmin=vmin, vmax=vmax)
    masked = np.ma.masked_equal(saf, 0)
    im = axA.imshow(masked, origin="lower", aspect="auto", cmap=cmap, norm=norm, interpolation="nearest")
    for i, L in enumerate(lengths):
        for j, Hz in enumerate(horizons):
            v = saf[i, j]
            if v == 0:
                colour = "#555555"
            else:
                colour, _ = pick_text(cmap(norm(v))[:3])
            axA.text(j, i, fmt_cell(v), ha="center", va="center", fontsize=TICK, color=colour)
    axA.set_xticks(range(len(horizons)))
    axA.set_xticklabels([str(h) if k % 2 == 0 else "" for k, h in enumerate(horizons)])
    axA.set_yticks(range(len(lengths)))
    axA.set_yticklabels([str(L) for L in lengths])
    axA.set_xlabel("test horizon $H$ (steps)")
    axA.set_ylabel("plan length $L$ (instructions)")
    for s in axA.spines.values():
        s.set_visible(False)
    axA.tick_params(length=2)
    axA.set_title(D["numbers"]["titles"]["a"], pad=4)
    cb = fig.colorbar(im, cax=axCB)
    decades = [10 ** k for k in range(int(math.log10(vmin)), int(math.log10(vmax)) + 1)]
    cb.set_ticks(decades)
    cb.set_ticklabels([f"{d:g}" for d in decades])
    cb.minorticks_off()
    cb.outline.set_linewidth(0.5)
    cb.ax.tick_params(length=2)
    cb.set_label("unsafe plans permitted (%, log scale);\ngrey = none", fontsize=SECOND, labelpad=3)

    # ---------------- (b) confidentiality false prohibitions vs horizon
    conf = D["conf"].loc[lengths, horizons]
    ramp = plt.get_cmap("Blues")
    cols = {L: ramp(0.38 + 0.62 * k / (len(lengths) - 1)) for k, L in enumerate(lengths)}
    ends = {}
    for L in lengths:
        emph = L in (lengths[0], lengths[-1])
        axB.plot(horizons, conf.loc[L].to_numpy(), color=cols[L], lw=1.5 if emph else 0.8,
                 marker="o", ms=2.0 if emph else 1.4, zorder=3 if emph else 2)
        ends[L] = conf.loc[L, horizons[-1]]
    axB.set_xscale("log", base=2)
    axB.set_xlim(horizons[0] / 1.35, horizons[-1] * 1.35)
    axB.set_xticks(horizons[::2])
    axB.set_xticklabels([str(h) for h in horizons[::2]])
    axB.set_xticks(horizons[1::2], minor=True)
    axB.xaxis.set_minor_formatter(mpl.ticker.NullFormatter())
    ytop = math.ceil(conf.to_numpy().max() * 10 * 1.05) / 10
    axB.set_ylim(0, ytop)
    axB.set_yticks(np.round(np.arange(0, ytop + 1e-9, 0.1), 1))
    axB.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, p: "0" if v == 0 else f"{v:.1f}"))
    axB.set_xlabel("test horizon $H$ (steps)")
    axB.set_ylabel("compliant plans wrongly forbidden (%)")
    axB.set_title(D["numbers"]["titles"]["b"], pad=4)
    for L in (lengths[0], lengths[-1]):
        axB.annotate(f"$L = {L}$", xy=(horizons[-1], ends[L]), xytext=(4, 0), textcoords="offset points",
                     va="center", ha="left", fontsize=SECOND, color=cols[L] if L == lengths[-1] else ramp(0.62),
                     annotation_clip=False)

    # ---------------- (c) required horizon by length
    req = D["req"]
    Ls = req.length.to_numpy()
    series = [("median_first_bad", "median", "#7a7a7a", "o", 1.0, 2.6),
              ("p99", "99th pct.", "#111111", "s", 1.6, 2.6),
              ("p999", "99.9th pct.", "#a3a3a3", "^", 1.0, 2.8)]
    for col, _, colour, mk, lw, ms in series:
        axC.plot(Ls, req[col].to_numpy(), color=colour, marker=mk, lw=lw, ms=ms, zorder=3)
    axC.plot(Ls, req.max_first_bad.to_numpy(), ls="none", marker="x", ms=3.0, mew=0.8, color="#c4c4c4", zorder=2)
    axC.set_yscale("log", base=2)
    ymin = req.median_first_bad.min() / 1.35
    ymax = req.max_first_bad.max() * 1.35
    axC.set_ylim(ymin, ymax)
    yt = [2 ** k for k in range(math.ceil(math.log2(ymin)), math.floor(math.log2(ymax)) + 1)]
    axC.set_yticks(yt)
    axC.set_yticklabels([str(v) for v in yt])
    axC.yaxis.set_minor_locator(mpl.ticker.NullLocator())
    axC.set_xlim(Ls.min() - 1.2, Ls.max() + 1.2)
    axC.set_xticks(Ls[::2])
    axC.set_xticks(Ls[1::2], minor=True)
    axC.set_xlabel("plan length $L$ (instructions)")
    axC.set_ylabel("step at which the safe is first opened")
    axC.set_title(D["title_c"], pad=4)
    # direct labels at the right end, de-overlapped in display space
    names = [(c, n, colour) for c, n, colour, *_ in series] + [("max_first_bad", "maximum", "#9a9a9a")]
    fig.canvas.draw()
    ydisp = [axC.transData.transform((Ls[-1], req[c].iloc[-1]))[1] for c, _, _ in names]
    min_gap = SECOND * 1.25 * fig.dpi / 72
    ylab = repel(ydisp, min_gap)
    for (c, n, colour), yd in zip(names, ylab):
        _, yv = axC.transData.inverted().transform((0, yd))
        axC.annotate(n, xy=(Ls[-1], yv), xytext=(5, 0), textcoords="offset points", va="center", ha="left",
                     fontsize=SECOND, color=colour if colour != "#a3a3a3" else "#8a8a8a", annotation_clip=False)

    for ax, letter in ((axA, "a"), (axB, "b"), (axC, "c")):
        panel_letter(fig, ax, letter, 10.0, W)
    return fig, dict(a=axA, colorbar=axCB, b=axB, c=axC)


def overlap_check(fig):
    """Section 9.1 of the figure-style skill: visible text boxes must not overlap each other or spines."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    texts = [(t, t.get_window_extent(r)) for t in fig.findobj(mpl.text.Text)
             if t.get_text().strip() and t.get_visible()]
    spines = [(s, s.get_window_extent(r)) for ax in fig.axes for s in ax.spines.values() if s.get_visible()]
    ticklabels = {ax: set(ax.get_xticklabels(which="both") + ax.get_yticklabels(which="both")) for ax in fig.axes}
    overlaps = [(a.get_text(), b.get_text()) for i, (a, ba) in enumerate(texts) for b, bb in texts[i + 1:]
                if ba.overlaps(bb)]
    overlaps += [(t.get_text(), "spine") for t, bt in texts for s, bs in spines
                 if bt.overlaps(bs) and t not in ticklabels[s.axes]]
    fb = fig.bbox
    outside = [t.get_text() for t, bt in texts if bt.x0 < fb.x0 - 1 or bt.x1 > fb.x1 + 1 or bt.y0 < fb.y0 - 1 or bt.y1 > fb.y1 + 1]
    return overlaps, outside


def main():
    logging.getLogger("fontTools").setLevel(logging.ERROR)   # silence harmless font-timestamp notices
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", default=str(HERE.parent / "reproducibility"))
    ap.add_argument("--out", default=str(HERE))
    a = ap.parse_args()
    apply_style()
    D = derive(*load(a.data))
    fig, axes = make_figure(D)
    overlaps, outside = overlap_check(fig)
    out = Path(a.out)
    fig.savefig(out / "fig4_simulations.pdf")
    fig.savefig(out / "fig4_simulations.png", dpi=300)
    (out / "fig4_numbers.json").write_text(json.dumps(D["numbers"], indent=1))
    print(f"fig4: titles checked; (a) no false permission at H >= {D['h_clear']}; "
          f"(c) title = {D['title_c']!r}")
    print(f"fig4: text overlaps = {len(overlaps)}; text outside figure = {len(outside)}")
    for o in overlaps:
        print("  overlap:", o)
    for o in outside:
        print("  outside:", o)
    if overlaps or outside:
        sys.exit(1)


if __name__ == "__main__":
    main()
