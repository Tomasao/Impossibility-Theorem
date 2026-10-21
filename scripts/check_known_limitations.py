#!/usr/bin/env python3
"""Reproduce counterexamples to three archived Simulation 5 certifiers."""
import ast
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ast.parse((ROOT/'reproducibility/sim5_rulebook_sized_omission.py').read_text())
    certifiers = next(ast.literal_eval(n.value) for n in source.body
                     if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CERTIFIERS' for t in n.targets))
    alias = 'def run(h, env):\n    yield\n    getattr(env, "bad")()\n    yield\n'
    unrelated_return = 'def helper():\n    return\ndef run(h, env):\n    yield\n    env.bad()\n    yield\n'
    cases = [('syntactic_no_bad',alias),('no_loops_no_bad',alias),
             ('bad_only_in_dead_code_after_return',unrelated_return)]
    results=[]
    with tempfile.TemporaryDirectory(prefix='v14-limitations-') as tmp:
        path=Path(tmp)/'sim1_diagonal_gatekeeper.py'
        shutil.copyfile(ROOT/'reproducibility'/path.name,path)
        spec=importlib.util.spec_from_file_location('v14_env',path)
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        for name,program in cases:
            certified,_=module.run_checker(certifiers[name],program,0)
            bad=module.run_top(program,0,10)['bad_step']
            if not certified or bad is None:
                raise SystemExit('Counterexample no longer reproduced: '+name)
            results.append(dict(certifier=name,certifies_unsafe_program=certified,bad_step=bad,
                                counterexample_source=program))
    print(json.dumps(dict(status='known_counterexamples_reproduced',results=results),indent=2))


if __name__=='__main__': main()
