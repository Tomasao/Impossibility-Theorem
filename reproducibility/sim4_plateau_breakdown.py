#!/usr/bin/env python3
"""Simulation 4: what are the compliant programs that the bounded
confidentiality test forbids at every horizon?  Same population and labels
as sim2; for each false prohibition at H in {64, 1024, 4096} record the
termination status of the two runs (halted / repeated configuration /
stable cycle) and whether a run publishes an infinite periodic sequence."""
import csv, random, sys
from pathlib import Path
from multiprocessing import Pool
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sim2_horizon_landscape as s2
ext, base = s2.ext, s2.base
HS = (64, 1024, 4096)

def work(length):
    rng = random.Random(s2.SEED * 1000 + length)
    body, tail = s2.options(length, False), s2.options(length, True)
    out = {h: dict(false_prohibitions=0, both_halted=0, some_run_publishes_forever=0,
                   both_publish_forever=0, compliant_both_halted_within_H=0,
                   compliant_both_halted_within_H_errors=0) for h in HS}
    for _ in range(s2.SAMPLES):
        code = [rng.choice(body) for _ in range(length - 1)] + [rng.choice(tail)]
        runs = [ext.trace(code, n, s2.TRUTH_BUDGET) for n in (0, 1)]
        conf = ext.confidentiality_truth(*runs)
        if conf is None and base.input_independent(code): conf = True
        if conf is not True: continue
        forms = [ext.public_form(r) for r in runs]
        forever = [f[0] == "periodic" for f in forms]
        for h in HS:
            p0, p1 = (ext.prefix_by(r, h, "pub") for r in runs)
            halted_in_h = all(r["kind"] == "halted" and r["halt_step"] <= h for r in runs)
            o = out[h]
            if halted_in_h:
                o["compliant_both_halted_within_H"] += 1
                o["compliant_both_halted_within_H_errors"] += (p0 != p1)
            if p0 != p1:
                o["false_prohibitions"] += 1
                o["both_halted"] += all(r["kind"] == "halted" for r in runs)
                o["some_run_publishes_forever"] += any(forever)
                o["both_publish_forever"] += all(forever)
    return [dict(length=length, horizon=h, **v) for h, v in out.items()]

if __name__ == "__main__":
    with Pool(10) as pool:
        res = pool.map(work, s2.LENGTHS)
    rows = [r for rs in res for r in rs]
    p = Path(__file__).resolve().parent / "sim4_plateau_breakdown.csv"
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    tot = {h: dict(fp=0, bh=0, sf=0, bf=0, ch=0, che=0) for h in HS}
    for r in rows:
        t = tot[r["horizon"]]; t["fp"] += r["false_prohibitions"]; t["bh"] += r["both_halted"]
        t["sf"] += r["some_run_publishes_forever"]; t["bf"] += r["both_publish_forever"]
        t["ch"] += r["compliant_both_halted_within_H"]; t["che"] += r["compliant_both_halted_within_H_errors"]
    for h, t in tot.items():
        print(f"H={h}: false prohibitions {t['fp']}; both runs halted {t['bh']}; some run publishes forever {t['sf']}; "
              f"both publish forever {t['bf']}; compliant programs with both runs halted within H {t['ch']} -> errors {t['che']}")
