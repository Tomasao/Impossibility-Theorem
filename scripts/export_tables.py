#!/usr/bin/env python3
"""Export all numerical manuscript/supplement tables from the archived CSVs."""
import argparse
import csv
from pathlib import Path


def read(path):
    with path.open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def escape(value):
    text = str(value)
    for old, new in [ ('\\', r'\textbackslash{}'), ('_', r'\_'), ('%', r'\%'),
                      ('&', r'\&'), ('#', r'\#') ]:
        text = text.replace(old, new)
    return text


def export(data, output):
    output.mkdir(parents=True, exist_ok=True)
    coverage = read(data / 'data_extensions/separator_coverage.csv')
    small = read(data / 'data_extensions/small_programs_summary.csv')
    sampled = read(data / 'data_sampled/sampled_programs_summary.csv')
    horizons = {int(r['length']): r for r in read(data / 'sim2_required_horizon.csv')}
    landscape = read(data / 'sim2_landscape.csv')
    main = []
    for length, h in sorted(horizons.items()):
        by_h = {int(r['horizon']): r for r in landscape if int(r['length']) == length}
        last = by_h[max(by_h)]
        row = dict(length=length, unsafe=last['safety_forbidden'],
                   safety_unresolved=last['safety_unresolved'], conf_unresolved=last['conf_unresolved'])
        for horizon in (8, 16, 32, 64):
            row['safety_false_permission_percent_H' + str(horizon)] = format(
                100 * int(by_h[horizon]['safety_false_permissions']) / int(last['safety_forbidden']), '.2f')
        row['conf_false_prohibition_percent_H4096'] = format(
            100 * int(last['conf_false_prohibitions']) / int(last['conf_permitted']), '.3f')
        row.update({key: h[key] for key in ('median_first_bad', 'p99', 'p999', 'max_first_bad')})
        main.append(row)
    specifications = [
        ('table_G1_A', 'Table G.1A: exhaustive finite models', coverage,
         [('states','States'),('models','Models'),('norm','Norm'),('permitted','Permitted'),
          ('admitted','Admitted'),('coverage_percent','Coverage (percent)'),('unsound_admissions','Unsound')]),
        ('table_G1_B_and_S2', 'Table G.1B / Supplementary Table S2: all short programs', small,
         [('norm','Norm'),('horizon','H'),('permitted','Permitted'),('forbidden','Forbidden'),
          ('unresolved','Unresolved'),('false_permissions','FP'),('false_prohibitions','FN'),('certified','Certified')]),
        ('table_G1_C_and_S3', 'Table G.1C / Supplementary Table S3: sampled programs', sampled,
         [('length','L'),('norm','Norm'),('horizon','H'),('permitted','Permitted'),('forbidden','Forbidden'),
          ('unresolved','Unresolved'),('false_permissions','FP'),('false_prohibitions','FN'),('certified','Certified')]),
        ('table_S4', 'Supplementary Table S4: Simulation 2', main,
         [('length','L'),('unsafe','Unsafe'),('safety_unresolved','S-unres'),('conf_unresolved','C-unres'),
          ('safety_false_permission_percent_H8','FP8 (percent)'),('safety_false_permission_percent_H16','FP16 (percent)'),
          ('safety_false_permission_percent_H32','FP32 (percent)'),('safety_false_permission_percent_H64','FP64 (percent)'),
          ('conf_false_prohibition_percent_H4096','Plateau (percent)'),('median_first_bad','Median'),('p99','p99'),
          ('p999','p999'),('max_first_bad','Max')]),
    ]
    tex = [r'\documentclass[10pt]{article}', r'\usepackage[a4paper,margin=12mm]{geometry}',
           r'\usepackage[T1]{fontenc}', r'\usepackage{booktabs,longtable,pdflscape}',
           r'\begin{document}', r'\section*{Numerical tables regenerated from the v14 data}',
           r'FP means false permission; FN means false prohibition. Counts exclude unresolved programs where appropriate.',
           r'The CSV exports retain all original columns. Table ordering and typography differ from the manuscript.',
           r'\begin{landscape}\scriptsize\setlength{\tabcolsep}{3pt}']
    md = ['# Numerical tables', '', 'Generated from CSV data. See `docs/RESULTS_MAP.md` for manuscript locations.', '']
    for name, title, rows, columns in specifications:
        with (output / (name + '.csv')).open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)
        md += ['## ' + title, '', '| ' + ' | '.join(label for _,label in columns) + ' |',
               '| ' + ' | '.join('---' for _ in columns) + ' |']
        md += ['| ' + ' | '.join(str(row[key]) for key,_ in columns) + ' |' for row in rows]
        md.append('')
        alignment = 'l' * len(columns)
        tex += [r'\begin{longtable}{' + alignment + '}', r'\caption{' + escape(title) + r'}\\', r'\toprule',
                ' & '.join(escape(label) for _,label in columns) + r'\\\midrule\endfirsthead',
                r'\toprule ' + ' & '.join(escape(label) for _,label in columns) + r'\\\midrule\endhead']
        tex += [' & '.join(escape(row[key]) for key,_ in columns) + r'\\' for row in rows]
        tex += [r'\bottomrule\end{longtable}', r'\clearpage']
    tex += [r'\end{landscape}\end{document}']
    (output / 'numerical_tables.tex').write_text('\n'.join(tex)+'\n', encoding='utf-8')
    (output / 'numerical_tables.md').write_text('\n'.join(md)+'\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path(__file__).resolve().parents[1] / 'reproducibility')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    export(args.data, args.output)
