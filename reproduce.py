#!/usr/bin/env python3
"""Reproduce v14 results in build/ while preserving every archived input."""
import argparse
import csv
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from derive_horizons import write as write_horizons
from export_tables import export as export_tables


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_integrity():
    manifest = json.loads((ROOT / 'MANIFEST_SHA256.json').read_text())
    bad = [name for name, expected in manifest['files'].items()
           if not (ROOT / name).is_file() or digest(ROOT / name) != expected]
    if bad:
        raise RuntimeError('Archive integrity mismatch: ' + ', '.join(bad))
    return len(manifest['files'])


def compare(expected, actual):
    if expected.suffix == '.csv':
        with expected.open(newline='') as h: a = list(csv.DictReader(h))
        with actual.open(newline='') as h: b = list(csv.DictReader(h))
        if len(a) != len(b):
            return dict(status='mismatch', reason='row count')
        fields = set(a[0]) if a else set()
        if b and fields != set(b[0]):
            return dict(status='mismatch', reason='columns')
        timings = {'wall_s', 'wall_truth_s', 'wall_checker_s'}
        differences, coin_differences = 0, 0
        for ar, br in zip(a, b):
            changed = {k for k in fields - timings if ar[k] != br[k]}
            allowed = ({'truth_permitted','verdict_permitted','bad_step'}
                       if expected.name == 'sim1_adversary_results.csv' else
                       {'verdict_permitted','correct'}
                       if expected.name == 'sim1_benign_benchmark.csv' else set())
            if changed and ar.get('checker') == br.get('checker') == 'coin_flip' and changed <= allowed:
                coin_differences += 1
            elif changed:
                differences += 1
        identical = expected.read_bytes() == actual.read_bytes()
        if not (fields & timings) and not coin_differences and not identical:
            return dict(status='mismatch', reason='byte comparison', differing_rows=differences)
        return dict(status='mismatch' if differences else 'documented_difference' if coin_differences else 'matched',
                    differing_rows=differences, hash_sensitive_coin_rows=coin_differences,
                    timing_columns_excluded=sorted(fields & timings),
                    byte_identical=identical)
    return dict(status='matched' if expected.read_bytes() == actual.read_bytes() else 'mismatch')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', choices=('archive','core','full'), default='archive',
                        help='archive: regenerate derived outputs; core: also rerun core; full: rerun every experiment')
    parser.add_argument('--plots', action='store_true', help='Regenerate Figure 4 using installed plotting dependencies')
    parser.add_argument('--tex', action='store_true', help='Compile six TeX figure sources, numerical tables and S1')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/reproduction')
    args = parser.parse_args()
    target = args.output.resolve()
    if target == ROOT or ROOT in target.parents and target.relative_to(ROOT).parts[0] != 'build':
        parser.error('An output inside the repository must be under build/.')
    if target in ROOT.parents:
        parser.error('Output cannot be an ancestor of the repository.')
    count = verify_integrity()
    target.mkdir(parents=True, exist_ok=True)
    logdir = target / 'logs'; logdir.mkdir(exist_ok=True)
    stage = target / 'workspace'
    for name in ('reproducibility','figures','supplementary'):
        shutil.copytree(ROOT / name, stage / name, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__','sim1_out','sim2_out'))
    env = dict(os.environ, PYTHONHASHSEED='0', PYTHONUNBUFFERED='1', MPLCONFIGDIR=str(target / 'matplotlib-cache'))
    records, comparisons = [], []
    def run(name, command, cwd=None):
        print('Running ' + name, flush=True)
        start = time.monotonic()
        with (logdir / (name + '.log')).open('w', encoding='utf-8') as log:
            result = subprocess.run(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
        records.append(dict(task=name, returncode=result.returncode, elapsed_seconds=round(time.monotonic()-start,3)))
        if result.returncode:
            raise RuntimeError(name + ' failed; see ' + str(logdir / (name + '.log')))
    def check(relative):
        result = compare(ROOT/'reproducibility'/relative, stage/'reproducibility'/relative)
        result['file'] = relative
        comparisons.append(result)
    repro = stage/'reproducibility'
    status = 'running'
    failure = None
    try:
        if args.suite in ('core','full'):
            run('base', [sys.executable, str(repro/'run_simulations.py')])
            for f in sorted((ROOT/'reproducibility/data').iterdir()):
                if f.suffix in ('.csv','.json') and f.name not in ('runtime.json','sha256_manifest.json'):
                    check('data/'+f.name)
        if args.suite == 'full':
            for label, script, directory in [('extensions','run_extensions.py','data_extensions'),
                                             ('sampled','run_sampled.py','data_sampled')]:
                run(label,[sys.executable,str(repro/script)])
                for f in sorted((ROOT/'reproducibility'/directory).iterdir()):
                    if f.is_file(): check(directory+'/'+f.name)
            run('sim1',[sys.executable,str(repro/'sim1_diagonal_gatekeeper.py')])
            for name in ('adversary_results.csv','benign_benchmark.csv'):
                shutil.copyfile(repro/'sim1_out'/name, repro/('sim1_'+name)); check('sim1_'+name)
            run('sim2',[sys.executable,str(repro/'sim2_horizon_landscape.py')])
            for source,dest in [('landscape.csv','sim2_landscape.csv'),('first_bad_meta.json','sim2_first_bad_meta.json')]:
                shutil.copyfile(repro/'sim2_out'/source,repro/dest); check(dest)
            for label,script,filename in [('sim3','sim3_open_problem_programs.py','sim3_open_problem_results.csv'),
                                           ('sim4','sim4_plateau_breakdown.py','sim4_plateau_breakdown.csv'),
                                           ('sim5','sim5_rulebook_sized_omission.py','sim5_rulebook_sized_omission.csv')]:
                run(label,[sys.executable,str(repro/script)]); check(filename)
        write_horizons(repro, repro/'sim2_required_horizon.csv')
        check('sim2_required_horizon.csv')
        export_tables(repro, target/'tables')
        run('figure1_data',[sys.executable,str(stage/'figures/build_fig1_data.py')])
        run('figure3_data',[sys.executable,str(stage/'figures/build_fig3_data.py')])
        run('supplementary_figure_sources',[sys.executable,str(repro/'build_figures.py')])
        run('experiments_figure_source',[sys.executable,str(repro/'build_figure_experiments.py')])
        if args.plots:
            run('figure4',[sys.executable,str(stage/'figures/build_fig4.py')])
            result=compare(ROOT/'figures/fig4_numbers.json',stage/'figures/fig4_numbers.json')
            result['file']='figures/fig4_numbers.json'; comparisons.append(result)
        if args.tex:
            engine = shutil.which('pdflatex')
            if not engine:
                raise RuntimeError('pdflatex is required for --tex')
            targets = [(stage/'figures',n) for n in ('fig1_concept','fig2_evidence','fig3_selfreference')]
            targets += [(repro/'figures',n) for n in ('finite_models','bounded_observation','experiments')]
            targets += [(target/'tables','numerical_tables')]
            for folder,name in targets:
                run(name,[engine,'-interaction=nonstopmode','-halt-on-error',name+'.tex'],folder)
                if name == 'numerical_tables':
                    run(name+'_second_pass',[engine,'-interaction=nonstopmode','-halt-on-error',name+'.tex'],folder)
            shutil.copyfile(repro/'figures/bounded_observation.pdf',stage/'supplementary/bounded_observation.pdf')
            for i in (1,2):
                run('supplement_'+str(i),[engine,'-interaction=nonstopmode','-halt-on-error','S1_protocol.tex'],stage/'supplementary')
            shutil.copyfile(stage/'supplementary/S1_protocol.pdf',stage/'supplementary/Supplementary_Document_S1.pdf')
        if any(r['status']=='mismatch' for r in comparisons):
            status='failed_comparison'
        elif any(r['status']=='documented_difference' for r in comparisons):
            status='completed_with_documented_differences'
        else:
            status='completed'
    except (RuntimeError, OSError, ValueError) as error:
        status='failed'; failure=str(error)
    report = dict(status=status, suite=args.suite, python=platform.python_version(),
                  platform=platform.system()+' '+platform.machine(), archive_files_checked=count,
                  pythonhashseed='0', tasks=records, comparisons=comparisons,
                  scientific_validation='Not established by numerical reproduction; see docs/KNOWN_LIMITATIONS.md',
                  failure=failure)
    (target/'reproduction_report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(status + ': ' + str(target/'reproduction_report.json'),flush=True)
    if failure: print(failure,file=sys.stderr)
    return 1 if status.startswith('failed') else 0


if __name__ == '__main__':
    raise SystemExit(main())
