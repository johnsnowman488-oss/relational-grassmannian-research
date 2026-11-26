import hashlib

import pytest

from rgm.leptograph.m4.evidence import (
    DerivedEvidence, EvidenceStore, EvidenceSummary, NaryEvent, Participant,
)


def event(event_id, *, value="office", event_time=1.0, observed_at=1.0,
          payload=b"payload", revision_of=None):
    return NaryEvent(
        event_id=event_id,
        event_type="gave",
        participants=(
            Participant("giver", "mary", "person"),
            Participant("object", "cake", "object"),
            Participant("recipient", value, "person"),
        ),
        event_time=event_time,
        observed_at=observed_at,
        provenance="official-babi-fixture",
        source_locator=f"fixture://{event_id}",
        payload_digest=hashlib.sha256(payload).hexdigest(),
        revision_of=revision_of,
    )


def test_nary_event_keeps_all_roles_under_one_identity():
    record = event("e1", value="fred")
    assert record.role("giver").entity_id == "mary"
    assert record.role("object").entity_id == "cake"
    assert record.role("recipient").entity_id == "fred"
    assert record.event_id == "e1"
    with pytest.raises(ValueError, match="unique"):
        NaryEvent(
            "bad", "gave",
            (Participant("person", "mary", "person"),
             Participant("person", "fred", "person")),
            1.0, 1.0, "source", "loc", hashlib.sha256(b"x").hexdigest(),
        )


def test_late_observation_is_preserved_but_hidden_before_observed_at_cutoff():
    store = EvidenceStore()
    late = event("late", event_time=2.0, observed_at=5.0)
    assert store.append(late) == "STORED"
    with pytest.raises(PermissionError):
        store.get_event("late", observation_cutoff=4.0)
    assert store.get_event("late", observation_cutoff=5.0) == late


def test_contradictions_are_retained_and_reported_not_overwritten():
    store = EvidenceStore()
    assert store.append(event("claim-a", value="fred")) == "STORED"
    assert store.append(event("claim-b", value="bill")) == "STORED"
    assert store.contradictions(
        event_type="gave", key_roles=("giver", "object"),
        value_role="recipient", observation_cutoff=2.0,
    ) == (("claim-a", "claim-b"),)
    assert store.count == 2


def test_summary_and_derived_evidence_recover_exact_source_witnesses():
    store = EvidenceStore()
    first, second = event("e1"), event("e2", event_time=2.0, observed_at=2.0)
    store.append(first)
    store.append(second)
    derivation = DerivedEvidence(
        "d1", 1, "rule-sha256", ("e1", "e2"), "two-event conclusion", 3.0
    )
    store.append_derivation(derivation)
    import json
    # Summary digest commits to its direct derivation reference. Recovery then
    # resolves that derivation to the exact original event records.
    derivation_digest = hashlib.sha256(json.dumps(
        [derivation.__dict__], sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False
    ).encode()).hexdigest()
    summary = EvidenceSummary("s1", 2, "compressed conclusion", ("d1",), derivation_digest, 4.0)
    store.append_summary(summary)
    restored = EvidenceStore.from_snapshot(store.snapshot())
    recovered = restored.recover("s1", observation_cutoff=4.0)
    chain = restored.recover_chain("s1", observation_cutoff=4.0)
    assert {item.event_id for item in recovered} == {"e1", "e2"}
    assert [item.summary_id for item in chain["summaries"]] == ["s1"]
    assert [item.derivation_id for item in chain["derivations"]] == ["d1"]
    assert {item.role("recipient").entity_id for item in recovered} == {"office"}


def test_missing_witness_and_bad_provenance_fail_closed():
    store = EvidenceStore()
    with pytest.raises(KeyError, match="missing"):
        store.append_derivation(DerivedEvidence("d", 1, "rule", ("absent",), "x", 2.0))
    record = event("e1", payload=b"expected")
    store.append(record)
    assert store.verify_provenance("e1", lambda _: b"expected")
    assert not store.verify_provenance("e1", lambda _: b"tampered")


def test_capacity_exhaustion_abstains_without_evicting_evidence():
    store = EvidenceStore(capacity=1)
    assert store.append(event("e1")) == "STORED"
    assert store.append(event("e2")) == "ABSTAIN_CAPACITY"
    assert store.event_ids == ("e1",)


def test_snapshot_roundtrip_preserves_roles_summaries_and_witness_recovery():
    store = EvidenceStore()
    item = event("e1", value="fred")
    store.append(item)
    restored = EvidenceStore.from_snapshot(store.snapshot())
    assert restored.recover("e1", observation_cutoff=3.0) == (item,)
    assert restored.get_event("e1").role("recipient").entity_id == "fred"


def test_revision_is_append_only_and_requires_retained_parent():
    store = EvidenceStore()
    original = event("e1", value="fred")
    store.append(original)
    revised = event("e2", value="bill", event_time=2.0, observed_at=2.0, revision_of="e1")
    assert store.append(revised) == "STORED"
    assert store.get_event("e1") == original
    assert store.get_event("e2").revision_of == "e1"

def test_journal_recovery_merges_without_deleting_newer_evidence():
    old = EvidenceStore(capacity=4)
    old.append(event("old"))
    checkpoint = old.snapshot()
    live = EvidenceStore(capacity=4)
    live.append(event("new", event_time=2.0, observed_at=2.0))
    live.merge_snapshot(checkpoint)
    assert set(live.event_ids) == {"old", "new"}
