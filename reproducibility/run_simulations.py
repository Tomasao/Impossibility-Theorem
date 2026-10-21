#!/usr/bin/env python3
"""Deterministic illustrations for Phase 4. Python >= 3.9, standard library only.

Normative truth is obtained from exact finite-model algorithms or proved
template semantics. A timeout is never used as a normative truth label.
"""
import argparse
import csv
import hashlib
import itertools
import json
import platform
from pathlib import Path

BUDGETS = [2 ** k for k in range(2, 13)]  # 4,...,4096 virtual steps
DELAYS = [2 ** k for k in range(11)]      # 1,...,1024
INPUT_COUNTS = [2 ** k for k in range(12)]  # 1,...,2048
RESPONSE_BUDGET = 64
REGISTER_COUNT = 4


def write_csv(path, rows):
    assert rows
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


# Exact finite-state models. Each state is either a terminal response, or an
# event with one successor. Initial state on input n is n % len(graph).
def fsm_safety(graph):
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


def fsm_response(graph):
    for initial in range(len(graph)):
        q, seen = initial, set()
        while q not in seen:
            seen.add(q)
            event, nxt = graph[q]
            if event.startswith("return"):
                break
            q = nxt
        else:
            return False
    return True


def next_public(graph, initial):
    q, seen = initial, set()
    while q not in seen:
        seen.add(q)
        event, nxt = graph[q]
        if event.startswith("return"):
            return None
        if event.startswith("pub"):
            return (int(event[-1]), nxt)
        q = nxt
    return None  # silent cycle: no more public output


def fsm_confidentiality(graph):
    pair, seen = (0, 1), set()
    while pair not in seen:
        seen.add(pair)
        left, right = (next_public(graph, q) for q in pair)
        if left is None or right is None:
            return left is None and right is None
        if left[0] != right[0]:
            return False
        pair = (left[1], right[1])
    return True


def fsm_independent_checks(graph):
    """Reachability/fixed-point checks, distinct from following a single path."""
    reachable, pending = set(), [0]
    while pending:
        q = pending.pop()
        if q in reachable:
            continue
        reachable.add(q)
        event, nxt = graph[q]
        if not event.startswith("return"):
            pending.append(nxt)
    safe = all(graph[q][0] != "bad" for q in reachable)

    reaches_return = {q for q, (event, _) in enumerate(graph)
                      if event.startswith("return")}
    while True:
        expanded = reaches_return | {
            q for q, (event, nxt) in enumerate(graph)
            if not event.startswith("return") and nxt in reaches_return}
        if expanded == reaches_return:
            break
        reaches_return = expanded
    responsive = len(reaches_return) == len(graph)

    public = [next_public(graph, q) for q in range(len(graph))]
    equal = set(itertools.product(range(len(graph)), repeat=2))
    while True:
        retained = set()
        for a, b in equal:
            left, right = public[a], public[b]
            if left is None and right is None:
                retained.add((a, b))
            elif left is not None and right is not None:
                if left[0] == right[0] and (left[1], right[1]) in equal:
                    retained.add((a, b))
        if retained == equal:
            break
        equal = retained
    return safe, responsive, (0, 1) in equal


def finite_models(data_dir):
    choices = [(event, nxt)
               for event in ("none", "bad", "pub0", "pub1")
               for nxt in range(3)]
    choices.extend([("return0", None), ("return1", None)])
    rows = []
    counts = {norm: {"permitted": 0, "forbidden": 0}
              for norm in ("safety", "confidentiality", "response")}
    for index, graph in enumerate(itertools.product(choices, repeat=3)):
        safe, conf, resp = (fsm_safety(graph), fsm_confidentiality(graph),
                            fsm_response(graph))
        independent = fsm_independent_checks(graph)
        assert (safe, resp, conf) == independent
        labels = dict(safety=safe, confidentiality=conf, response=resp)
        rows.append(dict(model_id=index, graph=json.dumps(graph),
                         **{norm: int(value) for norm, value in labels.items()}))
        for norm, value in labels.items():
            counts[norm]["permitted" if value else "forbidden"] += 1
    assert len(rows) == 14 ** 3 == 2744
    write_csv(data_dir / "finite_models.csv", rows)
    summary = [dict(norm=norm, **labels, total=len(rows))
               for norm, labels in counts.items()]
    write_csv(data_dir / "finite_summary.csv", summary)
    return summary


