#!/usr/bin/env python3
"""Acquire and byte-freeze the pinned bAbI v1.2 Task 3/5 source splits.

This utility only acquires, verifies and inventories source files. It does not
parse story text, annotate events, or run a benchmark.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
import tarfile
from urllib.request import urlopen


ARCHIVE_URL = (
    "https://huggingface.co/datasets/facebook/babi_qa/resolve/refs%2Fpr%2F5/"
    "data/tasks_1-20_v1-2.tar.gz"
)
EXPECTED_SHA256 = "0364ebde659f14d11bc21744516c5ec49d3d06cb692733f66680771244998898"
EXPECTED_SIZE = 15_719_851
PREFIX = "tasks_1-20_v1-2/en-valid-10k/"
FILES = {
    "task3_train": PREFIX + "qa3_train.txt",
    "task3_validation": PREFIX + "qa3_valid.txt",
    "task3_test": PREFIX + "qa3_test.txt",
    "task5_train": PREFIX + "qa5_train.txt",
    "task5_validation": PREFIX + "qa5_valid.txt",
    "task5_test": PREFIX + "qa5_test.txt",
}


def digest(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def inventory(payload: bytes) -> dict:
    lines = payload.splitlines()
    story_starts = 0
    for line in lines:
        if not line:
            continue
        prefix = line.split(None, 1)[0]
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

    archive = urlopen(ARCHIVE_URL, timeout=60).read()
    actual_digest = digest(archive)
    if len(archive) != EXPECTED_SIZE or actual_digest != EXPECTED_SHA256:
        raise SystemExit(
            "Pinned bAbI archive mismatch: "
            f"size={len(archive)} sha256={actual_digest}"
        )

    wanted = set(FILES.values())
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
            stream = tar.extractfile(member)
            if stream is None:
                raise SystemExit(f"Cannot read archive member: {member.name}")
            extracted[member.name] = stream.read()

    missing = wanted - set(extracted)
    if missing:
        raise SystemExit(f"Archive missing required task splits: {sorted(missing)}")

    args.output.mkdir(parents=True, exist_ok=True)
    file_records = {}
    for key, archive_path in FILES.items():
        payload = extracted[archive_path]
        target = args.output / Path(archive_path).name
        target.write_bytes(payload)
        file_records[key] = {
            "archive_path": archive_path,
            "local_path": str(target),
            **inventory(payload),
        }

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    byte_freeze = manifest["benchmark"]["byte_freeze"]
    byte_freeze.update({
        "status": "VERIFIED",
        "archive_sha256": actual_digest,
        "archive_size_bytes": len(archive),
        "selected_file_sha256": {
            key: row["sha256"] for key, row in file_records.items()
        },
        "selected_files": file_records,
    })
    manifest["status"] = "source-bytes-verified; structured-event stage ready"
    args.manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "archive_sha256": actual_digest,
        "archive_size_bytes": len(archive),
        "files": file_records,
        "manifest": str(args.manifest),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
