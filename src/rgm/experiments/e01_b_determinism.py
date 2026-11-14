"""Compare independent CI replicas of one E01-B cell for deterministic evidence."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def _compare(a: Any, b: Any, path: str, differences: list[str]) -> None:
    if isinstance(a, bool) or isinstance(b, bool):
        if a != b:
            differences.append(path)
        return
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if not math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-12):
            differences.append(path)
        return
    if type(a) is not type(b):
        differences.append(path)
        return
    if isinstance(a, dict):
        if set(a) != set(b):
            differences.append(path + " [keys]")
            return
        for key in sorted(a):
            _compare(a[key], b[key], f"{path}.{key}", differences)
        return
    if isinstance(a, list):
        if len(a) != len(b):
            differences.append(path + " [length]")
            return
        for index, (left, right) in enumerate(zip(a, b)):
            _compare(left, right, f"{path}[{index}]", differences)
        return
    if a != b:
        differences.append(path)


def compare(input_dir: Path) -> dict[str, Any]:
    files = sorted(input_dir.glob("*replica-*.json"))
    if len(files) != 2:
        raise ValueError(f"expected exactly two replica JSON files, found {len(files)}")
    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in files]
    differences: list[str] = []
    _compare(payloads[0], payloads[1], "$", differences)
    return {
        "experiment": "E01-B deterministic replica audit",
        "files": [path.name for path in files],
        "comparison_tolerance": {"relative": 1e-12, "absolute": 1e-12},
        "equivalent": not differences,
        "difference_count": len(differences),
        "first_differences": differences[:25],
        "cell": {
            "condition": payloads[0].get("condition"),
            "memory_arm": payloads[0].get("memory_arm"),
            "world_seed": payloads[0].get("world_seed"),
            "codebook_seed": payloads[0].get("codebook_seed"),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.input_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["equivalent"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
