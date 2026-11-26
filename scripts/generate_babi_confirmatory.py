#!/usr/bin/env python3
"""Generate the independent bAbI-compatible structured confirmatory inputs."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from rgm.experiments.babi_synthetic_confirmatory import write_confirmatory_inputs

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotation-root", type=Path, default=Path("artifacts/babi-structured"))
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/babi-confirmatory"))
    args = parser.parse_args()
    report = write_confirmatory_inputs(args.output_root, args.annotation_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
