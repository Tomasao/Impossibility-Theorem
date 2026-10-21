#!/usr/bin/env python3
"""Run the protocol twice and compare every deterministic output byte.

Runtime metadata and its checksum manifest can depend on the Python version.
They are excluded from comparisons with the archived data, but both new runs
must reproduce all non-runtime outputs exactly.
"""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    excluded = {"runtime.json", "sha256_manifest.json"}
    records = []
    with tempfile.TemporaryDirectory(prefix="normative-reproduction-") as folder:
        outputs = [Path(folder) / "run1", Path(folder) / "run2"]
        for output in outputs:
            subprocess.run([sys.executable, str(root / "run_simulations.py"),
                            "--output", str(output)], check=True,
                           stdout=subprocess.PIPE)
        names = sorted(p.name for p in (root / "data").iterdir()
                       if p.is_file() and p.name not in excluded)
        for name in names:
            archived = (root / "data" / name).read_bytes()
            first, second = [(output / name).read_bytes() for output in outputs]
            if first != second or first != archived:
                raise SystemExit("Reproduction mismatch: " + name)
            records.append(dict(file=name, sha256=hashlib.sha256(first).hexdigest()))
    result = dict(status="passed", deterministic_files_checked=len(records),
                  runtime_excluded=sorted(excluded), files=records)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
