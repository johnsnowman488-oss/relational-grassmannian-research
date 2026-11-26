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
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ARCHIVE_URLS = (
    "https://s3.amazonaws.com/text-datasets/babi_tasks_1-20_v1-2.tar.gz",
    "https://www.thespermwhale.com/jaseweston/babi/tasks_1-20_v1-2.tar.gz",
    "https://huggingface.co/datasets/facebook/babi_qa/resolve/refs%2Fpr%2F5/data/tasks_1-20_v1-2.tar.gz",
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
    parser.add_argument("--inspect-candidates", action="store_true",
                        help="inventory candidate archive bytes without accepting or freezing them")
    parser.add_argument("--output", type=Path, default=Path("data/babi-v1.2"))
    parser.add_argument(
        "--manifest", type=Path,
        default=Path("docs/experiments/HLG_BABI_TASKS_3_5_STRUCTURED_CAMPAIGN_v0_1.json"),
    )
    args = parser.parse_args()

    archive = None
    acquisition_errors = []
    acquisition_url = None
    for url in ARCHIVE_URLS:
        try:
            request = Request(url, headers={"User-Agent": "LeptographResearch-bAbI-freezer/0.1"})
            candidate = urlopen(request, timeout=90).read()
        except (HTTPError, URLError, TimeoutError) as exc:
            acquisition_errors.append(f"{url}: {exc}")
            continue
        candidate_digest = digest(candidate)
        if len(candidate) == EXPECTED_SIZE and candidate_digest == EXPECTED_SHA256:
            archive = candidate
            acquisition_url = url
            break
        if args.inspect_candidates:
            try:
                inspected = {}
                with tarfile.open(fileobj=BytesIO(candidate), mode="r:gz") as probe:
                    for member in probe.getmembers():
                        if member.name not in set(FILES.values()):
                            continue
                        if not member.isfile() or member.issym() or member.islnk():
                            raise ValueError(f"unsafe/non-regular member: {member.name}")
                        stream = probe.extractfile(member)
                        if stream is None:
                            raise ValueError(f"cannot read member: {member.name}")
                        inspected[member.name] = inventory(stream.read())
                print(json.dumps({
                    "inspection_only": True,
                    "accepted": False,
                    "url": url,
                    "archive_size_bytes": len(candidate),
                    "archive_sha256": candidate_digest,
                    "selected_members": inspected,
                    "missing_members": sorted(set(FILES.values()) - set(inspected)),
                }, indent=2))
                return 0
            except (tarfile.TarError, OSError, ValueError) as exc:
                acquisition_errors.append(f"{url}: inspection failed: {exc}")
                continue
        acquisition_errors.append(
            f"{url}: digest mismatch size={len(candidate)} sha256={candidate_digest}"
        )
    if archive is None:
        raise SystemExit("No bAbI source matched the pinned archive identity:\\n" +
                         "\\n".join(acquisition_errors))
    actual_digest = digest(archive)

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
        "acquisition_url": acquisition_url,
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
        "acquisition_url": acquisition_url,
        "files": file_records,
        "manifest": str(args.manifest),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
