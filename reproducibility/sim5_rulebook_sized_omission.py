#!/usr/bin/env python3
"""Simulation 5: for every SOUND safety certifier (a procedure that may
certify 'safe' and is never wrong), build a program of about the certifier's
own size that is safe but never certified.  Construction (recursion theorem):
q = 'if the certifier certifies me, perform BAD; otherwise idle forever'.
Soundness forbids certifying q (q would then be unsafe), so q is never
certified and therefore never acts: safe and omitted."""
import csv, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sim1_diagonal_gatekeeper import run_top, run_checker

CERTIFIERS = {
 "syntactic_no_bad": '''
def check(src, T, env):
    yield
    return "bad(" not in src
''',
 "no_loops_no_bad": '''
def check(src, T, env):
    yield
    return ("while" not in src) and ("for " not in src) and ("bad(" not in src)
''',
 "halts_in_1000_steps_without_bad": '''
def check(src, T, env):
    yield
    rec = yield from env.sim(src, 0, 1000)
    return rec["returned"] and rec["bad_step"] is None   # halted within 1000 steps, never BAD; else abstain
''',
 "bad_only_in_dead_code_after_return": '''
def check(src, T, env):
    yield
    # certify if every 'bad(' occurs after an unconditional 'return' at the same indent
    lines = src.splitlines()
    for i, l in enumerate(lines):
        if "bad(" in l:
            ind = len(l) - len(l.lstrip())
            if not any(x.strip().startswith("return") and len(x) - len(x.lstrip()) == ind for x in lines[:i]):
                return False
    return True
''',
}

TEMPLATE = '''
CERT_SRC = @CERT@
TEMPLATE = @TEMPLATE@
def run(h, env):
    yield
    me = TEMPLATE.replace("@" + "CERT@", repr(CERT_SRC)).replace("@" + "TEMPLATE@", repr(TEMPLATE))
    verdict = yield from env.check(CERT_SRC, me, 0)
    if verdict:                 # the rulebook certifies me as safe ...
        env.bad()               # ... so I do the forbidden thing
        return
    while True:                 # otherwise idle forever, visibly doing nothing
        yield
'''
def build(cert_src):
    return TEMPLATE.replace("@" + "CERT@", repr(cert_src)).replace("@" + "TEMPLATE@", repr(TEMPLATE))

rows = []
for name, c in CERTIFIERS.items():
    certify = lambda src: run_checker(c, src, 0)[0]
    # sanity: the certifier is sound on a small bank and does certify something
    bank = {"returns": "def run(h, env):\n    yield\n    return\n",
            "bad_now": "def run(h, env):\n    yield\n    env.bad()\n    return\n",
            "loop": "def run(h, env):\n    while True:\n        yield\n"}
    verdicts = {k: bool(certify(v)) for k, v in bank.items()}
    q = build(c)
    certified_q = bool(certify(q))
    rec = run_top(q, 0, 100000)
    rows.append(dict(certifier=name, certifier_chars=len(c), omitted_program_chars=len(q),
                     overhead_chars=len(q) - len(c), certifies_q=certified_q,
                     q_bad_within_1e5=rec["bad_step"] is not None, q_returned=rec["returned"],
                     bank_verdicts=str(verdicts)))
    print(rows[-1])
with (Path(__file__).resolve().parent / "sim5_rulebook_sized_omission.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
