#!/usr/bin/env python3
"""Simulation 3: programs whose safety equals an open mathematical problem.
Same step-counted environment as sim1.  Each program searches for a
counterexample to a conjecture and performs BAD only if it finds one.
Bounded tests at horizons 10^k must permit it; no certificate of safety exists
unless the conjecture is proved."""
import csv, json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sim1_diagonal_gatekeeper import run_top  # reuse the step-counted environment

GOLDBACH = '''
def run(h, env):
    def is_prime(k):
        if k < 2: return False
        i = 2
        while i * i <= k:
            if k % i == 0: return False
            i += 1
        return True
    n = 4
    while True:
        yield                       # one step per even number examined
        found = False
        a = 2
        while a <= n // 2:
            if is_prime(a) and is_prime(n - a):
                found = True; break
            a += 1
        if not found:
            env.bad()               # counterexample to Goldbach: open the safe
            return
        n += 2
'''
COLLATZ = '''
def run(h, env):
    n = 1
    while True:
        yield                       # one step per starting value examined
        x, seen = n, 0
        while x != 1:
            x = x // 2 if x % 2 == 0 else 3 * x + 1
            seen += 1
            if seen > 10**7:        # a cycle or divergence would be a counterexample
                env.bad(); return
        n += 1
'''
# control: a program whose counterexample search provably terminates
CONTROL = '''
def run(h, env):
    n = 1
    while True:
        yield
        if n * n > 10**6:           # 'is every square below one million?' - false at n = 1001
            env.bad(); return
        n += 1
'''
rows = []
for name, src in (("goldbach_search", GOLDBACH), ("collatz_search", COLLATZ), ("control_false_conjecture", CONTROL)):
    for H in (10, 100, 1000, 10000, 100000, 1000000):
        if name != "control_false_conjecture" and H > 100000: pass
        t0 = time.perf_counter()
        rec = run_top(src, 0, H)
        rows.append(dict(program=name, horizon=H, bad_observed=rec["bad_step"] is not None,
                         bad_step=rec["bad_step"], bounded_test_verdict="permitted" if rec["bad_step"] is None else "forbidden",
                         wall_s=round(time.perf_counter() - t0, 2)))
        print(rows[-1])
out = Path(__file__).resolve().parent / "sim3_open_problem_results.csv"
with out.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
