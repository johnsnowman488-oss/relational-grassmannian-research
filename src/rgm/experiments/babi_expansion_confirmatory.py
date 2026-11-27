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
    """Generate an identifiable two-entity coreference episode.

    The two name anchors have distinct, explicitly model-visible grammatical-
    gender cues. Every pronoun therefore has exactly one compatible antecedent.
    The generated cue is part of the synthetic input schema, not a hidden
    evaluator-only attribute or a claim about raw bAbI surface text.
    """
    entities = [_entity_token(rng, i) for i in range(2)]
    genders = {entities[0]: "female", entities[1]: "male"}
    locations = [f"place_{rng.randrange(10_000, 99_999)}" for _ in range(12)]
    story_id = f"t11-s{seed}-story{ordinal:04d}"
    observations = []
    current: dict[str, str] = {}
    witnesses: dict[str, list[str]] = {entity: [] for entity in entities}
    anchor_event_ids: dict[str, str] = {}
    current_anchor_event_ids: dict[str, str] = {}
    last_event_ids: dict[str, str] = {}
    last_was_pronoun: dict[str, bool] = {}
    binding_edges = []
    tick = 0

    for entity in entities:
        tick += 1
        location = locations.pop()
        event_id = f"{story_id}-e{tick:03d}"
        anchor_event_ids[entity] = event_id
        current_anchor_event_ids[entity] = event_id
        source_ref = f"{story_id}#event={tick:03d}"
        observations.append({
            "event_id": event_id,
            "surface_mention": entity,
            "is_pronoun": False,
            "grammatical_gender": genders[entity],
            "location": location,
            "observed_at": tick,
            "source_ref": source_ref,
        })
        current[entity] = location
        witnesses[entity].append(event_id)
        last_event_ids[entity] = event_id
        last_was_pronoun[entity] = False

    for _ in range(8):
        tick += 1
        entity = rng.choice(entities)
        use_pronoun = rng.random() < 0.60
        surface = ("she" if genders[entity] == "female" else "he") if use_pronoun else entity
        location = locations.pop()
        event_id = f"{story_id}-e{tick:03d}"
        source_ref = f"{story_id}#event={tick:03d}"
        observations.append({
            "event_id": event_id,
            "surface_mention": surface,
            "is_pronoun": use_pronoun,
            "grammatical_gender": genders[entity],
            "location": location,
            "observed_at": tick,
            "source_ref": source_ref,
        })
        current[entity] = location
        witnesses[entity].append(event_id)
        last_event_ids[entity] = event_id
        last_was_pronoun[entity] = use_pronoun
        if use_pronoun:
            binding_edges.append({
                "mention_event_id": event_id,
                "antecedent_event_id": current_anchor_event_ids[entity],
                "entity_id": entity,
            })
        else:
            current_anchor_event_ids[entity] = event_id

    target = rng.choice(entities)
    target_event_id = last_event_ids[target]
    query = {
        "query_id": f"{story_id}-q",
        "task_id": 11,
        "entity": target,
        "observed_at": tick + 1,
        "source_ref": f"{story_id}#query",
    }
    inp = {
        "story_id": story_id,
        "task_id": 11,
        "events": observations,
        "query": query,
    }
    if last_was_pronoun[target]:
        l1_target = {
            "mention_event_id": target_event_id,
            "antecedent_event_id": current_anchor_event_ids[target],
            "entity_id": target,
            "relation": "corefers_with",
        }
    else:
        l1_target = {
            "mention_event_id": target_event_id,
            "antecedent_event_id": None,
            "entity_id": target,
            "relation": "self_anchor",
        }
    label = {
        "query_id": query["query_id"],
        "source_ref": f"{story_id}#evaluator-label",
        "gold_answer": current[target],
        "support_event_ids": witnesses[target],
        "mention_binding_edges": binding_edges,
        "task11_supervision": {
            "l0_mention_binding": {
                "mention_event_id": target_event_id,
                "entity_id": target,
            },
            "l1_coreference_edge": l1_target,
            "l2_entity_state": {
                "entity_id": target,
                "location": current[target],
                "witness_event_ids": witnesses[target],
            },
        },
    }
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
    nodes = [f"place_{rng.randrange(100_000, 999_999)}_{index}" for index in range(node_count)]
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
            "11": "two novel entities with distinct model-visible grammatical-gender cues; pronoun antecedents are uniquely identifiable; bindings/targets remain evaluator-only",
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
        forbidden = {"gold_answer", "support_event_ids", "support_line_numbers", "answer",
                     "mention_binding_edges", "task11_supervision", "antecedent_event_id"}
        for row in input_rows:
            if forbidden & set(row):
                raise AssertionError(f"Task {task_id}: evaluator field found in input record")
            if forbidden & set(row["query"]):
                raise AssertionError(f"Task {task_id}: evaluator field found in query")
            event_rows = row["events"] if task_id == 11 else row["observations"]
            for event in event_rows:
                if forbidden & set(event):
                    raise AssertionError(f"Task {task_id}: evaluator field found in observation")
            if task_id == 11:
                from rgm.experiments.babi_expansion_adapters import task11_confirmatory_input_to_story
                story = task11_confirmatory_input_to_story(row)
                anchors = {e.surface_mention: e.grammatical_gender for e in story.events if not e.is_pronoun}
                if len(anchors) != 2 or set(anchors.values()) != {"female", "male"}:
                    raise AssertionError("Task 11 confirmatory anchors must have distinct gender cues")
                for event in story.events:
                    if event.is_pronoun:
                        matches = [name for name, gender in anchors.items()
                                   if gender == event.grammatical_gender]
                        if len(matches) != 1:
                            raise AssertionError("Task 11 pronoun antecedent is not identifiable")
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
    manifest_core = dict(manifest)
    expected_manifest_sha = manifest_core.pop("manifest_sha256", None)
    actual_manifest_sha = sha256(_canonical(manifest_core)).hexdigest()
    if expected_manifest_sha != actual_manifest_sha:
        raise ValueError("confirmatory manifest fingerprint mismatch")
    if manifest.get("status") != "FROZEN_GENERATOR_AND_SEEDS":
        raise ValueError("confirmatory manifest is not frozen")
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
        input_id_list = [row["query"]["query_id"] for row in inputs]
        label_id_list = [row["query_id"] for row in labels]
        input_ids = set(input_id_list)
        label_ids = set(label_id_list)
        if len(input_ids) != len(input_id_list) or len(label_ids) != len(label_id_list):
            raise ValueError(f"Task {task_id}: duplicate confirmatory query/label IDs")
        if input_ids != label_ids:
            raise ValueError(f"Task {task_id}: input/label partition mismatch")
        forbidden_input_tokens = ("gold_answer", "support_event_ids", "support_line_numbers",
                                  "mention_binding_edges", "task11_supervision", "antecedent_event_id")
        if any(token in json.dumps(row) for row in inputs for token in forbidden_input_tokens):
            raise ValueError(f"Task {task_id}: evaluator content leaked into inputs")
        if task_id == 11:
            from rgm.experiments.babi_expansion_adapters import task11_confirmatory_input_to_story
            for row in inputs:
                task11_confirmatory_input_to_story(row)
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


