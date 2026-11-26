#!/usr/bin/env python3
"""Run the frozen H1 hierarchical validation or confirmatory campaign."""
from __future__ import annotations
import argparse
import json
from rgm.experiments.h1_hierarchical_campaign import run_hierarchical_campaign

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--partition", required=True,
                        choices=("validation", "confirmatory_test"))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = run_hierarchical_campaign(args.partition, args.output)
    print(json.dumps({
        "result": result["result"],
        "partition": result["partition"],
        "world_seed_count": result["world_seed_count"],
        "world_instance_count": result["world_instance_count"],
        "campaign_summary": result["campaign_summary"],
        "hard_integrity": result["hard_integrity"],
        "runtime": result["runtime"],
        "output": args.output,
    }, indent=2))
    if result["result"] != "PASS":
        raise SystemExit(1)

if __name__ == "__main__":
    main()