# A fixed effective register-machine semantics. Natural register values are
# unbounded. Every instruction is one virtual transition, not one physical
# CPU instruction or a claim about bit complexity.
def validate_code(code):
    arities = {"LOAD": 2, "MOV": 2, "INC": 1, "DECJZ": 2,
               "EQJUMP": 3, "JMP": 1, "PUB": 1, "BAD": 0, "RETURN": 1}
    register_positions = {"LOAD": (0,), "MOV": (0, 1), "INC": (0,),
                          "DECJZ": (0,), "EQJUMP": (0,), "JMP": (),
                          "PUB": (0,), "BAD": (), "RETURN": (0,)}
    jump_positions = {"DECJZ": 1, "EQJUMP": 2, "JMP": 0}
    assert code
    for pc, instruction in enumerate(code):
        op, *args = instruction
        assert op in arities and len(args) == arities[op]
        assert all(isinstance(a, int) and a >= 0 for a in args)
        assert all(args[i] < REGISTER_COUNT for i in register_positions[op])
        if op in jump_positions:
            assert args[jump_positions[op]] < len(code)
        if op not in ("JMP", "RETURN"):
            assert pc + 1 < len(code)


def run_vm(code, n, budget):
    validate_code(code)
    assert n >= 0 and budget >= 0
    registers, pc = [n, 0, 0, 0], 0
    seen = {(pc, tuple(registers)): 0}
    public, public_steps, bad_steps = [], [], []
    first_repeat = None
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
            public.append(registers[args[0]])
            public_steps.append(step)
        elif op == "BAD":
            bad_steps.append(step)
        elif op == "RETURN":
            return dict(public=public, public_steps=public_steps,
                        bad_steps=bad_steps, halted=True,
                        response=registers[args[0]], steps=step,
                        first_repeat=first_repeat)
        pc = nxt
        configuration = (pc, tuple(registers))
        if configuration in seen and first_repeat is None:
            first_repeat = dict(previous=seen[configuration], current=step)
        seen.setdefault(configuration, step)
    return dict(public=public, public_steps=public_steps,
                bad_steps=bad_steps, halted=False, response=None,
                steps=budget, first_repeat=first_repeat)


def constant_response(k):
    return [("LOAD", 3, k), ("RETURN", 3)]


def delayed_event(d, event):
    code = [("LOAD", 2, d), ("DECJZ", 2, 3), ("JMP", 1)]
    code.append((event, 0) if event == "PUB" else (event,))
    code.extend([("LOAD", 3, 0), ("RETURN", 3)])
    return code


def delayed_equal(d):
    return [("EQJUMP", 0, 0, 7), ("LOAD", 2, d),
            ("DECJZ", 2, 4), ("JMP", 2), ("LOAD", 3, 0),
            ("PUB", 3), ("RETURN", 3), ("LOAD", 3, 0),
            ("PUB", 3), ("RETURN", 3)]


def trap(m, growing=False):
    tail = [("INC", 2), ("JMP", 3)] if growing else [("JMP", 3)]
    return [("EQJUMP", 0, m, 3), ("LOAD", 3, 0), ("RETURN", 3)] + tail


def delayed_response(d):
    return [("LOAD", 2, d), ("DECJZ", 2, 3), ("JMP", 1),
            ("LOAD", 3, 0), ("RETURN", 3)]


