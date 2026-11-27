"""Deterministic generated confirmatory challenges for bAbI expansion tasks.

Input observations and evaluator labels are written to separate files. These
records are not official bAbI test data and are generated independently of the
source adapter's training/validation split.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import random
from typing import Any

CONFIRMATORY_SEEDS = (971101, 971102, 971103)
STORIES_PER_SEED = 128
TASKS = (11, 14, 19)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _entity_token(rng: random.Random, index: int) -> str:
    consonants = "bcdfghjklmnprstvz"
    vowels = "aeiou"
    return "".join((rng.choice(consonants), rng.choice(vowels), rng.choice(consonants), rng.choice(vowels))) + str(index)


def _task11(rng: random.Random, seed: int, ordinal: int) -> tuple[dict, dict]:
    entities = [_entity_token(rng, i) for i in range(4)]
    genders = {entity: rng.choice(("female", "male")) for entity in entities}
    locations = [f"place_{rng.randrange(10_000, 99_999)}" for _ in range(12)]
    observations = []
    current: dict[str, str] = {}
    witnesses: dict[str, list[str]] = {entity: [] for entity in entities}
    tick = 0
    for entity in entities:
        tick += 1
        location = locations.pop()
        event_id = f"t11-s{seed}-story{ordinal:04d}-e{tick:03d}"
        observations.append({
            "event_id": event_id,
            "surface_mention": entity,
            "is_pronoun": False,
            "grammatical_gender": genders[entity],
            "location": location,
            "observed_at": tick,
        })
        current[entity] = location
        witnesses[entity].append(event_id)
    for _ in range(8):
        tick += 1
        entity = rng.choice(entities)
        use_pronoun = rng.random() < 0.60
        surface = ("she" if genders[entity] == "female" else "he") if use_pronoun else entity
        location = locations.pop()
        event_id = f"t11-s{seed}-story{ordinal:04d}-e{tick:03d}"
        observations.append({
            "event_id": event_id,
            "surface_mention": surface,
            "is_pronoun": use_pronoun,
            "grammatical_gender": genders[entity] if use_pronoun else genders[entity],
            "location": location,
            "observed_at": tick,
        })
        current[entity] = location
        witnesses[entity].append(event_id)
    target = rng.choice(entities)
    query = {
        "query_id": f"t11-s{seed}-story{ordinal:04d}-q",
        "task_id": 11,
        "target_entity": target,
        "observed_at": tick + 1,
    }
    inp = {"story_id": f"t11-s{seed}-story{ordinal:04d}", "task_id": 11,
           "observations": observations, "query": query}
    label = {"query_id": query["query_id"], "gold_answer": current[target],
             "support_event_ids": witnesses[target]}
    return inp, label


def _task14(rng: random.Random, seed: int, ordinal: int) -> tuple[dict, dict]:
    actor = f"actor_{rng.randrange(100_000, 999_999)}"
    anchors = ["yesterday", "this morning", "this afternoon", "this evening"]
    rng.shuffle(anchors)
    # Events are observed in a shuffled order; event-time order is represented
    # only by the temporal anchor feature, not by source position.
    rows = []
    for index, anchor in enumerate(anchors):
        rows.append({
            "event_id": f"t14-s{seed}-story{ordinal:04d}-e{index + 1:03d}",
            "actor": actor,
            "destination": f"place_{rng.randrange(10_000, 99_999)}",
            "temporal_anchor": anchor,
            "event_time_rank": {"yesterday": 0, "this morning": 1,
                                "this afternoon": 2, "this evening": 3}[anchor],
            "observed_at": index + 1,
        })
    target = rows[rng.randrange(1, len(rows))]
    earlier = [row for row in rows if row["event_time_rank"] < target["event_time_rank"]]
    if not earlier:
        # Deterministically select the latest temporal anchor as query target.
        target = max(rows, key=lambda row: row["event_time_rank"])
        earlier = [row for row in rows if row["event_time_rank"] < target["event_time_rank"]]
    previous = max(earlier, key=lambda row: (row["event_time_rank"], row["observed_at"]))
    query = {
        "query_id": f"t14-s{seed}-story{ordinal:04d}-q",
        "task_id": 14,
        "actor": actor,
        "target_destination": target["destination"],
        "observed_at": len(rows) + 1,
    }
    inp = {"story_id": f"t14-s{seed}-story{ordinal:04d}", "task_id": 14,
           "observations": rows, "query": query}
    label = {"query_id": query["query_id"], "gold_answer": previous["destination"],
             "support_event_ids": [previous["event_id"], target["event_id"]]}
    return inp, label


def _task19(rng: random.Random, seed: int, ordinal: int) -> tuple[dict, dict]:
    node_count = rng.randint(4, 6)
    nodes = [f"place_{rng.randrange(100_000, 999_999)}" for _ in range(node_count)]
    direction_names = ("north", "south", "east", "west")
    observations = []
    directions = []
    for index in range(node_count - 1):
        direction = rng.choice(direction_names)
        directions.append(direction)
        observations.append({
            "event_id": f"t19-s{seed}-story{ordinal:04d}-e{index + 1:03d}",
            "start": nodes[index],
            "end": nodes[index + 1],
            "direction": direction,
            "observed_at": index + 1,
        })
    query = {
        "query_id": f"t19-s{seed}-story{ordinal:04d}-q",
        "task_id": 19,
        "start_location": nodes[0],
        "end_location": nodes[-1],
        "observed_at": len(observations) + 1,
    }
    answer_codes = {"north": "n", "south": "s", "east": "e", "west": "w"}
    inp = {"story_id": f"t19-s{seed}-story{ordinal:04d}", "task_id": 19,
           "observations": observations, "query": query}
    label = {"query_id": query["query_id"],
             "gold_answer": ",".join(answer_codes[d] for d in directions),
             "support_event_ids": [row["event_id"] for row in observations]}
    return inp, label


_GENERATORS = {11: _task11, 14: _task14, 19: _task19}


def generate(output_root: Path) -> dict:
    output_root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "HLG-BABI-EXPANSION-CONFIRMATORY-v1",
        "protocol_id": "HLG-BABI-EXPANSION-CONFIRMATORY-v1",
        "status": "FROZEN_GENERATOR_AND_SEEDS",
        "not_official_babi_test": True,
        "seeds": list(CONFIRMATORY_SEEDS),
        "stories_per_seed_per_task": STORIES_PER_SEED,
        "task_ids": list(TASKS),
        "task_generators": {
            "11": "raw name/pronoun mentions, novel entity tokens, location-state query; no resolved antecedent in input",
            "14": "shuffled source-order temporal events with explicit ordinal anchor features; before-destination query",
            "19": "novel directed spatial chain with ordered route query and source edge witnesses",
        },
        "input_label_separation": "Input JSONL never contains gold_answer, support_event_ids or evaluator annotations. Labels are written to a distinct evaluator-only JSONL.",
        "labels_used_for_learning": False,
        "official_test_access": False,
        "files": {},
    }
    for task_id in TASKS:
        inputs_path = output_root / f"task{task_id}-inputs.jsonl"
        labels_path = output_root / f"task{task_id}-evaluator-labels.jsonl"
        input_rows, label_rows = [], []
        for seed in CONFIRMATORY_SEEDS:
            rng = random.Random(f"HLG-BABI-CONFIRMATORY-v1:{task_id}:{seed}")
            for ordinal in range(STORIES_PER_SEED):
                inp, label = _GENERATORS[task_id](rng, seed, ordinal)
                input_rows.append(inp)
                label_rows.append(label)
        inputs_path.write_text(
            "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in input_rows),
            encoding="utf-8",
        )
        labels_path.write_text(
            "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in label_rows),
            encoding="utf-8",
        )
        input_ids = [row["query"]["query_id"] for row in input_rows]
        label_ids = [row["query_id"] for row in label_rows]
        if len(set(input_ids)) != len(input_ids) or set(input_ids) != set(label_ids):
            raise AssertionError(f"Task {task_id}: confirmatory query/label identity mismatch")
        forbidden = {"gold_answer", "support_event_ids", "support_line_numbers", "answer"}
        for row in input_rows:
            if forbidden & set(row):
                raise AssertionError(f"Task {task_id}: evaluator field found in input record")
            if forbidden & set(row["query"]):
                raise AssertionError(f"Task {task_id}: evaluator field found in query")
            for event in row["observations"]:
                if forbidden & set(event):
                    raise AssertionError(f"Task {task_id}: evaluator field found in observation")
        manifest["files"][str(task_id)] = {
            "inputs": {"path": inputs_path.name, "rows": len(input_rows), "sha256": _sha(inputs_path)},
            "evaluator_labels": {"path": labels_path.name, "rows": len(label_rows), "sha256": _sha(labels_path)},
            "input_query_ids_sha256": sha256("\n".join(input_ids).encode()).hexdigest(),
            "label_query_ids_sha256": sha256("\n".join(label_ids).encode()).hexdigest(),
            "input_label_query_ids_match": True,
        }
    manifest["manifest_sha256"] = sha256(_canonical(manifest)).hexdigest()
    manifest_path = output_root / "confirmatory-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["manifest_file_sha256"] = _sha(manifest_path)
    return manifest


def verify(output_root: Path) -> dict:
    manifest_path = output_root / "confirmatory-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for task_id in TASKS:
        record = manifest["files"][str(task_id)]
        for key in ("inputs", "evaluator_labels"):
            path = output_root / record[key]["path"]
            if _sha(path) != record[key]["sha256"]:
                raise ValueError(f"Task {task_id}: {key} digest mismatch")
        inputs = [json.loads(line) for line in (output_root / record["inputs"]["path"]).read_text().splitlines()]
        labels = [json.loads(line) for line in (output_root / record["evaluator_labels"]["path"]).read_text().splitlines()]
        if len(inputs) != STORIES_PER_SEED * len(CONFIRMATORY_SEEDS) or len(labels) != len(inputs):
            raise ValueError(f"Task {task_id}: unexpected challenge row count")
        input_ids = {row["query"]["query_id"] for row in inputs}
        label_ids = {row["query_id"] for row in labels}
        if input_ids != label_ids:
            raise ValueError(f"Task {task_id}: input/label partition mismatch")
        if any("gold_answer" in json.dumps(row) or "support_event_ids" in json.dumps(row) for row in inputs):
            raise ValueError(f"Task {task_id}: evaluator content leaked into inputs")
    return {"status": "PASS", "manifest_sha256": manifest["manifest_sha256"],
            "task_count": len(TASKS), "stories_per_task": STORIES_PER_SEED * len(CONFIRMATORY_SEEDS)}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/babi-expansion-confirmatory"))
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    result = verify(args.output_root) if args.verify else generate(args.output_root)
    print(json.dumps(result, indent=2, sort_keys=True))
