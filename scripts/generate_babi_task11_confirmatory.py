#!/usr/bin/env python3
"""Generate or verify the Task 11-only confirmatory challenge after candidate selection."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from rgm.experiments.babi_expansion_confirmatory import (
    generate_task11_confirmatory,
    verify_task11_confirmatory,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("generate", "verify"))
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    result = (
        generate_task11_confirmatory(args.output_root)
        if args.action == "generate"
        else verify_task11_confirmatory(args.output_root)
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
