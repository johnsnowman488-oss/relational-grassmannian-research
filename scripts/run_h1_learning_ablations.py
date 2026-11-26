"""Run the deterministic H1 learning-channel ablation campaign."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from rgm.experiments.h1_learning_ablations import run_learning_ablation_campaign


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/h1-learning-ablations.json")
    args = parser.parse_args()
    result = run_learning_ablation_campaign()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"acceptance": result["acceptance"],
                      "manifest_fingerprint": result["manifest_fingerprint"],
                      "rows": result["rows"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
