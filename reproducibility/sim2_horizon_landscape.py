#!/usr/bin/env python3
"""Simulation 2: for which (program length L, horizon H) does the bounded
safety/confidentiality test err?  Random register-machine programs over
registers r0-r2 and constants 0-7 (as in the article's Experiment C), using
the article's own interpreter `trace` and sound reference labels
(halt / repeated configuration / stable-cycle certificate / syntactic
rules).  Programs none of these settles are 'unresolved' and excluded.
"""
import csv, json, random, sys
from pathlib import Path
from multiprocessing import Pool
import importlib.util

HERE = Path(__file__).resolve().parent
REPRO = HERE if (HERE / "run_extensions.py").exists() else HERE.parent / "proj" / "reproducibility"
def load(name):
    spec = importlib.util.spec_from_file_location(name, REPRO / f"{name}.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
base = load("run_simulations"); ext = load("run_extensions")

SEED = 20261020
SAMPLES = 200000
LENGTHS = tuple(range(4, 25, 2))
HORIZONS = [2 ** k for k in range(2, 13)]        # 4 .. 4096
TRUTH_BUDGET = 5000
REGS, CONSTS = (0, 1, 2), tuple(range(8))
OUT = HERE / "sim2_out"; OUT.mkdir(exist_ok=True)

def options(length, last):
    targets = range(length)
    if last:
        return [("RETURN", r) for r in REGS] + [("JMP", l) for l in targets]
    o = [("LOAD", r, k) for r in REGS for k in CONSTS]
    o += [("MOV", i, j) for i in REGS for j in REGS]
    o += [("INC", r) for r in REGS]
    o += [("DECJZ", r, l) for r in REGS for l in targets]
    o += [("EQJUMP", r, k, l) for r in REGS for k in CONSTS for l in targets]
    o += [("JMP", l) for l in targets]
    o += [("PUB", r) for r in REGS]
    o += [("BAD",)]
    o += [("RETURN", r) for r in REGS]
    return o

def work(length):
    rng = random.Random(SEED * 1000 + length)
    body, tail = options(length, False), options(length, True)
    lab = dict(safety=[0, 0, 0], conf=[0, 0, 0])      # permitted, forbidden, unresolved
    err = {h: dict(s_fp=0, c_fp=0, c_fn=0, s_cert=0, c_cert=0) for h in HORIZONS}
    first_bad, max_fb = [], 0
    for _ in range(SAMPLES):
        code = [rng.choice(body) for _ in range(length - 1)] + [rng.choice(tail)]
        runs = [ext.trace(code, n, TRUTH_BUDGET) for n in (0, 1)]
        has_bad = any(i[0] == "BAD" for i in code)
        safe = ext.safety_truth(runs[0])
        if safe is None and not has_bad: safe = True
        conf = ext.confidentiality_truth(*runs)
        indep = base.input_independent(code)
        if conf is None and indep: conf = True
        for k, t in (("safety", safe), ("conf", conf)):
            lab[k][2 if t is None else (0 if t else 1)] += 1
        fb = ext.first_bad_step(runs[0])
        if safe is False and fb:
            first_bad.append(fb); max_fb = max(max_fb, fb)
        for h in HORIZONS:
            e = err[h]
            seen_bad = fb is not None and fb <= h
            if safe is not None:
                e["s_fp"] += (safe is False) and not seen_bad
                e["s_cert"] += seen_bad or not has_bad
            if conf is not None:
                p0, p1 = (ext.prefix_by(r, h, "pub") for r in runs)
                permits = p0 == p1
                e["c_fp"] += permits and not conf
                e["c_fn"] += (not permits) and conf
                common = min(len(p0), len(p1))
                done = [r["kind"] == "halted" and r["halt_step"] <= h for r in runs]
                v = None
                if p0[:common] != p1[:common]: v = False
                elif (done[0] and len(p1) > len(p0)) or (done[1] and len(p0) > len(p1)): v = False
                elif done[0] and done[1]: v = p0 == p1
                elif indep: v = True
                e["c_cert"] += v is not None
    rows = []
    for h in HORIZONS:
        e = err[h]
        rows.append(dict(length=length, horizon=h, programs=SAMPLES,
            safety_permitted=lab["safety"][0], safety_forbidden=lab["safety"][1], safety_unresolved=lab["safety"][2],
            conf_permitted=lab["conf"][0], conf_forbidden=lab["conf"][1], conf_unresolved=lab["conf"][2],
            safety_false_permissions=e["s_fp"], conf_false_permissions=e["c_fp"], conf_false_prohibitions=e["c_fn"],
            safety_certified=e["s_cert"], conf_certified=e["c_cert"]))
    hist = {}
    for fb in first_bad: hist[fb] = hist.get(fb, 0) + 1
    meta = dict(length=length, max_first_bad_step=max_fb, n_forbidden=len(first_bad),
                first_bad_hist={str(k): v for k, v in sorted(hist.items())})
    return rows, meta

if __name__ == "__main__":
    with Pool(min(10, len(LENGTHS))) as pool:
        results = pool.map(work, LENGTHS)
    rows = [r for rs, _ in results for r in rs]
    metas = [m for _, m in results]
    with (OUT / "landscape.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    (OUT / "first_bad_meta.json").write_text(json.dumps(metas, indent=1))
    for m in metas:
        print(m["length"], "max first BAD step:", m["max_first_bad_step"], "forbidden:", m["n_forbidden"])
