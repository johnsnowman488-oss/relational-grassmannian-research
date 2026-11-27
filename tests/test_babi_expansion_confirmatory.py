import json

from rgm.experiments.babi_expansion_confirmatory import generate, verify


def test_confirmatory_challenge_is_deterministic_and_label_separated(tmp_path):
    output = tmp_path / "confirmatory"
    manifest = generate(output)
    result = verify(output)
    assert result["status"] == "PASS"
    assert result["task_count"] == 3
    assert result["stories_per_task"] == 384
    for task_id in (11, 14, 19):
        record = manifest["files"][str(task_id)]
        inputs = [json.loads(line) for line in (output / record["inputs"]["path"]).read_text().splitlines()]
        labels = [json.loads(line) for line in (output / record["evaluator_labels"]["path"]).read_text().splitlines()]
        assert len(inputs) == len(labels) == 384
        assert all("gold_answer" not in row and "support_event_ids" not in row for row in inputs)
        assert {row["query"]["query_id"] for row in inputs} == {row["query_id"] for row in labels}
    second = tmp_path / "confirmatory-repeat"
    repeated = generate(second)
    assert manifest["manifest_sha256"] == repeated["manifest_sha256"]
    for task_id in (11, 14, 19):
        assert manifest["files"][str(task_id)] == repeated["files"][str(task_id)]
