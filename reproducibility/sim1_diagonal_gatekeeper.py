#!/usr/bin/env python3
"""Simulation 1: the diagonal argument of Theorem 'budget' made executable.

Model.  A *program* is Python source defining a generator `run(h, env)`.
Each `yield` is one step.  env.bad() performs the forbidden operation,
env.pub(v) publishes v, and `yield from env.sim(src, h, T)` runs another
program internally for at most T steps (every inner step costs one outer
step: linear simulation overhead).  The environment never lets internal
simulations reach the external channels (assumption A2/A3).

A *gatekeeper* (checker) is Python source defining a generator
`check(src, T, env)` that must return True ("permitted: no BAD within the
budget T") or False.  Its cost is the number of steps it yields.

The *adversary generator* turns any checker into the program d_T that
(1) reconstructs its own source (a quine), (2) runs the checker on itself
with budget T, and (3) does the opposite of the verdict.  Ground truth is
"does d_T perform BAD within T steps on input 0?", obtained by running d_T
for T steps.
"""
import csv, json, math, random, sys, time
from pathlib import Path

sys.setrecursionlimit(200000)
OUT = Path(__file__).resolve().parent / "sim1_out"
OUT.mkdir(exist_ok=True)

# ------------------------------------------------------------ environment
class Env:
    def __init__(self):
        self.events = []          # ("bad",) or ("pub", v)
    def bad(self):
        self.events.append(("bad",))
    def pub(self, v):
        self.events.append(("pub", v))
    def sim(self, src, h, T):
        """Generator: run src internally for <= T steps; each inner step
        yields once outward. Returns a record."""
        rec = yield from _run(src, h, T)
        return rec
    def check(self, checker_src, prog_src, T):
        """Generator: run a checker on prog_src with budget T."""
        ns = {}
        exec(checker_src, ns)
        verdict = yield from ns["check"](prog_src, T, Env())
        return verdict

def _run(src, h, T):
    """Run program src on input h for at most T steps.
    Returns dict(steps, bad_step, returned, events)."""
    ns = {}
    exec(src, ns)
    env = Env()
    gen = ns["run"](h, env)
    steps, bad_step, returned = 0, None, False
    try:
        while steps < T:
            next(gen)
            steps += 1
            yield
            if bad_step is None and any(e[0] == "bad" for e in env.events):
                bad_step = steps
    except StopIteration:
        returned = True
    if bad_step is None and any(e[0] == "bad" for e in env.events):
        bad_step = steps
    return dict(steps=steps, bad_step=bad_step, returned=returned,
                events=list(env.events))

def run_top(src, h, T):
    """Run at top level, counting steps."""
    g = _run(src, h, T)
    cost = 0
    try:
        while True:
            next(g); cost += 1
    except StopIteration as stop:
        rec = stop.value
    rec["cost"] = cost
    return rec

def run_checker(checker_src, prog_src, T):
    ns = {}
    exec(checker_src, ns)
    g = ns["check"](prog_src, T, Env())
    cost = 0
    try:
        while True:
            next(g); cost += 1
    except StopIteration as stop:
        verdict = stop.value
    return verdict, cost

# ------------------------------------------------------------- gatekeepers
CHECKERS = {
 "always_permit": '''
def check(src, T, env):
    yield
    return True
''',
 "always_forbid": '''
def check(src, T, env):
    yield
    return False
''',
 "static_no_bad_call": '''
def check(src, T, env):
    # permitted iff the text 'bad(' never appears in the source
    yield
    return "bad(" not in src
''',
 "simulate_sqrt_T": '''
def check(src, T, env):
    import math
    yield
    rec = yield from env.sim(src, 0, max(1, math.isqrt(T)))
    return rec["bad_step"] is None
''',
 "simulate_half_T": '''
def check(src, T, env):
    yield
    rec = yield from env.sim(src, 0, T // 2)
    return rec["bad_step"] is None
''',
 "simulate_full_T": '''
def check(src, T, env):
    yield
    rec = yield from env.sim(src, 0, T)
    return rec["bad_step"] is None
''',
 "coin_flip": '''
def check(src, T, env):
    import random
    yield
    return random.Random(hash(src) & 0xffff).random() < 0.5
''',
 "length_heuristic": '''
def check(src, T, env):
    # 'short programs are harmless'
    yield
    return len(src) < 400
''',
}