TASK11_CONFIRMATORY_SEED = 953200
TASK11_CONFIRMATORY_STORIES = 384
TASK11_AMBIGUOUS_STORIES = 64


def generate_task11_confirmatory(output_root: Path) -> dict:
    """Generate the frozen Task 11-only challenge after validation selection.

    The generated input and evaluator labels are separate files. This function
    is intentionally not called by fit, validation, preflight or campaign jobs.
    """
    from rgm.experiments.babi_expansion_adapters import (
        derive_task11_weak_binding_targets,
        task11_confirmatory_input_to_story,
    )

    output_root.mkdir(parents=True, exist_ok=True)
    rng = random.Random(f"HLG-BABI-TASK11-CONFIRMATORY-v1:{TASK11_CONFIRMATORY_SEED}")
    inputs, labels = [], []
    for ordinal in range(TASK11_CONFIRMATORY_STORIES):
        inp, label = _task11(rng, TASK11_CONFIRMATORY_SEED, ordinal)
        if ordinal < TASK11_AMBIGUOUS_STORIES:
            target = label["task11_supervision"]["l2_entity_state"]["entity_id"]
            anchor = next(
                row for row in inp["events"]
                if not row["is_pronoun"] and row["surface_mention"] == target
            )
            gender = anchor["grammatical_gender"]
            third_name = _entity_token(rng, ordinal + 1000)
            tick = max(row["observed_at"] for row in inp["events"]) + 1
            inp["events"].append({
                "event_id": f"{inp['story_id']}-e{tick:03d}",
                "surface_mention": third_name,
                "is_pronoun": False,
                "grammatical_gender": gender,
                "location": f"place_{rng.randrange(10000, 99999)}",
                "observed_at": tick,
                "source_ref": f"{inp['story_id']}#event={tick:03d}",
            })
            tick += 1
            pronoun = "she" if gender == "female" else "he"
            inp["events"].append({
                "event_id": f"{inp['story_id']}-e{tick:03d}",
                "surface_mention": pronoun,
                "is_pronoun": True,
                "grammatical_gender": gender,
                "location": f"place_{rng.randrange(10000, 99999)}",
                "observed_at": tick,
                "source_ref": f"{inp['story_id']}#event={tick:03d}",
            })
            inp["query"]["observed_at"] = tick + 1
            inp["query"]["source_ref"] = f"{inp['story_id']}#query"
            labels.append({
                "query_id": inp["query"]["query_id"],
                "expected_abstention": True,
                "expected_reason": "ambiguous_entity_mention_after_last_grounded_state",
                "ambiguous_pronoun_event_id": inp["events"][-1]["event_id"],
            })
        else:
            labels.append({
                "query_id": label["query_id"],
                "expected_abstention": False,
                "gold_answer": label["gold_answer"],
                "support_event_ids": label["support_event_ids"],
            })
        story = task11_confirmatory_input_to_story(inp)
        weak = derive_task11_weak_binding_targets(story)
        if ordinal < TASK11_AMBIGUOUS_STORIES:
            if not any(row["reason"] == "ambiguous_gender_candidates"
                       for row in weak["abstentions"]):
                raise AssertionError("ambiguous confirmatory case did not trigger weak-binding abstention")
        elif weak["abstentions"]:
            raise AssertionError("uniquely resolvable confirmatory case unexpectedly abstained")
        inputs.append(inp)

    input_path = output_root / "task11-confirmatory-inputs.jsonl"
    label_path = output_root / "task11-confirmatory-evaluator-labels.jsonl"
    input_path.write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\\n" for row in inputs),
        encoding="utf-8",
    )
    label_path.write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\\n" for row in labels),
        encoding="utf-8",
    )
    input_ids = [row["query"]["query_id"] for row in inputs]
    label_ids = [row["query_id"] for row in labels]
    if len(set(input_ids)) != TASK11_CONFIRMATORY_STORIES or set(input_ids) != set(label_ids):
        raise AssertionError("Task 11 confirmatory query/label identities are not one-to-one")
    forbidden = {
        "gold_answer", "support_event_ids", "mention_binding_edges",
        "task11_supervision", "antecedent_event_id", "expected_abstention",
    }
    for row in inputs:
        if forbidden & set(row) or forbidden & set(row["query"]):
            raise AssertionError("evaluator data leaked into Task 11 confirmatory inputs")
        if any(forbidden & set(event) for event in row["events"]):
            raise AssertionError("evaluator data leaked into Task 11 confirmatory observations")

    manifest = {
        "schema": "HLG-BABI-TASK11-CONFIRMATORY-v1",
        "protocol_id": "HLG-BABI-TASK11-CONFIRMATORY-v1",
        "status": "FROZEN_GENERATOR_AND_SEEDS",
        "not_official_babi_test": True,
        "task_ids": [11],
        "seed": TASK11_CONFIRMATORY_SEED,
        "story_count": TASK11_CONFIRMATORY_STORIES,
        "answerable_story_count": TASK11_CONFIRMATORY_STORIES - TASK11_AMBIGUOUS_STORIES,
        "ambiguous_abstention_story_count": TASK11_AMBIGUOUS_STORIES,
        "input_label_separation": "Distinct JSONL files; inputs contain no evaluator answers, support IDs or expected-abstention labels.",
        "labels_used_for_learning": False,
        "official_test_access": False,
        "files": {
            "inputs": {
                "path": input_path.name, "rows": len(inputs), "sha256": _sha(input_path),
                "query_ids_sha256": sha256("\\n".join(input_ids).encode()).hexdigest(),
            },
            "evaluator_labels": {
                "path": label_path.name, "rows": len(labels), "sha256": _sha(label_path),
                "query_ids_sha256": sha256("\\n".join(label_ids).encode()).hexdigest(),
            },
        },
    }
    manifest["manifest_sha256"] = sha256(_canonical(manifest)).hexdigest()
    manifest_path = output_root / "task11-confirmatory-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\\n",
                             encoding="utf-8")
    manifest["manifest_file_sha256"] = _sha(manifest_path)
    return manifest


