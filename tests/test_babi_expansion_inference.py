from types import SimpleNamespace

from rgm.experiments.babi_expansion_adapters import ExpansionQuery
from rgm.experiments.babi_expansion_inference import (
    ABSTAIN, predict_task11_from_learned_state,
)


class FakeEvidence:
    def __init__(self):
        self.rows = {
            "mary-event": SimpleNamespace(
                role=lambda name: (SimpleNamespace(entity_id="Mary") if name == "mention" else\n                                  SimpleNamespace(entity_id="office") if name == "location" else None)
            ),
            "pronoun-event": SimpleNamespace(
                role=lambda name: (SimpleNamespace(entity_id="she") if name == "mention" else\n                                  SimpleNamespace(entity_id="office") if name == "location" else None)
            ),
        }

    @property
    def event_ids(self):
        return tuple(self.rows)

    def recover(self, event_id, *, observation_cutoff):
        assert observation_cutoff == 9.0
        return (self.rows[event_id],)


class FakeRuntime:
    def __init__(self, architecture="HLA", *, location="location:office",
                 role_pattern=None, relation_pattern=None):
        self.adapter = SimpleNamespace(
            architecture=architecture,
            learning=SimpleNamespace(
                event_roles=SimpleNamespace(
                    predict=lambda context: role_pattern
                ),
                relations=SimpleNamespace(
                    predict=lambda context: relation_pattern
                ),
                context_transitions=SimpleNamespace(
                    predict=lambda context: location
                ),
            ),
        )
        self.evidence = FakeEvidence()


def query():
    return ExpansionQuery("q1", 11, 9, "validation#9", entity="mary")


def test_task11_inference_uses_learned_h1_state_and_source_evidence_only():
    role = SimpleNamespace(
        event_type="TASK11_MENTION_BINDING_TARGET",
        roles=(
            ("entity", "mary", "entity"),
            ("antecedent_event", "mary-event", "mention_event"),
            ("mention", "Mary", "name"),
            ("location", "kitchen", "location"),
        ),
    )
    relation = SimpleNamespace(
        relation_type="corefers_with",
        subject_type="mention_event",
        subject_id="pronoun-event",
        object_type="mention_event",
        object_id="mary-event",
    )
    runtime = FakeRuntime(role_pattern=role, relation_pattern=relation)

    prediction = predict_task11_from_learned_state(runtime, query())

    assert prediction.architecture == "HLA"
    assert prediction.answer == "office"
    assert prediction.abstained is False
    assert prediction.l0_mention_binding["entity_id"] == "mary"
    assert prediction.l1_coreference_edge["relation"] == "corefers_with"
    assert prediction.l2_entity_state["location"] == "office"
    assert prediction.witness_event_ids == ("mary-event",)
    assert prediction.forecast_values()["answer_value"] == "office"
    assert prediction.model_fingerprint


def test_task11_inference_abstains_when_model_has_no_entity_context():
    runtime = FakeRuntime(location=None)
    prediction = predict_task11_from_learned_state(runtime, query())

    assert prediction.abstained is True
    assert prediction.reason == "unseen_or_unusable_entity_context"
    assert prediction.answer is None
    assert prediction.forecast_values()["answer_value"] == ABSTAIN


def test_task11_inference_abstains_when_learned_location_has_no_source_witness():
    runtime = FakeRuntime(location="location:office")
    runtime.evidence.rows = {}
    prediction = predict_task11_from_learned_state(runtime, query())

    assert prediction.abstained is True
    assert prediction.reason == "no_source_grounded_entity_witness"
    assert prediction.answer is None


def test_task11_inference_rejects_other_tasks_and_architectures():
    import pytest

    with pytest.raises(ValueError, match="another task"):
        predict_task11_from_learned_state(
            FakeRuntime(), ExpansionQuery("q2", 14, 9, "validation#9", entity="mary")
        )
    with pytest.raises(ValueError, match="HLA or HLB"):
        predict_task11_from_learned_state(FakeRuntime("OTHER"), query())



def test_task11_forecasts_are_issued_before_official_answer_scoring():
    from rgm.experiments.babi_expansion_runtime import ExpansionForecasts
    from rgm.experiments.babi_expansion_adapters import GoldLabel
    from rgm.experiments.babi_expansion_inference import issue_task11_model_forecasts

    role = SimpleNamespace(
        event_type="TASK11_MENTION_BINDING_TARGET",
        roles=(("entity", "mary", "entity"),
               ("antecedent_event", "mary-event", "mention_event")),
    )
    runtime = FakeRuntime(role_pattern=role)
    forecasts = ExpansionForecasts(11)
    prediction = issue_task11_model_forecasts(
        runtime, query(), forecasts,
        issued_tick=7, issued_at=7.0, evidence_cutoff=7.0,
    )
    assert prediction.answer == "office"
    scored = forecasts.score_query(
        query(), GoldLabel("q1", "office", (1,), "validation#9"),
        evaluated_tick=8, observed_at=9.0,
    )
    assert scored["task11.answer.location_answer"]["value"] == 1.0
