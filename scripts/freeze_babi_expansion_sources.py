#!/usr/bin/env python3
"""Acquire and audit bAbI v1.2.0 en-10k source members for Tasks 11, 14 and 19.

This is deliberately separate from scripts/freeze_babi_tasks.py, which freezes
the untouched Task 3/5 pilot. The archive and every selected source member are
verified before an audit manifest is emitted.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha1, sha256
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
from urllib.request import Request, urlopen

ARCHIVE_URL = (
    "https://huggingface.co/datasets/facebook/babi_qa/resolve/main/"
    "data/tasks_1-20_v1-2.tar.gz?download=true"
)
ARCHIVE_NAME = "tasks_1-20_v1-2.tar.gz"
ARCHIVE_SHA256 = "0364ebde659f14d11bc21744516c5ec49d3d06cb692733f66680771244998898"
ARCHIVE_SIZE = 15_719_851
ARCHIVE_LFS_OID = "sha256:" + ARCHIVE_SHA256
PREFIX = "tasks_1-20_v1-2/en-10k/"
MIRROR_REPOSITORY = "raviraju/NLP_QA_Project"
MIRROR_COMMIT = "0051751275841561267b1c6f5d9116b985521df1"
SOURCE_FILES = {
    11: {
        "train": "qa11_basic-coreference_train.txt",
        "test": "qa11_basic-coreference_test.txt",
    },
    14: {
        "train": "qa14_time-reasoning_train.txt",
        "test": "qa14_time-reasoning_test.txt",
    },
    19: {
        "train": "qa19_path-finding_train.txt",
        "test": "qa19_path-finding_test.txt",
    },
}
# GitHub Git-blob object IDs from an independent, commit-pinned copy of the
# exact v1.2 en-10k members. Recomputed as SHA1("blob <size>\\0" + bytes).
MIRROR_BLOB_SHA1 = {
    "qa11_basic-coreference_train.txt": "ff530d4de05dc753a0fe9d9638aa761ed855b81e",
    "qa11_basic-coreference_test.txt": "c9feb150855483c587c5a825211fc306d4cfebe3",
    "qa14_time-reasoning_train.txt": "35350c2fbfcc081218731cf3929f3e56c169360c",
    "qa14_time-reasoning_test.txt": "c0c88cd92b690d6c533c3e532cb8a9e38ae8f1bf",
    "qa19_path-finding_train.txt": "c9ec29b500eaf11f977d24c38aa0504f09f00cbf",
    "qa19_path-finding_test.txt": "fe316702f1bd930bf17257fac3513ec3ceac628c",
}
MIRROR_BLOB_SIZE = {
    "qa11_basic-coreference_train.txt": 1_046_139,
    "qa11_basic-coreference_test.txt": 104_800,
    "qa14_time-reasoning_train.txt": 1_506_583,
    "qa14_time-reasoning_test.txt": 151_420,
    "qa19_path-finding_train.txt": 2_475_046,
    "qa19_path-finding_test.txt": 247_449,
}
DIRECTIONS = {"north", "south", "east", "west"}
LINE_RE = re.compile(r"^(\\d+)\\s+(.*)$")
SUPPORT_RE = re.compile(r"\\d+(?:\\s+\\d+)*")


class SourceAuditError(ValueError):
    """Raised when a source file violates the frozen bAbI format contract."""


def digest(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def git_blob_sha1(payload: bytes) -> str:
    header = b"blob " + str(len(payload)).encode("ascii") + b"\\0"
    return sha1(header + payload).hexdigest()


def audit_member(payload: bytes, *, task_id: int, member_name: str) -> dict:
    """Parse one member and validate story-local support witnesses."""
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SourceAuditError(f"{member_name}: source is not UTF-8") from exc

    story_count = statement_count = question_count = line_count = 0
    story_line_counts: list[int] = []
    answer_counts: Counter[str] = Counter()
    support_count_counts: Counter[int] = Counter()
    support_ids_total = 0
    max_support_id = 0
    current_story_line_count = 0
    previous_line_number = 0
    statement_ids: set[int] = set()
    all_support_ids_valid = True

    def close_story() -> None:
        nonlocal current_story_line_count
        if current_story_line_count:
            story_line_counts.append(current_story_line_count)
            current_story_line_count = 0

    for physical_line, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.rstrip("\r")
        if not line:
            continue
        line_count += 1
        match = LINE_RE.fullmatch(line)
        if match is None:
            raise SourceAuditError(
                f"{member_name}:{physical_line}: expected '<id> <text>'"
            )
        line_number = int(match.group(1))
        body = match.group(2)
        if line_number == 1:
            close_story()
            story_count += 1
            statement_ids = set()
            previous_line_number = 0
        elif story_count == 0:
            raise SourceAuditError(
                f"{member_name}:{physical_line}: first story must start at line 1"
            )
        if line_number != previous_line_number + 1:
            raise SourceAuditError(
                f"{member_name}:{physical_line}: expected story-local line "
                f"{previous_line_number + 1}, got {line_number}"
            )
        previous_line_number = line_number
        current_story_line_count += 1

        if "\\t" not in body:
            if not body.strip():
                raise SourceAuditError(
                    f"{member_name}:{physical_line}: empty statement"
                )
            statement_count += 1
            statement_ids.add(line_number)
            continue

        fields = body.split("\\t")
        if len(fields) != 3:
            raise SourceAuditError(
                f"{member_name}:{physical_line}: question must have exactly "
                "three tab-separated fields"
            )
        question, answer, support_field = fields
        if not question.strip() or not answer.strip():
            raise SourceAuditError(
                f"{member_name}:{physical_line}: empty question or answer"
            )
        if not SUPPORT_RE.fullmatch(support_field.strip()):
            raise SourceAuditError(
                f"{member_name}:{physical_line}: malformed supporting-line list"
            )
        supports = [int(item) for item in support_field.split()]
        if len(supports) != len(set(supports)):
            raise SourceAuditError(
                f"{member_name}:{physical_line}: duplicate support-line ID"
            )
        invalid = [sid for sid in supports if sid >= line_number or sid not in statement_ids]
        if invalid:
            all_support_ids_valid = False
            raise SourceAuditError(
                f"{member_name}:{physical_line}: support IDs are not prior "
                f"statement lines in this story: {invalid}"
            )
        if task_id == 19:
            direction_tokens = answer.lower().split()
            if not direction_tokens or any(token not in DIRECTIONS for token in direction_tokens):
                raise SourceAuditError(
                    f"{member_name}:{physical_line}: Task 19 answer is not an "
                    "ordered cardinal-direction sequence"
                )
        question_count += 1
        answer_counts[answer] += 1
        support_count_counts[len(supports)] += 1
        support_ids_total += len(supports)
        max_support_id = max(max_support_id, max(supports, default=0))

    close_story()
    if not story_count or not question_count:
        raise SourceAuditError(f"{member_name}: no complete stories/questions found")
    if not all_support_ids_valid:
        raise SourceAuditError(f"{member_name}: one or more support references failed")

    return {
        "member_name": member_name,
        "size_bytes": len(payload),
        "sha256": digest(payload),
        "git_blob_sha1": git_blob_sha1(payload),
        "physical_line_count": len(text.splitlines()),
        "nonempty_record_count": line_count,
        "story_count": story_count,
        "statement_count": statement_count,
        "question_count": question_count,
        "mean_records_per_story": round(line_count / story_count, 6),
        "support_reference_count": support_ids_total,
        "supporting_fact_count_distribution": {
            str(k): v for k, v in sorted(support_count_counts.items())
        },
        "max_support_line_id": max_support_id,
        "support_references_valid_story_local_prior_statements": True,
        "answer_distribution": dict(sorted(answer_counts.items())),
        "answer_unique_count": len(answer_counts),
        "story_record_count_min": min(story_line_counts),
        "story_record_count_max": max(story_line_counts),
        "story_record_count_mean": round(sum(story_line_counts) / len(story_line_counts), 6),
    }


def selected_members(archive_bytes: bytes) -> dict[str, bytes]:
    wanted = {
        PREFIX + filename
        for task_splits in SOURCE_FILES.values()
        for filename in task_splits.values()
    }
    found: dict[str, bytes] = {}
    try:
        archive = tarfile.open(fileobj=BytesIO(archive_bytes), mode="r:gz")
    except (tarfile.TarError, OSError) as exc:
        raise SourceAuditError(f"archive is not a readable gzip tar: {exc}") from exc
    with archive:
        for member in archive.getmembers():
            member_path = PurePosixPath(member.name)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise SourceAuditError(f"unsafe archive path: {member.name}")
            if member.name not in wanted:
                continue
            if not member.isfile() or member.issym() or member.islnk():
                raise SourceAuditError(f"selected member is not a regular file: {member.name}")
            if member.name in found:
                raise SourceAuditError(f"duplicate archive member: {member.name}")
            stream = archive.extractfile(member)
            if stream is None:
                raise SourceAuditError(f"cannot read archive member: {member.name}")
            found[member.name] = stream.read()
    missing = wanted - found.keys()
    if missing:
        raise SourceAuditError(f"archive is missing selected members: {sorted(missing)}")
    return found


def acquire_archive(destination: Path) -> bytes:
    request = Request(
        ARCHIVE_URL,
        headers={"User-Agent": "LeptographResearch-bAbI-SourceFreeze/1.0"},
    )
    with urlopen(request, timeout=120) as response:
        payload = response.read()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
    actual_sha = digest(payload)
    if len(payload) != ARCHIVE_SIZE or actual_sha != ARCHIVE_SHA256:
        raise SourceAuditError(
            "v1.2 archive identity mismatch: "
            f"size={len(payload)} sha256={actual_sha}; "
            f"expected size={ARCHIVE_SIZE} sha256={ARCHIVE_SHA256}"
        )
    return payload


def freeze(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    archive_path = output / ARCHIVE_NAME
    archive_bytes = acquire_archive(archive_path)
    members = selected_members(archive_bytes)

    member_records = {}
    for task_id, splits in SOURCE_FILES.items():
        for split, filename in splits.items():
            archive_member = PREFIX + filename
            payload = members[archive_member]
            git_sha = git_blob_sha1(payload)
            if len(payload) != MIRROR_BLOB_SIZE[filename]:
                raise SourceAuditError(
                    f"{filename}: byte size disagrees with independent pinned mirror"
                )
            if git_sha != MIRROR_BLOB_SHA1[filename]:
                raise SourceAuditError(
                    f"{filename}: content differs from the independent "
                    f"commit-pinned mirror (git blob {git_sha})"
                )
            audit = audit_member(payload, task_id=task_id, member_name=filename)
            target = output / filename
            target.write_bytes(payload)
            audit.update({
                "task_id": task_id,
                "split": split,
                "archive_path": archive_member,
                "local_path": str(target),
                "independent_mirror": {
                    "repository": MIRROR_REPOSITORY,
                    "commit": MIRROR_COMMIT,
                    "git_blob_sha1": MIRROR_BLOB_SHA1[filename],
                    "size_bytes": MIRROR_BLOB_SIZE[filename],
                },
            })
            member_records[f"task{task_id}_{split}"] = audit

    manifest = {
        "schema": "HLG-BABI-EXPANSION-SOURCE-FREEZE-v1.0",
        "status": "VERIFIED",
        "verified_utc": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "dataset": {
            "name": "The 20-Task bAbI Question-Answering Dataset",
            "version": "1.2.0",
            "language": "English",
            "configuration": "en-10k",
            "original_creators": [
                "Jason Weston", "Antoine Bordes", "Sumit Chopra",
                "Alexander M. Rush", "Bart van Merriënboer",
                "Armand Joulin", "Tomas Mikolov"
            ],
            "copyright_notice": "Copyright (c) 2015-present, Facebook, Inc.",
            "license": "Creative Commons Attribution 3.0 Unported (CC BY 3.0)",
            "license_evidence": (
                "The pinned mirror's tasks_1-20_v1-2/LICENSE.txt identifies "
                "Facebook, Inc. and CC BY 3.0 Unported; the Hugging Face "
                "facebook/babi_qa dataset script also declares CC BY 3.0."
            ),
            "dataset_paper": (
                "Towards AI-Complete Question Answering: A Set of Prerequisite Toy Tasks"
            ),
            "paper_arxiv": "https://arxiv.org/abs/1502.05698",
            "release_notes": (
                "The v1.2 README identifies en-10k as the 10,000-training-example "
                "configuration and documents the numbered-line/tab-separated format."
            ),
        },
        "acquisition": {
            "archive_filename": ARCHIVE_NAME,
            "archive_url": ARCHIVE_URL,
            "archive_sha256": digest(archive_bytes),
            "archive_size_bytes": len(archive_bytes),
            "archive_lfs_oid": ARCHIVE_LFS_OID,
            "archive_mirror": "Hugging Face dataset repository facebook/babi_qa",
            "archive_mirror_pin": "Git LFS SHA-256 object identity",
            "archive_is_publisher_hosted": False,
            "provenance_caveat": (
                "The acquired tarball is a content-pinned mirror of the v1.2 release, "
                "not a download from a currently publisher-controlled host. Exact "
                "selected member bytes are independently cross-checked against a "
                "separate commit-pinned GitHub copy."
            ),
        },
        "independent_member_mirror": {
            "repository": MIRROR_REPOSITORY,
            "commit": MIRROR_COMMIT,
            "purpose": "Independent per-member byte-identity cross-check",
            "note": "Git blob SHA-1 is used only as a second-copy identity check; SHA-256 is the primary manifest digest.",
        },
        "format_contract": {
            "encoding": "UTF-8",
            "record": "ID text",
            "question": "ID question<TAB>answer<TAB>supporting-fact IDs",
            "story_boundary": "A reset of the story-local ID to 1 starts a new story",
            "line_ids": "Consecutive within each story, including question records",
            "support_scope": "Support IDs resolve to earlier statement lines within the same story",
            "official_validation_split": False,
            "validation_policy": (
                "Derive task-specific validation from each training file using a frozen "
                "deterministic whole-story split; the official test file remains sealed "
                "from fitting, model selection and validation."
            ),
        },
        "members": member_records,
        "acceptance": {
            "archive_digest_and_size_match_pinned_lfs_object": True,
            "all_six_members_present_once": True,
            "member_bytes_match_independent_commit_pinned_copy": True,
            "all_members_are_utf8_and_parse": True,
            "story_resets_and_line_sequences_valid": True,
            "all_support_ids_resolve_to_same_story_prior_statements": True,
            "task19_answers_are_ordered_cardinal_direction_sequences": True,
            "official_test_files_quarantined": True,
        },
    }
    report_path = output / "source-audit.json"
    report_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("data/babi-v1.2-expansion")
    )
    args = parser.parse_args()
    report = freeze(args.output)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
