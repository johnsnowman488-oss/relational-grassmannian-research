#!/usr/bin/env python3
"""Acquire and audit bAbI v1.2.0 en-10k members for Tasks 11, 14 and 19.

The experiment consumes six selected source members, not the complete archive.
This downloader obtains a fresh, commit-pinned external copy of those exact
members from an independent GitHub mirror and verifies each against its Git
blob identity before auditing. It is independent of the frozen Task 3/5 path.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha1, sha256
import json
from pathlib import Path, PurePosixPath
import re
from urllib.request import Request, urlopen

MIRROR_REPOSITORY = "raviraju/NLP_QA_Project"
MIRROR_COMMIT = "0051751275841561267b1c6f5d9116b985521df1"
MIRROR_ROOT = (
    "https://raw.githubusercontent.com/raviraju/NLP_QA_Project/"
    + MIRROR_COMMIT
    + "/tasks_1-20_v1-2/"
)
CONFIGURATION = "en-10k"
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
SUPPORT_RE = re.compile(r"\d+(?:\s+\d+)*")
LINE_RE = re.compile(r"^(\d+)\s+(.*)$")
DIRECTIONS = {"north", "south", "east", "west"}


class SourceAuditError(ValueError):
    """Raised when a source file violates the frozen bAbI source contract."""


def digest(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def git_blob_sha1(payload: bytes) -> str:
    header = b"blob " + str(len(payload)).encode("ascii") + b"\0"
    return sha1(header + payload).hexdigest()


def download(url: str) -> bytes:
    request = Request(
        url,
        headers={"User-Agent": "LeptographResearch-bAbI-SourceFreeze/1.1"},
    )
    with urlopen(request, timeout=120) as response:
        return response.read()


def audit_member(payload: bytes, *, task_id: int, member_name: str) -> dict:
    """Parse one member and validate story-local support witnesses."""
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SourceAuditError(f"{member_name}: source is not UTF-8") from exc

    story_count = statement_count = question_count = record_count = 0
    story_record_counts: list[int] = []
    answer_counts: Counter[str] = Counter()
    support_count_counts: Counter[int] = Counter()
    support_reference_count = 0
    max_support_id = 0
    current_story_records = 0
    previous_line_number = 0
    statement_ids: set[int] = set()

    def close_story() -> None:
        nonlocal current_story_records
        if current_story_records:
            story_record_counts.append(current_story_records)
            current_story_records = 0

    for physical_line, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.rstrip("\r")
        if not line:
            continue
        record_count += 1
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
        current_story_records += 1

        if "\t" not in body:
            if not body.strip():
                raise SourceAuditError(f"{member_name}:{physical_line}: empty statement")
            statement_count += 1
            statement_ids.add(line_number)
            continue

        fields = body.split("\t")
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
        invalid = [
            sid for sid in supports
            if sid >= line_number or sid not in statement_ids
        ]
        if invalid:
            raise SourceAuditError(
                f"{member_name}:{physical_line}: support IDs are not prior "
                f"statement lines in this story: {invalid}"
            )
        if task_id == 19:
            direction_tokens = answer.lower().split()
            if (
                not direction_tokens
                or any(token not in DIRECTIONS for token in direction_tokens)
            ):
                raise SourceAuditError(
                    f"{member_name}:{physical_line}: Task 19 answer is not an "
                    "ordered cardinal-direction sequence"
                )

        question_count += 1
        answer_counts[answer] += 1
        support_count_counts[len(supports)] += 1
        support_reference_count += len(supports)
        max_support_id = max(max_support_id, max(supports, default=0))

    close_story()
    if not story_count or not question_count:
        raise SourceAuditError(f"{member_name}: no complete stories/questions found")

    return {
        "member_name": member_name,
        "size_bytes": len(payload),
        "sha256": digest(payload),
        "git_blob_sha1": git_blob_sha1(payload),
        "physical_line_count": len(text.splitlines()),
        "nonempty_record_count": record_count,
        "story_count": story_count,
        "statement_count": statement_count,
        "question_count": question_count,
        "mean_records_per_story": round(record_count / story_count, 6),
        "support_reference_count": support_reference_count,
        "supporting_fact_count_distribution": {
            str(k): v for k, v in sorted(support_count_counts.items())
        },
        "max_support_line_id": max_support_id,
        "support_references_valid_story_local_prior_statements": True,
        "answer_distribution": dict(sorted(answer_counts.items())),
        "answer_unique_count": len(answer_counts),
        "story_record_count_min": min(story_record_counts),
        "story_record_count_max": max(story_record_counts),
        "story_record_count_mean": round(
            sum(story_record_counts) / len(story_record_counts), 6
        ),
    }


def freeze(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)

    # Acquire the dataset release README and license from the same immutable
    # repository revision, so provenance metadata travels with the byte copy.
    support_files = {}
    for filename in ("README.txt", "LICENSE.txt"):
        payload = download(MIRROR_ROOT + filename)
        (output / filename).write_bytes(payload)
        support_files[filename] = {
            "size_bytes": len(payload),
            "sha256": digest(payload),
            "git_blob_sha1": git_blob_sha1(payload),
        }

    member_records = {}
    for task_id, splits in SOURCE_FILES.items():
        for split, filename in splits.items():
            relative_path = CONFIGURATION + "/" + filename
            payload = download(MIRROR_ROOT + relative_path)
            git_sha = git_blob_sha1(payload)
            if len(payload) != MIRROR_BLOB_SIZE[filename]:
                raise SourceAuditError(
                    f"{filename}: downloaded byte size differs from pinned source"
                )
            if git_sha != MIRROR_BLOB_SHA1[filename]:
                raise SourceAuditError(
                    f"{filename}: downloaded content differs from the "
                    f"commit-pinned Git blob (actual {git_sha})"
                )
            audit = audit_member(payload, task_id=task_id, member_name=filename)
            target = output / filename
            target.write_bytes(payload)
            audit.update({
                "task_id": task_id,
                "split": split,
                "archive_path": "tasks_1-20_v1-2/en-10k/" + filename,
                "local_path": str(target),
                "download_url": MIRROR_ROOT + relative_path,
                "independent_source": {
                    "repository": MIRROR_REPOSITORY,
                    "commit": MIRROR_COMMIT,
                    "git_blob_sha1": MIRROR_BLOB_SHA1[filename],
                    "size_bytes": MIRROR_BLOB_SIZE[filename],
                },
            })
            member_records[f"task{task_id}_{split}"] = audit

    report = {
        "schema": "HLG-BABI-EXPANSION-SOURCE-FREEZE-v1.0",
        "status": "VERIFIED",
        "verified_utc": datetime.now(timezone.utc).isoformat(),
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
                "The commit-pinned tasks_1-20_v1-2/LICENSE.txt identifies "
                "Facebook, Inc. and CC BY 3.0 Unported."
            ),
            "release_readme": "README.txt",
            "release_readme_evidence": (
                "The v1.2 README identifies en-10k as the 10,000-training-example "
                "configuration and documents the numbered-line/tab-separated format."
            ),
            "paper": (
                "Towards AI-Complete Question Answering: A Set of Prerequisite Toy Tasks"
            ),
            "paper_url": "https://arxiv.org/abs/1502.05698",
        },
        "acquisition": {
            "type": "fresh external per-member copy",
            "repository": MIRROR_REPOSITORY,
            "commit": MIRROR_COMMIT,
            "root_url": MIRROR_ROOT,
            "archive_member_prefix": "tasks_1-20_v1-2/en-10k/",
            "archive_tarball_downloaded": False,
            "archive_note": (
                "The Hugging Face dataset repository's documented tarball LFS "
                "pointer returned HTTP 404 at the attempted resolve endpoint. "
                "Instead, the six selected source members were downloaded "
                "individually from an immutable external Git commit and verified "
                "against that commit's Git blob identities. No archive-byte "
                "verification is claimed."
            ),
            "support_files": support_files,
        },
        "independent_source": {
            "repository": MIRROR_REPOSITORY,
            "commit": MIRROR_COMMIT,
            "purpose": "Fresh external copy and immutable per-member byte identity",
            "note": (
                "Each downloaded member is verified by byte length and Git blob "
                "SHA-1, then assigned a SHA-256 for the experiment's primary manifest."
            ),
        },
        "format_contract": {
            "encoding": "UTF-8",
            "record": "ID text",
            "question": "ID question<TAB>answer<TAB>supporting-fact IDs",
            "story_boundary": "A reset of the story-local ID to 1 starts a new story",
            "line_ids": "Consecutive within each story, including question records",
            "support_scope": "Support IDs resolve to earlier statement lines within the same story",
            "official_validation_split_for_en_10k": False,
            "validation_policy": (
                "Derive task-specific validation from each training file using a "
                "frozen deterministic whole-story split; keep official test members "
                "sealed from fitting, adaptation, validation and candidate selection."
            ),
            "test_policy": "Quarantined; retain only as source bytes and audited metadata.",
        },
        "members": member_records,
        "acceptance": {
            "six_selected_members_downloaded_from_external_commit": True,
            "all_six_members_match_pinned_git_blob_and_size": True,
            "all_six_members_have_sha256": True,
            "all_members_are_utf8_and_parse": True,
            "story_resets_and_line_sequences_valid": True,
            "all_support_ids_resolve_to_same_story_prior_statements": True,
            "task19_answers_are_ordered_cardinal_direction_sequences": True,
            "official_test_files_quarantined": True,
            "archive_tarball_downloaded_and_verified": False,
        },
    }
    report_path = output / "source-audit.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report


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
