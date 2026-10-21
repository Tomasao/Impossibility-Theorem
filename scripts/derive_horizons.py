#!/usr/bin/env python3
"""Regenerate the v14 first-violation table using exact order statistics."""
import argparse
import csv
import json
from pathlib import Path


def derive(data):
    meta = json.loads((data / 'sim2_first_bad_meta.json').read_text())
    with (data / 'sim2_landscape.csv').open(newline='') as handle:
        landscape = list(csv.DictReader(handle))
    rows = []
    for item in sorted(meta, key=lambda m: m['length']):
        hist = sorted((int(k), int(v)) for k, v in item['first_bad_hist'].items())
        count = sum(v for _, v in hist)
        if not count or count != item['n_forbidden']:
            raise ValueError('Invalid first-violation histogram')
        def percentile(numerator, denominator):
            index = (count - 1) * numerator // denominator
            cumulative = 0
            for step, frequency in hist:
                cumulative += frequency
                if cumulative > index:
                    return step
            raise AssertionError('Missing order statistic')
        group = sorted((r for r in landscape if int(r['length']) == item['length']),
                       key=lambda r: int(r['horizon']))
        if any(int(r['safety_forbidden']) != count for r in group):
            raise ValueError('Histogram and landscape disagree')
        clear = [int(r['horizon']) for i, r in enumerate(group)
                 if all(int(s['safety_false_permissions']) == 0 for s in group[i:])]
        rows.append(dict(length=item['length'], unsafe_programs=count,
                         median_first_bad=percentile(1, 2), p99=percentile(99, 100),
                         p999=percentile(999, 1000), max_first_bad=hist[-1][0],
                         min_errorfree_horizon_tested=min(clear) if clear else ''))
    return rows


def write(data, output):
    rows = derive(data)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path(__file__).resolve().parents[1] / 'reproducibility')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    write(args.data, args.output)
