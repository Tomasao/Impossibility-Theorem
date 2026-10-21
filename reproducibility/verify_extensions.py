#!/usr/bin/env python3
"""Run run_extensions.py twice and compare every output byte with data_extensions/."""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    records = []
    with tempfile.TemporaryDirectory(prefix="normative-extensions-") as folder:
        outputs = [Path(folder) / "run1", Path(folder) / "run2"]
        for output in outputs:
            subprocess.run([sys.executable, str(root / "run_extensions.py"),
                            "--output", str(output)], check=True,
                           stdout=subprocess.PIPE)
        for archived in sorted((root / "data_extensions").iterdir()):
            first, second = [(output / archived.name).read_bytes() for output in outputs]
            if first != second or first != archived.read_bytes():
                raise SystemExit("Reproduction mismatch: " + archived.name)
            records.append(dict(file=archived.name,
                                sha256=hashlib.sha256(first).hexdigest()))
    print(json.dumps(dict(status="passed", files_checked=len(records),
                          files=records), indent=2))


if __name__ == "__main__":
    main()
