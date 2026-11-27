#!/usr/bin/env python3
"""Generate or verify the frozen Task 11/14/19 confirmatory challenge."""
from rgm.experiments.babi_expansion_confirmatory import generate, verify
from pathlib import Path
import argparse
import json

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/babi-expansion-confirmatory"))
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    result = verify(args.output_root) if args.verify else generate(args.output_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
