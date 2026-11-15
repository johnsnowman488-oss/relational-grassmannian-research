"""Execute frozen deterministic multi-route reference cases for HLG-M2."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from rgm.leptograph.m2 import CASE_IDS, run_case

EXPERIMENT_ID = "HYBRID-LEPTOGRAPH-M2"
SCHEMA_VERSION = "1.0"


def verify_result_directory(directory: Path) -> dict:
    cases = []
    for case_id in CASE_IDS:
        path = directory / f"{case_id}.json"
        if not path.is_file():
            raise FileNotFoundError(f"missing M2 evidence file: {path}")
        result = json.loads(path.read_text(encoding="utf-8"))
        if result.get("experiment_id") != EXPERIMENT_ID or result.get("case_id") != case_id:
            raise ValueError(f"invalid experiment/case identity in {path}")
        if result.get("passed") is not True:
            raise AssertionError(f"M2 case {case_id} did not pass")
        cases.append({"case_id": case_id, "passed": True})
    return {
        "experiment_id": EXPERIMENT_ID,
        "schema_version": SCHEMA_VERSION,
        "case_ids": list(CASE_IDS),
        "case_count": len(cases),
        "all_cases_passed": True,
        "cases": cases,
    }


def _write_json(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASE_IDS)
    parser.add_argument("--verify-result-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (args.case is None) == (args.verify_result_dir is None):
        parser.error("specify exactly one of --case or --verify-result-dir")
    result = run_case(args.case) if args.case else verify_result_directory(args.verify_result_dir)
    digest = _write_json(args.output, result)
    print(json.dumps({"output": str(args.output), "sha256": digest, **result}, sort_keys=True))
    if result.get("passed") is False or result.get("all_cases_passed") is False:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
