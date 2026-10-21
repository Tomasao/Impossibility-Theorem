#!/usr/bin/env python3
"""Review or update hashes of existing manifest entries after deliberate edits."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write',action='store_true',help='Write reviewed current hashes; does not alter provenance')
    args=parser.parse_args()
    path=ROOT/'MANIFEST_SHA256.json'
    manifest=json.loads(path.read_text())
    changes=[]
    for name,old in manifest['files'].items():
        file=(ROOT/name).resolve()
        if ROOT not in file.parents or not file.is_file():
            raise SystemExit('Missing or invalid manifest path: '+name)
        new=hashlib.sha256(file.read_bytes()).hexdigest()
        if old!=new: changes.append(name)
        manifest['files'][name]=new
    print(json.dumps({'changed_files':changes,'write_requested':args.write},indent=2))
    if args.write:
        path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        print('Updated current-package hashes. Original-source provenance was not changed.')
    return 0


if __name__=='__main__':raise SystemExit(main())