def input_independent(code):
    # A conservative finite syntactic certificate. We deliberately do not
    # infer anything about programs outside this fragment.
    read_positions = {"LOAD": (), "MOV": (1,), "INC": (0,), "DECJZ": (0,),
                      "EQJUMP": (0,), "JMP": (), "PUB": (0,), "BAD": (),
                      "RETURN": (0,)}
    return all(instruction[i + 1] != 0
               for instruction in code for i in read_positions[instruction[0]])


def acyclic_return_certificate(code):
    # Overapproximate both outcomes of every conditional jump. If this whole
    # reachable graph is acyclic and all sinks are RETURN, all inputs return.
    def successors(pc):
        op, *args = code[pc]
        if op == "RETURN":
            return []
        if op == "JMP":
            return [args[0]]
        if op in ("DECJZ", "EQJUMP"):
            return [pc + 1, args[-1]]
        return [pc + 1]

    visiting, done = set(), set()
    def visit(pc):
        if pc in visiting:
            return False
        if pc in done:
            return True
        visiting.add(pc)
        result = all(visit(q) for q in successors(pc))
        visiting.remove(pc)
        done.add(pc)
        return result
    return visit(0)


def candidate(name, code, permitted, reason, parameter=None):
    validate_code(code)
    return dict(name=name, code=code, permitted=permitted,
                analytic_justification=reason, parameter=parameter)


def safety_experiment(data_dir, all_candidates):
    programs = [
        candidate("constant_return", constant_response(0), True, "No BAD."),
        candidate("silent_loop", [("JMP", 0)], True, "No BAD."),
        candidate("unreachable_bad",
                  [("LOAD", 3, 0), ("RETURN", 3), ("BAD",), ("JMP", 2)],
                  True, "RETURN at step 2; BAD is unreachable.")]
    programs += [candidate("bad_delay_%d" % d, delayed_event(d, "BAD"), False,
                           "BAD at exactly 2*d+3 transitions on input 0.", d)
                 for d in DELAYS]
    for p in programs[3:]:
        observed = run_vm(p["code"], 0, 2*p["parameter"] + 5)
        assert observed["bad_steps"] == [2*p["parameter"] + 3]
        assert observed["halted"]
    rows, summary = [], []
    for horizon in BUDGETS:
        false_allow = false_deny = unknown = 0
        for p in programs:
            observed = run_vm(p["code"], 0, horizon)
            naive_allow = not observed["bad_steps"]
            status = ("forbidden" if observed["bad_steps"] else
                      "permitted" if not any(i[0] == "BAD" for i in p["code"])
                      else "unknown")
            assert status == "unknown" or (status == "permitted") == p["permitted"]
            false_allow += int(naive_allow and not p["permitted"])
            false_deny += int(not naive_allow and p["permitted"])
            unknown += int(status == "unknown")
            rows.append(dict(horizon=horizon, candidate=p["name"],
                             truth_permitted=int(p["permitted"]),
                             naive_permitted=int(naive_allow),
                             certificate_status=status,
                             bad_steps=json.dumps(observed["bad_steps"]),
                             halted=int(observed["halted"])))
        summary.append(dict(horizon=horizon, total=len(programs),
                            true_permitted=3, true_forbidden=len(DELAYS),
                            false_permissions=false_allow,
                            false_prohibitions=false_deny,
                            certificate_unknown=unknown,
                            certificate_errors=0))
    write_csv(data_dir / "safety_observations.csv", rows)
    write_csv(data_dir / "safety_summary.csv", summary)
    all_candidates["safety"] = programs
    return summary


