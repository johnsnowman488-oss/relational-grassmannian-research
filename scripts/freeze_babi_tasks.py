#!/usr/bin/env python3
"""Acquire and byte-freeze official bAbI v1.2 Task 3/5 source data.

The upstream v1.2 archive supplies official en-10k train/test files. This
protocol derives a deterministic 10% validation partition from whole training
stories, preserving the official test split untouched. No text parsing occurs.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
import tarfile
from urllib.request import Request, urlopen

ARCHIVE_URL = "https://s3.amazonaws.com/text-datasets/babi_tasks_1-20_v1-2.tar.gz"
EXPECTED_SHA256 = "84f5296ab9a1ad0dc9464e08c491d65cd08830fca3acae9ab86f75e0fb81573c"
EXPECTED_SIZE = 11_745_123
PREFIX = "tasks_1-20_v1-2/en-10k/"
VALIDATION_FRACTION = 0.10
VALIDATION_SEED = "HLG-BABI-T3-T5-VALIDATION-v1"
SOURCE_FILES = {
    "task3_train_source": PREFIX + "qa3_three-supporting-facts_train.txt",
    "task3_test_debug_only": PREFIX + "qa3_three-supporting-facts_test.txt",
    "task3_confirmatory_source": "tasks_1-20_v1-2/en/qa3_three-supporting-facts_test.txt",
    "task5_train_source": PREFIX + "qa5_three-arg-relations_train.txt",
    "task5_test_debug_only": PREFIX + "qa5_three-arg-relations_test.txt",
    "task5_confirmatory_source": "tasks_1-20_v1-2/en/qa5_three-arg-relations_test.txt",
}


def digest(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def split_story_blocks(payload: bytes, *, task_id: int) -> tuple[bytes, bytes, dict]:
    """Deterministically split complete numbered stories, never individual lines."""
    lines = payload.splitlines(keepends=True)
    blocks: list[bytes] = []
    current: list[bytes] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                current.append(line)
            continue
        prefix = stripped.split(None, 1)[0]
        if prefix == b"1":
            if current:
                blocks.append(b"".join(current))
            current = [line]
        elif current:
            current.append(line)
        else:
            raise ValueError("source split begins before first story reset")
    if current:
        blocks.append(b"".join(current))
    if not blocks or any(not block.splitlines()[0].lstrip().startswith(b"1") for block in blocks):
        raise ValueError("could not identify complete story blocks")
    if len(blocks) < 10:
        raise ValueError("too few stories for a 10% validation partition")

    ranked = sorted(
        range(len(blocks)),
        key=lambda index: sha256(
            VALIDATION_SEED.encode("ascii") + b"\0" +
            str(task_id).encode("ascii") + b"\0" + blocks[index]
        ).digest(),
    )
    validation_count = max(1, round(len(blocks) * VALIDATION_FRACTION))
    validation_indices = set(ranked[:validation_count])
    fit = b"".join(block for index, block in enumerate(blocks) if index not in validation_indices)
    validation = b"".join(block for index, block in enumerate(blocks) if index in validation_indices)
    record = {
        "source_story_count": len(blocks),
        "fit_story_count": len(blocks) - validation_count,
        "validation_story_count": validation_count,
        "validation_fraction": VALIDATION_FRACTION,
        "validation_seed": VALIDATION_SEED,
        "split_unit": "whole story block; all questions/support lines remain together",
    }
    return fit, validation, record


def normalized_story_digests(payload: bytes) -> list[str]:
    """Hash story content without evaluator-only answer/support columns."""
    stories: list[list[str]] = []
    current: list[str] = []
    for raw in payload.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split(b"\\t")
        if len(parts) < 1:
            continue
        prefix, sentence = parts[0].split(None, 1)
        if prefix == b"1":
            if current:
                stories.append(current)
            current = []
        normalized = b" ".join(sentence.strip().split())
        current.append(normalized.decode("utf-8").casefold())
    if current:
        stories.append(current)
    return [digest("\\n".join(story).encode("utf-8")) for story in stories]


def inventory(payload: bytes) -> dict:
    lines = payload.splitlines()
    story_starts = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        prefix = stripped.split(None, 1)[0]
        if prefix == b"1":
            story_starts += 1
    return {
        "sha256": digest(payload),
        "size_bytes": len(payload),
        "line_count": len(lines),
        "story_count_by_line_reset": story_starts,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/babi-v1.2"))
    parser.add_argument(
        "--manifest", type=Path,
        default=Path("docs/experiments/HLG_BABI_TASKS_3_5_STRUCTURED_CAMPAIGN_v0_1.json"),
    )
    args = parser.parse_args()

    request = Request(ARCHIVE_URL, headers={"User-Agent": "LeptographResearch-bAbI-freezer/0.2"})
    with urlopen(request, timeout=90) as response:
        archive = response.read()
    actual_digest = digest(archive)
    if len(archive) != EXPECTED_SIZE or actual_digest != EXPECTED_SHA256:
        raise SystemExit(
            "Official bAbI v1.2 archive identity mismatch: "
            f"size={len(archive)} sha256={actual_digest}; "
            f"expected size={EXPECTED_SIZE} sha256={EXPECTED_SHA256}"
        )

    wanted = set(SOURCE_FILES.values())
    extracted: dict[str, bytes] = {}
    with tarfile.open(fileobj=BytesIO(archive), mode="r:gz") as tar:
        for member in tar.getmembers():
            name = PurePosixPath(member.name)
            if name.is_absolute() or ".." in name.parts:
                raise SystemExit(f"Unsafe archive member path: {member.name}")
            if member.name not in wanted:
                continue
            if not member.isfile() or member.issym() or member.islnk():
                raise SystemExit(f"Expected a regular file: {member.name}")
            if member.name in extracted:
                raise SystemExit(f"Duplicate archive member: {member.name}")
            stream = tar.extractfile(member)
            if stream is None:
                raise SystemExit(f"Cannot read archive member: {member.name}")
            extracted[member.name] = stream.read()

    missing = wanted - set(extracted)
    if missing:
        raise SystemExit(f"Archive missing required official task splits: {sorted(missing)}")

    args.output.mkdir(parents=True, exist_ok=True)
    payloads: dict[str, tuple[bytes, str]] = {}
    for key, archive_path in SOURCE_FILES.items():
        payloads[key] = (extracted[archive_path], archive_path)

    partition_records = {}
    for task_id, prefix in ((3, "task3"), (5, "task5")):
        source_key = f"{prefix}_train_source"
        fit, validation, partition = split_story_blocks(payloads[source_key][0], task_id=task_id)
        partition_records[prefix] = partition
        payloads[f"{prefix}_train"] = (fit, "derived whole-story fit partition")
        payloads[f"{prefix}_validation"] = (validation, "derived whole-story validation partition")

    independence_records = {}
    for task_id in (3, 5):
        prefix = f"task{task_id}"
        independent = normalized_story_digests(payloads[f"{prefix}_confirmatory_source"][0])
        en10k_train = normalized_story_digests(payloads[f"{prefix}_train_source"][0])
        en10k_test = normalized_story_digests(payloads[f"{prefix}_test_debug_only"][0])
        if len(independent) != len(set(independent)):
            raise SystemExit(f"Duplicate story blocks within independent Task {task_id} confirmatory source")
        overlap = set(independent) & (set(en10k_train) | set(en10k_test))
        if overlap:
            raise SystemExit(
                f"Task {task_id} en confirmatory source overlaps en-10k train/test by {len(overlap)} story blocks"
            )
        independence_records[prefix] = {
            "confirmatory_configuration": "en",
            "confirmatory_story_count": len(independent),
            "overlap_with_en10k_training_or_test": 0,
            "overlap_check": "normalized statement/question text; evaluator answer/support columns excluded",
            "confirmatory_story_digest_set_sha256": digest("\\n".join(sorted(independent)).encode("ascii")),
        }

    file_records = {}
    output_names = {
        "task3_train_source": "qa3_train_source.txt",
        "task3_train": "qa3_train.txt",
        "task3_validation": "qa3_valid.txt",
        "task3_test_debug_only": "qa3_test_debug_only.txt",
        "task3_confirmatory_source": "qa3_confirmatory_source.txt",
        "task5_train_source": "qa5_train_source.txt",
        "task5_train": "qa5_train.txt",
        "task5_validation": "qa5_valid.txt",
        "task5_test_debug_only": "qa5_test_debug_only.txt",
        "task5_confirmatory_source": "qa5_confirmatory_source.txt",
    }
    for key, (payload, source_description) in payloads.items():
        target = args.output / output_names[key]
        target.write_bytes(payload)
        file_records[key] = {
            "local_path": str(target),
            "source": source_description,
            **inventory(payload),
        }

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    benchmark = manifest["benchmark"]
    byte_freeze = benchmark["byte_freeze"]
    byte_freeze.update({
        "status": "VERIFIED",
        "archive_sha256": actual_digest,
        "archive_size_bytes": len(archive),
        "acquisition_url": ARCHIVE_URL,
        "selected_files": file_records,
        "selected_file_sha256": {key: row["sha256"] for key, row in file_records.items()},
        "derived_validation_partitions": partition_records,
    })
    manifest["status"] = "official en-10k source bytes verified; deterministic story-level validation derived"
    benchmark["configuration"] = "en-10k fit/validation; independent en confirmatory"
    benchmark["canonical_archive"] = ARCHIVE_URL
    benchmark["archive_object_commit"] = None
    benchmark["archive_object_revision"] = "official v1.2 archive mirrored by S3; immutable SHA-256 pinned"
    benchmark["acquisition_url"] = ARCHIVE_URL
    benchmark["acquisition_fallbacks"] = []
    benchmark["archive_mirror_note"] = (
        "The official v1.2 en-10k archive is used. A Hugging Face staff-hosted archive "
        "object has a distinct LFS digest but its CDN currently returns 403; its en-valid-10k "
        "convenience split is not required. The official en-10k train/test bytes are frozen "
        "directly, and validation is derived deterministically from whole training stories."
    )
    benchmark["partition_policy"] = {
        "fit": "90% of complete en-10k training story blocks, selected deterministically by SHA-256 ranking",
        "validation": "10% of complete en-10k training story blocks, selected by the frozen seed",
        "confirmatory": "Independent official en test files; exact normalized story-block overlap with en-10k train and test sources is required to be zero",
        "quarantined": "The en-10k test files were inspected only during preprocessing/debugging and are excluded from all campaign metrics and candidate selection",
        "leakage": "All lines, questions and supporting facts within one story remain in the same fit or validation partition.",
        "validation_seed": VALIDATION_SEED,
        "confirmatory_source_independence": independence_records,
    }
    for task in manifest["selected_tasks"]:
        prefix = f"qa{task['task_id']}"
        task["train"] = f"data/babi-v1.2/{prefix}_train.txt"
        task["validation"] = f"data/babi-v1.2/{prefix}_valid.txt"
        task["test"] = f"data/babi-v1.2/{prefix}_confirmatory_source.txt"
        task["quarantined_en10k_test_debug_only"] = f"data/babi-v1.2/{prefix}_test_debug_only.txt"
        task["official_training_source"] = f"data/babi-v1.2/{prefix}_train_source.txt"

    protocol = manifest.get("learning_protocol", {})
    protocol.update({
        "protocol_id": "HLG-BABI-T3-T5-LEARNING-v1.1",
        "status": "FROZEN; independent en confirmatory source identity and zero-overlap verified by this freezer",
        "supersedes": "HLG-BABI-T3-T5-LEARNING-v1.0; en-10k test was quarantined after preprocessing-only inspection",
        "data_identity": {
            **protocol.get("data_identity", {}),
            "fit_validation_configuration": "en-10k",
            "confirmatory_configuration": "en",
            "confirmatory_source_independence": independence_records,
            "quarantined_test_configuration": "en-10k",
        },
        "execution_gates": [
            "G0: verify source archive, all fit/validation hashes and independent en confirmatory hashes",
            "G0.5: require zero normalized story-block overlap between en confirmatory and en-10k train/test sources",
            "G1: source-indexed structured annotation bundle and independent audit",
            "G2: current-head full CI, H1 adapter/evidence tests and compiled-native smoke",
            "G3: fit/validation learning and ablation campaigns; freeze candidates",
            "G4: unlock independent en confirmatory test once",
            "G5: publish artifact hashes and complete evidence ledger"
        ]
    })
    manifest["learning_protocol_ref"] = "docs/experiments/HLG_BABI_TASKS_3_5_LEARNING_PROTOCOL_v1_1.md"
    args.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "archive_sha256": actual_digest,
        "confirmatory_source_independence": independence_records,
        "archive_size_bytes": len(archive),
        "acquisition_url": ARCHIVE_URL,
        "files": file_records,
        "derived_validation_partitions": partition_records,
        "manifest": str(args.manifest),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