# ---------------------------------------------------------------- adversary
TEMPLATE = '''
CHECKER_SRC = @CHECKER@
T = @T@
TEMPLATE = @TEMPLATE@
def run(h, env):
    yield                                   # step 1: prepare my own code
    me = (TEMPLATE.replace("@" + "CHECKER@", repr(CHECKER_SRC))
                  .replace("@" + "T@", str(T))
                  .replace("@" + "TEMPLATE@", repr(TEMPLATE)))
    verdict = yield from env.check(CHECKER_SRC, me, T)   # ask the gatekeeper about me
    if verdict:                             # 'permitted' -> do the forbidden thing
        env.bad()
    yield                                   # step: act (or stay silent)
    return
'''

def make_adversary(checker_src, T):
    return (TEMPLATE.replace("@" + "CHECKER@", repr(checker_src))
                    .replace("@" + "T@", str(T))
                    .replace("@" + "TEMPLATE@", repr(TEMPLATE)))

# ------------------------------------------------- benign benchmark programs
def benign_bank(T):
    """Ordinary programs with known truth for budget T."""
    bank = []
    bank.append(("silent_loop", '''
def run(h, env):
    while True:
        yield
''', True))
    bank.append(("returns_quickly", '''
def run(h, env):
    yield; yield
    env.pub(7)
    return
''', True))
    bank.append(("bad_at_step_3", '''
def run(h, env):
    yield; yield
    env.bad()
    yield
''', False))
    bank.append(("bad_at_step_T_minus_1", f'''
def run(h, env):
    for _ in range({T} - 2):
        yield
    env.bad()
    yield
''', False))
    bank.append(("bad_after_budget", f'''
def run(h, env):
    for _ in range({T} + 5):
        yield
    env.bad()
    yield
''', True))   # permitted for the bounded norm: BAD occurs after T
    return bank

# -------------------------------------------------------------------- main
def main():
    budgets = [2 ** k for k in range(3, 11)]   # 8 .. 1024
    rows, bench = [], []
    for name, csrc in CHECKERS.items():
        for T in budgets:
            # benign benchmark
            for bname, bsrc, truth in benign_bank(T):
                v, c = run_checker(csrc, bsrc, T)
                bench.append(dict(checker=name, T=T, program=bname,
                                  truth_permitted=truth, verdict_permitted=v,
                                  correct=(v == truth), cost=c))
            # adversary
            adv = make_adversary(csrc, T)
            # self-check of the quine: the program must rebuild exactly itself
            ns = {}; exec(adv, ns)
            rebuilt = (ns["TEMPLATE"].replace("@" + "CHECKER@", repr(ns["CHECKER_SRC"]))
                       .replace("@" + "T@", str(ns["T"]))
                       .replace("@" + "TEMPLATE@", repr(ns["TEMPLATE"])))
            assert rebuilt == adv, "quine failed"
            t0 = time.perf_counter()
            truth_rec = run_top(adv, 0, T)
            truth = truth_rec["bad_step"] is None
            t1 = time.perf_counter()
            verdict, cost = run_checker(csrc, adv, T)
            t2 = time.perf_counter()
            rows.append(dict(checker=name, T=T, adversary_chars=len(adv),
                             truth_permitted=truth, verdict_permitted=verdict,
                             correct=(verdict == truth), checker_cost_steps=cost,
                             cost_over_T=round(cost / T, 3),
                             bad_step=truth_rec["bad_step"],
                             wall_truth_s=round(t1 - t0, 4),
                             wall_checker_s=round(t2 - t1, 4)))
    with (OUT / "adversary_results.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    with (OUT / "benign_benchmark.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(bench[0])); w.writeheader(); w.writerows(bench)
    # summary
    summary = {}
    for name in CHECKERS:
        r = [x for x in rows if x["checker"] == name]
        b = [x for x in bench if x["checker"] == name]
        summary[name] = dict(
            adversary_correct=sum(x["correct"] for x in r), adversary_total=len(r),
            benign_correct=sum(x["correct"] for x in b), benign_total=len(b),
            min_cost_over_T=min(x["cost_over_T"] for x in r),
            max_cost_over_T=max(x["cost_over_T"] for x in r))
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    (OUT / "example_adversary_T16.py").write_text(make_adversary(CHECKERS["simulate_half_T"], 16))
    for k, v in summary.items():
        print(f"{k:22s} adversary {v['adversary_correct']}/{v['adversary_total']}  "
              f"benign {v['benign_correct']}/{v['benign_total']}  cost/T in "
              f"[{v['min_cost_over_T']}, {v['max_cost_over_T']}]")

if __name__ == "__main__":
    main()