def confidentiality_experiment(data_dir, all_candidates):
    programs = [
        candidate("constant_public",
                  [("LOAD", 3, 7), ("PUB", 3), ("RETURN", 3)], True,
                  "Both complete public sequences are [7]."),
        candidate("silent_loop", [("JMP", 0)], True,
                  "Both complete public sequences are empty."),
        candidate("missing_output",
                  [("EQJUMP", 0, 0, 4), ("INC", 2), ("JMP", 1),
                   ("RETURN", 3), ("LOAD", 3, 0), ("PUB", 3), ("RETURN", 3)],
                  False,
                  "Secret 0 emits [0]; secret 1 increments silently forever.")]
    programs += [candidate("leak_delay_%d" % d, delayed_event(d, "PUB"), False,
                           "The complete public sequences are [0] and [1].", d)
                 for d in DELAYS]
    programs += [candidate("equal_delay_%d" % d, delayed_equal(d), True,
                           "Both complete public sequences are [0]; "
                           "publication times are 3 and 2*d+5.", d)
                 for d in DELAYS]
    for p in programs:
        if p["name"].startswith("leak_delay"):
            d = p["parameter"]
            runs = [run_vm(p["code"], h, 2*d+5) for h in (0, 1)]
            assert [r["public"] for r in runs] == [[0], [1]]
            assert all(r["public_steps"] == [2*d+3] for r in runs)
        elif p["name"].startswith("equal_delay"):
            d = p["parameter"]
            runs = [run_vm(p["code"], h, 2*d+6) for h in (0, 1)]
            assert [r["public"] for r in runs] == [[0], [0]]
            assert [r["public_steps"] for r in runs] == [[3], [2*d+5]]
            assert all(r["halted"] for r in runs)
    rows, summary = [], []
    for horizon in BUDGETS:
        false_allow = false_deny = unknown = 0
        for p in programs:
            left, right = [run_vm(p["code"], h, horizon) for h in (0, 1)]
            lpub, rpub = left["public"], right["public"]
            naive_allow = lpub == rpub
            mismatch = any(a != b for a, b in zip(lpub, rpub))
            completed_shorter = ((left["halted"] and len(lpub) < len(rpub)) or
                                 (right["halted"] and len(rpub) < len(lpub)))
            if mismatch or completed_shorter:
                status = "forbidden"
            elif input_independent(p["code"]) or (
                    left["halted"] and right["halted"] and lpub == rpub):
                status = "permitted"
            else:
                status = "unknown"
            assert status == "unknown" or (status == "permitted") == p["permitted"]
            false_allow += int(naive_allow and not p["permitted"])
            false_deny += int(not naive_allow and p["permitted"])
            unknown += int(status == "unknown")
            rows.append(dict(horizon=horizon, candidate=p["name"],
                             truth_permitted=int(p["permitted"]),
                             naive_permitted=int(naive_allow),
                             certificate_status=status,
                             public_0=json.dumps(lpub), public_1=json.dumps(rpub),
                             halted_0=int(left["halted"]),
                             halted_1=int(right["halted"])))
        summary.append(dict(horizon=horizon, total=len(programs),
                            true_permitted=len(DELAYS)+2,
                            true_forbidden=len(DELAYS)+1,
                            false_permissions=false_allow,
                            false_prohibitions=false_deny,
                            certificate_unknown=unknown,
                            certificate_errors=0))
    write_csv(data_dir / "confidentiality_observations.csv", rows)
    write_csv(data_dir / "confidentiality_summary.csv", summary)
    all_candidates["confidentiality"] = programs
    return summary


