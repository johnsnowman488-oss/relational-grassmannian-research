import json

from rgm.experiments.babi_expansion_adapters import (
    GoldLabel, task11_confirmatory_input_to_story,
)
from rgm.experiments.babi_expansion_baselines import evaluate_baselines
from rgm.experiments.babi_expansion_confirmatory import generate, verify
from rgm.experiments.babi_expansion_runtime import (
    ExpansionForecasts, task11_supervision_from_evaluator_label, to_nary_event,
)


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
        if task_id == 11:
            assert all("events" in row and "observations" not in row for row in inputs)
            assert all("mention_binding_edges" not in row for row in inputs)
            assert all("task11_supervision" in row for row in labels)

    second = tmp_path / "confirmatory-repeat"
    repeated = generate(second)
    assert manifest["manifest_sha256"] == repeated["manifest_sha256"]
    for task_id in (11, 14, 19):
        assert manifest["files"][str(task_id)] == repeated["files"][str(task_id)]


def test_task11_confirmatory_input_matches_runtime_and_gold_edges_stay_separate(tmp_path):
    output = tmp_path / "confirmatory"
    generate(output)
    inputs = [json.loads(line) for line in
              (output / "task11-inputs.jsonl").read_text().splitlines()]
    labels = [json.loads(line) for line in
              (output / "task11-evaluator-labels.jsonl").read_text().splitlines()]
    stories = [task11_confirmatory_input_to_story(row) for row in inputs]

    for story in stories:
        anchors = {event.surface_mention: event.grammatical_gender
                   for event in story.events if not event.is_pronoun}
        assert len(anchors) == 2
        assert set(anchors.values()) == {"female", "male"}
        for event in story.events:
            if event.is_pronoun:
                candidates = [name for name, gender in anchors.items()
                              if gender == event.grammatical_gender]
                assert len(candidates) == 1
                assert not hasattr(event, "antecedent_event_id")
                mapped = to_nary_event(story, event)
                assert any(participant.role == "grammatical_gender"
                           for participant in mapped.participants)
                assert not any(participant.role in {"entity", "antecedent"}
                               for participant in mapped.participants)

    gold_labels = [
        GoldLabel(row["query_id"], row["gold_answer"], (), row["source_ref"])
        for row in labels
    ]
    scorecard = evaluate_baselines(
        stories, gold_labels, evaluate_labels=True, target_labels=labels,
    )
    nearest = scorecard["task_results"]["11"]["nearest-compatible-antecedent"]
    assert nearest["answer_exact_match"] == 1.0
    assert nearest["target_metrics"]["status"] == "PASS_METRICS_AVAILABLE"
    assert nearest["target_metrics"]["scored_queries"] == 384
    assert nearest["target_metrics"]["precision"] == 1.0
    assert nearest["target_metrics"]["recall"] == 1.0
    assert nearest["target_metrics"]["f1"] == 1.0
    assert nearest["target_metrics"]["target_exact_match"] == 1.0


def test_task11_l0_l1_l2_supervision_is_scored_only_after_forecast(tmp_path):
    output = tmp_path / "confirmatory"
    generate(output)
    input_row = json.loads((output / "task11-inputs.jsonl").read_text().splitlines()[0])
    label_row = json.loads((output / "task11-evaluator-labels.jsonl").read_text().splitlines()[0])
    story = task11_confirmatory_input_to_story(input_row)
    query = story.queries[0]
    bundle = task11_supervision_from_evaluator_label(query, label_row)

    forecasts = ExpansionForecasts(11)
    forecasts.issue_query_forecasts(
        query, issued_tick=query.observed_at - 2,
        issued_at=float(query.observed_at - 2),
        evidence_cutoff=float(query.observed_at - 1),
        l0_value=bundle.l0_mention_binding,
        l1_value=bundle.l1_coreference_edge,
        l2_value=bundle.l2_entity_state,
        answer_value=label_row["gold_answer"],
        model_fingerprint="test-model",
    )
    scored = forecasts.score_task11_supervision(
        query, bundle, evaluated_tick=query.observed_at + 1,
        observed_at=float(query.observed_at + 1),
    )
    assert set(scored) == {"L0", "L1", "L2"}
    assert all(row["target_source_id"] == label_row["source_ref"]
               for row in scored.values())
