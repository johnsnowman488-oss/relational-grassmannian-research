#!/usr/bin/env python3
"""Create the source-indexed structured bAbI input/label bundle."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from rgm.experiments.babi_annotation import write_annotation_bundle

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=Path("data/babi-v1.2"))
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/babi-structured"))
    args = parser.parse_args()
    report = write_annotation_bundle(args.source_root, args.output_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