def response_experiment(data_dir, all_candidates):
    programs = [
        candidate("constant_return_0", constant_response(0), True,
                  "Returns 0 on every natural input."),
        candidate("constant_return_1", constant_response(1), True,
                  "Returns 1 on every natural input."),
        candidate("delayed_total_return", delayed_response(1024), True,
                  "Returns on every input at exactly 2052 transitions.", 1024)]
    for m in DELAYS:
        programs.extend([
            candidate("trap_%d" % m, trap(m), False,
                      "Returns except at input m, where it loops.", m),
            candidate("growing_trap_%d" % m, trap(m, True), False,
                      "Returns except at input m, where a silent counter "
                      "grows without bound.", m)])
    delayed = run_vm(programs[2]["code"], 0, 2052)
    assert delayed["halted"] and delayed["steps"] == 2052
    for p in programs[3:]:
        trapped = run_vm(p["code"], p["parameter"], RESPONSE_BUDGET)
        normal = run_vm(p["code"], 0, RESPONSE_BUDGET)  # every m >= 1
        assert not trapped["halted"] and normal["halted"]
        assert bool(trapped["first_repeat"]) == p["name"].startswith("trap_")
    rows, summary = [], []
    structural = {p["name"]: acyclic_return_certificate(p["code"])
                  for p in programs}
    for count in INPUT_COUNTS:
        false_allow = false_deny = unknown = 0
        for p in programs:
            failures, cycle_inputs = [], []
            for n in range(count):
                observed = run_vm(p["code"], n, RESPONSE_BUDGET)
                if not observed["halted"]:
                    failures.append(n)
                if observed["first_repeat"] is not None:
                    cycle_inputs.append(n)
            naive_allow = not failures
            status = ("forbidden" if cycle_inputs else
                      "permitted" if structural[p["name"]] else "unknown")
            assert status == "unknown" or (status == "permitted") == p["permitted"]
            false_allow += int(naive_allow and not p["permitted"])
            false_deny += int(not naive_allow and p["permitted"])
            unknown += int(status == "unknown")
            rows.append(dict(input_count=count, horizon=RESPONSE_BUDGET,
                             candidate=p["name"],
                             truth_permitted=int(p["permitted"]),
                             naive_permitted=int(naive_allow),
                             certificate_status=status,
                             timed_out_inputs=json.dumps(failures),
                             proved_cycle_inputs=json.dumps(cycle_inputs)))
        summary.append(dict(input_count=count, horizon=RESPONSE_BUDGET,
                            total=len(programs), true_permitted=3,
                            true_forbidden=2*len(DELAYS),
                            false_permissions=false_allow,
                            false_prohibitions=false_deny,
                            certificate_unknown=unknown,
                            certificate_errors=0))
    write_csv(data_dir / "response_observations.csv", rows)
    write_csv(data_dir / "response_summary.csv", summary)
    all_candidates["response"] = programs
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parent / "data")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    candidates = {}
    summary = dict(
        finite=finite_models(args.output),
        safety=safety_experiment(args.output, candidates),
        confidentiality=confidentiality_experiment(args.output, candidates),
        response=response_experiment(args.output, candidates))
    write_json(args.output / "candidates.json", candidates)
    write_json(args.output / "summary.json", summary)
    write_json(args.output / "protocol.json", dict(
        deterministic=True, random_seed=None, finite_state_count=3,
        finite_model_count=2744, virtual_step_budgets=BUDGETS,
        delay_parameters=DELAYS, input_counts=INPUT_COUNTS,
        response_budget=RESPONSE_BUDGET,
        runtime_note="Register values are arbitrary-precision naturals. One "
        "instruction is one virtual transition; physical bit costs are not "
        "measured.",
        truth_note="Normative labels come from exact finite algorithms and "
        "analytic template semantics, never from timeouts.",
        scope_note="The finite benchmark is an illustration, not a proof of "
        "undecidability or an empirical estimate of real-world risk."))
    runtime = dict(python_version=platform.python_version(),
                   implementation=platform.python_implementation())
    write_json(args.output / "runtime.json", runtime)
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(args.output.iterdir())
              if p.is_file() and p.name != "sha256_manifest.json"}
    write_json(args.output / "sha256_manifest.json", hashes)
    print(json.dumps(dict(
        finite=summary["finite"],
        safety_first=summary["safety"][0], safety_last=summary["safety"][-1],
        conf_first=summary["confidentiality"][0],
        conf_last=summary["confidentiality"][-1],
        response_first=summary["response"][0],
        response_last=summary["response"][-1],
        checks="All analytic-time, soundness and independent finite-model "
        "checks passed."), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

