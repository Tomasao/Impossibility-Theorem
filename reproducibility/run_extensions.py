#!/usr/bin/env python3
"""Additional deterministic experiments (v11). Python >= 3.9, standard library only.

Experiment A (separator coverage): for every deterministic finite-state model
with 3, 4 and 5 states, compare exact labels with simple decidable syntactic
admission sets (separators). Semantics are those of run_simulations.py.

Experiment B (exhaustive small programs): every valid register-machine program
of length 1-4 that uses registers r0 and r1 and constants 0 and 1. Reference
labels for safety (input 0) and confidentiality (inputs 0 and 1) are obtained
only from complete runs, repeated configurations, or a sound unconditional-cycle
certificate. Runs that none of these settles within the budget are reported as
unresolved and excluded from error counts. A timeout never defines a label.

This script does not modify the outputs of run_simulations.py.
"""
import argparse
import csv
import importlib.util
import itertools
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("base", ROOT / "run_simulations.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

HORIZONS = [2 ** k for k in range(2, 11)]   # 4,...,1024
TRUTH_BUDGET = 5000                          # steps per run for reference labels
STATE_COUNTS = (3, 4, 5)


def write_csv(path, rows):
    assert rows
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------- Experiment A
def fsm_choices(n):
    choices = [(event, nxt) for event in ("none", "bad", "pub0", "pub1")
               for nxt in range(n)]
    choices.extend([("return0", None), ("return1", None)])
    return choices


def fsm_safety_n(graph):
    q, seen = 0, set()
    while q not in seen:
        seen.add(q)
        event, nxt = graph[q]
        if event == "bad":
            return False
        if event.startswith("return"):
            return True
        q = nxt
    return True


def no_bad_anywhere(graph):
    return all(event != "bad" for event, _ in graph)


def no_publication_anywhere(graph):
    return all(not event.startswith("pub") for event, _ in graph)


def successor_graph_acyclic(graph):
    for start in range(len(graph)):
        q, seen = start, set()
        while True:
            event, nxt = graph[q]
            if event.startswith("return"):
                break
            if q in seen:
                return False
            seen.add(q)
            q = nxt
    return True


def separator_coverage():
    rows = []
    for n in STATE_COUNTS:
        stats = {key: dict(permitted=0, admitted=0, unsound=0)
                 for key in ("safety", "confidentiality", "response")}
        total = 0
        for graph in itertools.product(fsm_choices(n), repeat=n):
            total += 1
            # The base algorithms index initial states 0 and 1 and all states,
            # so they apply unchanged to n states.
            exact = dict(safety=fsm_safety_n(graph),
                         confidentiality=base.fsm_confidentiality(graph),
                         response=base.fsm_response(graph))
            admitted = dict(safety=no_bad_anywhere(graph),
                            confidentiality=no_publication_anywhere(graph),
                            response=successor_graph_acyclic(graph))
            for key in stats:
                stats[key]["permitted"] += exact[key]
                stats[key]["admitted"] += admitted[key]
                stats[key]["unsound"] += admitted[key] and not exact[key]
        assert total == (4 * n + 2) ** n
        names = dict(safety="no BAD event in any state",
                     confidentiality="no publication in any state",
                     response="successor graph has no cycle")
        for key, value in stats.items():
            assert value["unsound"] == 0
            rows.append(dict(states=n, models=total, norm=key,
                             separator=names[key],
                             permitted=value["permitted"],
                             admitted=value["admitted"],
                             coverage_percent=f"{100 * value['admitted'] / value['permitted']:.1f}",
                             unsound_admissions=value["unsound"]))
    # Consistency with the archived three-state counts of run_simulations.py.
    three = {r["norm"]: r["permitted"] for r in rows if r["states"] == 3}
    assert three == dict(safety=1850, confidentiality=1452, response=392)
    return rows


# ---------------------------------------------------------------- Experiment B
def instruction_options(length, last):
    targets = range(length)
    regs = (0, 1)
    consts = (0, 1)
    if last:
        return ([("RETURN", r) for r in regs] + [("JMP", l) for l in targets])
    options = [("LOAD", r, k) for r in regs for k in consts]
    options += [("MOV", i, j) for i in regs for j in regs]
    options += [("INC", r) for r in regs]
    options += [("DECJZ", r, l) for r in regs for l in targets]
    options += [("EQJUMP", r, k, l) for r in regs for k in consts for l in targets]
    options += [("JMP", l) for l in targets]
    options += [("PUB", r) for r in regs]
    options += [("BAD",)]
    options += [("RETURN", r) for r in regs]
    return options


def all_small_programs(max_length=4):
    for length in range(1, max_length + 1):
        body = instruction_options(length, last=False)
        tail = instruction_options(length, last=True)
        for prefix in itertools.product(body, repeat=length - 1):
            for final in tail:
                yield list(prefix) + [final]


def trace(code, n, budget):
    """Same transition semantics as run_simulations.run_vm, plus the final pc."""
    registers, pc = [n, 0, 0, 0], 0
    seen = {(pc, tuple(registers)): 0}
    events = []                      # (step, kind, value)
    for step in range(1, budget + 1):
        op, *args = code[pc]
        nxt = pc + 1
        if op == "LOAD":
            registers[args[0]] = args[1]
        elif op == "MOV":
            registers[args[0]] = registers[args[1]]
        elif op == "INC":
            registers[args[0]] += 1
        elif op == "DECJZ":
            if registers[args[0]] == 0:
                nxt = args[1]
            else:
                registers[args[0]] -= 1
        elif op == "EQJUMP":
            if registers[args[0]] == args[1]:
                nxt = args[2]
        elif op == "JMP":
            nxt = args[0]
        elif op == "PUB":
            events.append((step, "pub", registers[args[0]]))
        elif op == "BAD":
            events.append((step, "bad", None))
        elif op == "RETURN":
            return dict(kind="halted", events=events, halt_step=step)
        pc = nxt
        configuration = (pc, tuple(registers))
        if configuration in seen:
            return dict(kind="repeat", events=events,
                        cycle_start=seen[configuration], cycle_end=step)
        seen[configuration] = step
    # Sound stable-cycle certificate. (1) Continue from the current
    # configuration, recording every event, until the program counter repeats;
    # this locates a pc cycle entered at configuration E. (2) From E, execute
    # one further pass of the cycle, recording events and, at each conditional,
    # the value it tests. The pass must follow the same pc sequence and return
    # to the cycle start. (3) Each conditional must be stable: its register is
    # never written in the cycle; or it is an EQJUMP whose register the cycle
    # only increments and whose tested value already exceeds the constant; or it
    # is a DECJZ that read 0 and whose register no other cycle instruction
    # writes. Then every later pass repeats the same branches, so the run stays
    # in the cycle forever, and the recorded events are complete except for
    # repetitions of the cycle's own events.
    def step(q, regs, step_no, sink):
        op, *args = code[q]
        nxt = q + 1
        tested = None
        if op == "LOAD":
            regs[args[0]] = args[1]
        elif op == "MOV":
            regs[args[0]] = regs[args[1]]
        elif op == "INC":
            regs[args[0]] += 1
        elif op == "DECJZ":
            tested = regs[args[0]]
            if regs[args[0]] == 0:
                nxt = args[1]
            else:
                regs[args[0]] -= 1
        elif op == "EQJUMP":
            tested = regs[args[0]]
            if regs[args[0]] == args[1]:
                nxt = args[2]
        elif op == "JMP":
            nxt = args[0]
        elif op == "PUB":
            sink.append((step_no, "pub", regs[args[0]]))
        elif op == "BAD":
            sink.append((step_no, "bad", None))
        return nxt, tested
    regs = list(registers)
    q, step_no, path = pc, budget, []
    while q not in path:
        if len(path) > 2 * len(code) + 2 or code[q][0] == "RETURN":
            return dict(kind="unresolved", events=events)
        path.append(q)
        step_no += 1
        q, _ = step(q, regs, step_no, events)
    start = q
    cycle = path[path.index(start):]
    written_other = set()
    only_incremented = {}
    for idx in cycle:
        op, *args = code[idx]
        if op in ("LOAD", "MOV", "INC"):
            written_other.add(args[0])
            only_incremented[args[0]] = only_incremented.get(args[0], True) and op == "INC"
    decjz_regs = {code[idx][1] for idx in cycle if code[idx][0] == "DECJZ"}
    checked = []
    q2 = start
    for expected in cycle:
        if q2 != expected:
            return dict(kind="unresolved", events=events)
        step_no += 1
        op, *args = code[q2]
        nq, tested = step(q2, regs, step_no, events)
        if op == "DECJZ":
            r = args[0]
            if not (tested == 0 and r not in written_other):
                return dict(kind="unresolved", events=events)
        elif op == "EQJUMP":
            r, k = args[0], args[1]
            stable = (r not in written_other and r not in decjz_regs) or (
                only_incremented.get(r, False) and r not in decjz_regs and tested > k)
            if not stable:
                return dict(kind="unresolved", events=events)
        q2 = nq
    if q2 != start:
        return dict(kind="unresolved", events=events)
    cycle_ops = [code[i][0] for i in cycle]
    return dict(kind="uncond_cycle", events=events, cycle_ops=cycle_ops)


def safety_truth(run):
    if any(kind == "bad" for _, kind, _ in run["events"]):
        return False
    if run["kind"] == "halted":
        return True
    if run["kind"] == "repeat":
        return True            # no BAD so far and the cycle repeats it forever
    if run["kind"] == "uncond_cycle":
        return "BAD" not in run["cycle_ops"]
    return None


def public_form(run):
    """Return ('finite', seq) | ('periodic', prefix, cycle) | ('open', prefix)."""
    pubs = [(s, v) for s, kind, v in run["events"] if kind == "pub"]
    if run["kind"] == "halted":
        return ("finite", [v for _, v in pubs])
    if run["kind"] == "repeat":
        prefix = [v for s, v in pubs if s <= run["cycle_start"]]
        cycle = [v for s, v in pubs if run["cycle_start"] < s <= run["cycle_end"]]
        return ("finite", prefix) if not cycle else ("periodic", prefix, cycle)
    if run["kind"] == "uncond_cycle" and "PUB" not in run["cycle_ops"]:
        return ("finite", [v for _, v in pubs])
    return ("open", [v for _, v in pubs])


def expand(form, length):
    if form[0] != "periodic":
        return form[1][:length]
    prefix, cycle = form[1], form[2]
    out = list(prefix)
    while len(out) < length:
        out.extend(cycle)
    return out[:length]


def confidentiality_truth(run0, run1):
    a, b = public_form(run0), public_form(run1)
    common = min(len(a[1]), len(b[1]))
    if a[1][:common] != b[1][:common]:
        return False                         # mismatch at a shared position
    for x, y in ((a, b), (b, a)):
        if x[0] == "finite" and len(y[1]) > len(x[1]):
            return False                     # extra publication after completion
    if a[0] == "finite" and b[0] == "finite":
        return a[1] == b[1]
    if {a[0], b[0]} == {"finite", "periodic"}:
        return False                         # finite versus infinite sequence
    if a[0] == "periodic" and b[0] == "periodic":
        horizon = (len(a[1]) + len(b[1]) +
                   2 * math.lcm(len(a[2]), len(b[2])) * max(len(a[2]), len(b[2])))
        return expand(a, horizon) == expand(b, horizon)
    return None


def prefix_by(run, horizon, kind):
    """Values of the given event kind observed by the horizon. The trace of a
    repeating run stops at the first repeated configuration, so its cycle is
    unrolled with the cycle's period to reconstruct the timed observation."""
    events = list(run["events"])
    if run["kind"] == "repeat":
        start, end = run["cycle_start"], run["cycle_end"]
        period = end - start
        cycle = [(s, k, v) for s, k, v in run["events"] if start < s <= end]
        shift = period
        while cycle and end + shift - period < horizon:
            events.extend((s + shift, k, v) for s, k, v in cycle)
            shift += period
    return [v for s, k, v in events if k == kind and s <= horizon]


def first_bad_step(run):
    steps = [s for s, kind, _ in run["events"] if kind == "bad"]
    return steps[0] if steps else None


def small_programs():
    labels = dict(safety=dict(permitted=0, forbidden=0, unresolved=0),
                  confidentiality=dict(permitted=0, forbidden=0, unresolved=0))
    errors = {h: dict(safety_fp=0, conf_fp=0, conf_fn=0,
                      safety_cert=0, conf_cert=0,
                      safety_cert_err=0, conf_cert_err=0) for h in HORIZONS}
    latest = dict(first_bad=0, decisive_publication=0)
    split = dict(with_bad_resolved=0, with_bad_forbidden=0, with_bad_permitted=0,
                 with_bad_certified_forbidden=0, with_bad_certified_permitted=0)
    fp_kinds = {}
    count = 0
    checked_against_base = 0
    for code in all_small_programs():
        count += 1
        runs = [trace(code, n, TRUTH_BUDGET) for n in (0, 1)]
        if count % 997 == 0:               # cross-check semantics with run_vm
            for n, run in zip((0, 1), runs):
                reference = base.run_vm(code, n, TRUTH_BUDGET)
                bad = [s for s, k, _ in run["events"] if k == "bad"]
                pubs = [v for _, k, v in run["events"] if k == "pub"]
                if run["kind"] == "halted":
                    assert reference["halted"] and reference["bad_steps"] == bad
                    assert reference["public"] == pubs
                checked_against_base += 1
        safe = safety_truth(runs[0])
        conf = confidentiality_truth(*runs)
        # Sound syntactic reference rules, used only when the runs settle nothing.
        has_bad_instruction = any(ins[0] == "BAD" for ins in code)
        if safe is None and not has_bad_instruction:
            safe = True
        if conf is None and base.input_independent(code):
            conf = True
        for norm, truth in (("safety", safe), ("confidentiality", conf)):
            key = "unresolved" if truth is None else ("permitted" if truth else "forbidden")
            labels[norm][key] += 1
        fb = first_bad_step(runs[0])
        if safe is False and fb:
            latest["first_bad"] = max(latest["first_bad"], fb)
        independent = base.input_independent(code)
        if safe is not None and has_bad_instruction:
            split["with_bad_resolved"] += 1
            split["with_bad_forbidden"] += safe is False
            split["with_bad_permitted"] += safe is True
        for h in HORIZONS:
            e = errors[h]
            observed_bad = fb is not None and fb <= h
            if safe is not None:
                if safe is False and not observed_bad:
                    e["safety_fp"] += 1
                certified = observed_bad or not has_bad_instruction
                if h == HORIZONS[-1] and has_bad_instruction:
                    split["with_bad_certified_forbidden"] += observed_bad
                    split["with_bad_certified_permitted"] += certified and not observed_bad
                if certified:
                    e["safety_cert"] += 1
                    verdict = not observed_bad
                    e["safety_cert_err"] += verdict != safe
            if conf is not None:
                p0, p1 = (prefix_by(r, h, "pub") for r in runs)
                test_permits = p0 == p1
                e["conf_fp"] += test_permits and not conf
                e["conf_fn"] += (not test_permits) and conf
                if h == HORIZONS[-1] and (not test_permits) and conf:
                    forms = tuple(public_form(r)[0] for r in runs)
                    firsts = []
                    for r in runs:
                        steps = [st for st, kd, _ in r["events"] if kd == "pub"]
                        firsts.append(steps[0] if steps else None)
                    offset = (abs(firsts[0] - firsts[1])
                              if None not in firsts else None)
                    key = f"{forms[0]}/{forms[1]}/first-publication-offset={offset}"
                    fp_kinds[key] = fp_kinds.get(key, 0) + 1
                # Sound fragment of the article: mismatch, extra publication
                # after the other run terminated, two terminated identical
                # sequences, or syntactic input independence.
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
            rows.append(dict(norm=norm, horizon=h, programs=count,
                             permitted=l["permitted"], forbidden=l["forbidden"],
                             unresolved=l["unresolved"],
                             false_permissions=e["safety_fp"] if norm == "safety" else e["conf_fp"],
                             false_prohibitions=0 if norm == "safety" else e["conf_fn"],
                             certified=e["safety_cert"] if norm == "safety" else e["conf_cert"],
                             certificate_errors=e["safety_cert_err"] if norm == "safety" else e["conf_cert_err"]))
    for row in rows:
        assert row["certificate_errors"] == 0
    meta = dict(programs=count, latest_first_bad_step=latest["first_bad"],
                semantic_cross_checks=checked_against_base,
                truth_budget=TRUTH_BUDGET,
                safety_split_programs_with_bad_instruction=split,
                confidentiality_false_prohibitions_at_1024=dict(sorted(fp_kinds.items())))
    return rows, meta


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "data_extensions")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    coverage = separator_coverage()
    write_csv(args.output / "separator_coverage.csv", coverage)
    rows, meta = small_programs()
    write_csv(args.output / "small_programs_summary.csv", rows)
    (args.output / "small_programs_meta.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(coverage=coverage, small_programs=meta), indent=2))


if __name__ == "__main__":
    main()
