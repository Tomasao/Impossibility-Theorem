#!/usr/bin/env python3
"""Experiment C (v13): sampled register-machine programs of length 6, 8, 10 and 12.
Python >= 3.9, standard library only.

The exhaustive population of run_extensions.py (programs of length 1-4 over
registers r0, r1 and constants 0, 1) contains no program whose first forbidden
operation occurs after step 6. This experiment asks whether longer programs,
which can contain counting loops, produce later violations, and how the bounded
tests and the sound certificate methods behave on them.

For each length L in (6, 8, 10, 12), SAMPLES programs are drawn with a fixed seed. Each of
the first L-1 instructions is drawn uniformly from the instruction options over
registers r0, r1, r2 and constants 0..7; the last instruction is RETURN or JMP,
so that control never falls off the end. Reference labels, bounded tests and
certificate methods are exactly those of run_extensions.py: reference labels
come only from complete runs, repeated configurations, the sound stable-cycle
certificate, or the two syntactic rules; a timeout never defines a label.

This script does not modify the outputs of run_simulations.py or
run_extensions.py.
"""
import argparse
import importlib.util
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = load("run_simulations")
ext = load("run_extensions")

SEED = 20261013
SAMPLES = 50000
LENGTHS = (6, 8, 10, 12)
REGS = (0, 1, 2)
CONSTS = tuple(range(8))
HORIZONS = ext.HORIZONS
TRUTH_BUDGET = ext.TRUTH_BUDGET
STEP_BUCKETS = (4, 8, 16, 32, 64, 128, 256, 512, 1024, 5000)


def instruction_options(length, last):
    targets = range(length)
    if last:
        return [("RETURN", r) for r in REGS] + [("JMP", l) for l in targets]
    options = [("LOAD", r, k) for r in REGS for k in CONSTS]
    options += [("MOV", i, j) for i in REGS for j in REGS]
    options += [("INC", r) for r in REGS]
    options += [("DECJZ", r, l) for r in REGS for l in targets]
    options += [("EQJUMP", r, k, l) for r in REGS for k in CONSTS for l in targets]
    options += [("JMP", l) for l in targets]
    options += [("PUB", r) for r in REGS]
    options += [("BAD",)]
    options += [("RETURN", r) for r in REGS]
    return options


def sample_programs(length, rng):
    body = instruction_options(length, last=False)
    tail = instruction_options(length, last=True)
    for _ in range(SAMPLES):
        yield [rng.choice(body) for _ in range(length - 1)] + [rng.choice(tail)]


def has_backward_jump(code):
    for index, instruction in enumerate(code):
        op = instruction[0]
        target = None
        if op in ("DECJZ", "JMP"):
            target = instruction[-1]
        elif op == "EQJUMP":
            target = instruction[3]
        if target is not None and target <= index:
            return True
    return False


def bucket(step):
    for b in STEP_BUCKETS:
        if step <= b:
            return b
    return STEP_BUCKETS[-1]


