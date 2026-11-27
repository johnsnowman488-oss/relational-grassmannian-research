#!/usr/bin/env python3
"""Run one matched HLA/HLB bAbI task campaign against compiled Aberconics C++."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import gfe_ctypes
from rgm.experiments.babi_learning_campaign import CHANNELS, run_campaign

DEFAULT_SEEDS = list(range(953000, 953010))

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", type=int, choices=(3, 5), required=True)
    parser.add_argument("--architecture", choices=("HLA", "HLB"), required=True)
    parser.add_argument("--data-root", type=Path, default=Path("data/babi-v1.2"))
    parser.add_argument("--annotation-root", type=Path, default=Path("artifacts/babi-structured"))
    parser.add_argument("--confirmatory-root", type=Path, default=Path("artifacts/babi-confirmatory"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=DEFAULT_SEEDS)
    parser.add_argument(
        "--variants", choices=tuple(CHANNELS), nargs="+", default=list(CHANNELS),
        help="A unique subset of the six frozen learning/ablation conditions (default: all six).",
    )
    parser.add_argument(
        "--phase", choices=("validation", "confirmatory"), default="validation",
        help="Run the matched validation campaign, or reconstruct one selected full-learning candidate and evaluate it once.",
    )
    parser.add_argument(
        "--selection-file", type=Path, default=Path("artifacts/selected-candidates.json"),
        help="Validation-only candidate selection artifact required for confirmatory phase.",
    )
    args = parser.parse_args()

    expected_candidate_fingerprint = None
    if args.phase == "confirmatory":
        if not args.selection_file.is_file():
            raise FileNotFoundError(f"selected-candidate manifest not found: {args.selection_file}")
        selection = json.loads(args.selection_file.read_text(encoding="utf-8"))
        selected = selection["selected_candidates"][str(args.task_id)]
        args.seeds = [int(selected["seed"])]
        args.variants = ["full_learning"]
        expected_candidate_fingerprint = selected["candidate_fingerprints"][args.architecture]

    native_library = gfe_ctypes.load_gfe_library()
    result = run_campaign(
        args.task_id, args.architecture, args.data_root,
        args.annotation_root, args.confirmatory_root, args.output,
        args.seeds, gfe_ctypes, native_library,
        variants=args.variants,
        run_confirmatory=args.phase == "confirmatory",
        selection_manifest_path=args.selection_file if args.phase == "confirmatory" else None,
    )
    if args.phase == "confirmatory":
        actual = result["results"][0]["candidate_fingerprint"]
        if actual != expected_candidate_fingerprint:
            raise RuntimeError(
                "reconstructed candidate fingerprint differs from validation-selected candidate: "
                f"expected {expected_candidate_fingerprint}, got {actual}"
            )
    accepted = sum(
        row["candidate_accepted_on_validation"]
        for row in result["results"]
    )
    print(json.dumps({
        "task_id": args.task_id,
        "architecture": args.architecture,
        "run_count": result["run_count"],
        "validation_accepted": accepted,
        "output": str(args.output),
    }, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