def evaluate_task11_confirmatory(inputs: list[dict], labels: list[dict],
                                 decisions: dict[str, Any]) -> dict:
    """Evaluate once-selected predictions against the separately sealed labels."""
    input_by_id = {row["query"]["query_id"]: row for row in inputs}
    label_by_id = {row["query_id"]: row for row in labels}
    if len(input_by_id) != len(inputs) or len(label_by_id) != len(labels):
        raise ValueError("duplicate Task 11 confirmatory query/label IDs")
    if set(input_by_id) != set(label_by_id) or set(input_by_id) != set(decisions):
        raise ValueError("Task 11 confirmatory input, label and prediction IDs differ")

    answerable = [row for row in labels if not row["expected_abstention"]]
    ambiguous = [row for row in labels if row["expected_abstention"]]
    answer_correct = 0
    answer_covered = 0
    true_witnesses = 0
    total_witnesses = 0
    false_witnesses = 0
    correct_abstentions = 0
    false_acceptances = 0
    for label in answerable:
        prediction = decisions[label["query_id"]].prediction
        if not prediction.abstained:
            answer_covered += 1
            answer_correct += int(prediction.answer == label["gold_answer"])
        predicted = set(prediction.witness_event_ids)
        gold = set(label["support_event_ids"])
        true_witnesses += len(predicted & gold)
        total_witnesses += len(gold)
        false_witnesses += len(predicted - gold)
    for label in ambiguous:
        prediction = decisions[label["query_id"]].prediction
        correct_abstentions += int(prediction.abstained)
        false_acceptances += int(not prediction.abstained)

    return {
        "schema": "HLG-BABI-TASK11-CONFIRMATORY-SCORE-v1",
        "task_id": 11,
        "query_count": len(labels),
        "answerable_query_count": len(answerable),
        "ambiguous_query_count": len(ambiguous),
        "answer_exact_match_on_answerable": (
            answer_correct / len(answerable) if answerable else None
        ),
        "answer_coverage_on_answerable": (
            answer_covered / len(answerable) if answerable else None
        ),
        "support_witness_recall": (
            true_witnesses / total_witnesses if total_witnesses else None
        ),
        "false_witness_rate": (
            false_witnesses / (true_witnesses + false_witnesses)
            if true_witnesses + false_witnesses else None
        ),
        "ambiguous_abstention_recall": (
            correct_abstentions / len(ambiguous) if ambiguous else None
        ),
        "ambiguous_false_acceptances": false_acceptances,
        "label_boundary": "Generated evaluator labels are consumed only after candidate predictions are fixed.",
    }