def run_length(length, rng):
    labels = dict(safety=dict(permitted=0, forbidden=0, unresolved=0),
                  confidentiality=dict(permitted=0, forbidden=0, unresolved=0))
    errors = {h: dict(safety_fp=0, conf_fp=0, conf_fn=0,
                      safety_cert=0, conf_cert=0,
                      safety_cert_err=0, conf_cert_err=0) for h in HORIZONS}
    latest_first_bad = 0
    first_bad_hist = {str(b): 0 for b in STEP_BUCKETS}
    late = dict(forbidden_first_bad_after_8=0, of_which_with_backward_jump=0)
    checked_against_base = 0
    count = 0
    for code in sample_programs(length, rng):
        count += 1
        runs = [ext.trace(code, n, TRUTH_BUDGET) for n in (0, 1)]
        if count % 997 == 0:               # cross-check semantics with run_vm
            for n, run in zip((0, 1), runs):
                reference = base.run_vm(code, n, TRUTH_BUDGET)
                bad = [s for s, k, _ in run["events"] if k == "bad"]
                pubs = [v for _, k, v in run["events"] if k == "pub"]
                if run["kind"] == "halted":
                    assert reference["halted"] and reference["bad_steps"] == bad
                    assert reference["public"] == pubs
                checked_against_base += 1
        safe = ext.safety_truth(runs[0])
        conf = ext.confidentiality_truth(*runs)
        has_bad_instruction = any(ins[0] == "BAD" for ins in code)
        if safe is None and not has_bad_instruction:
            safe = True
        if conf is None and base.input_independent(code):
            conf = True
        for norm, truth in (("safety", safe), ("confidentiality", conf)):
            key = "unresolved" if truth is None else ("permitted" if truth else "forbidden")
            labels[norm][key] += 1
        fb = ext.first_bad_step(runs[0])
        if safe is False and fb:
            latest_first_bad = max(latest_first_bad, fb)
            first_bad_hist[str(bucket(fb))] += 1
            if fb > 8:
                late["forbidden_first_bad_after_8"] += 1
                late["of_which_with_backward_jump"] += has_backward_jump(code)
        independent = base.input_independent(code)
        for h in HORIZONS:
            e = errors[h]
            observed_bad = fb is not None and fb <= h
            if safe is not None:
                if safe is False and not observed_bad:
                    e["safety_fp"] += 1
                certified = observed_bad or not has_bad_instruction
                if certified:
                    e["safety_cert"] += 1
                    e["safety_cert_err"] += (not observed_bad) != safe
            if conf is not None:
                p0, p1 = (ext.prefix_by(r, h, "pub") for r in runs)
                test_permits = p0 == p1
                e["conf_fp"] += test_permits and not conf
                e["conf_fn"] += (not test_permits) and conf
                common = min(len(p0), len(p1))
                done = [r["kind"] == "halted" and r["halt_step"] <= h for r in runs]
                verdict = None
                if p0[:common] != p1[:common]:
                    verdict = False
                elif (done[0] and len(p1) > len(p0)) or (done[1] and len(p0) > len(p1)):
                    verdict = False
                elif done[0] and done[1]:
                    verdict = p0 == p1
                elif independent:
                    verdict = True
                if verdict is not None:
                    e["conf_cert"] += 1
                    e["conf_cert_err"] += verdict != conf
    rows = []
    for h in HORIZONS:
        e = errors[h]
        for norm in ("safety", "confidentiality"):
            l = labels[norm]
            rows.append(dict(length=length, norm=norm, horizon=h, programs=count,
                             permitted=l["permitted"], forbidden=l["forbidden"],
                             unresolved=l["unresolved"],
                             false_permissions=e["safety_fp"] if norm == "safety" else e["conf_fp"],
                             false_prohibitions=0 if norm == "safety" else e["conf_fn"],
                             certified=e["safety_cert"] if norm == "safety" else e["conf_cert"],
                             certificate_errors=e["safety_cert_err"] if norm == "safety" else e["conf_cert_err"]))
    meta = dict(programs=count, latest_first_bad_step=latest_first_bad,
                first_bad_step_histogram_upper_bounds=first_bad_hist,
                late_violations=late, semantic_cross_checks=checked_against_base)
    return rows, meta


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "data_sampled")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    rows, meta = [], dict(seed=SEED, samples_per_length=SAMPLES, lengths=list(LENGTHS),
                          registers=list(REGS), constants=list(CONSTS),
                          truth_budget=TRUTH_BUDGET, by_length={})
    for length in LENGTHS:
        length_rows, length_meta = run_length(length, rng)
        rows.extend(length_rows)
        meta["by_length"][str(length)] = length_meta
    for row in rows:
        assert row["certificate_errors"] == 0
    ext.write_csv(args.output / "sampled_programs_summary.csv", rows)
    (args.output / "sampled_programs_meta.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
