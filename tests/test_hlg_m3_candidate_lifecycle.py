import numpy as np
import pytest

from rgm.leptograph.m3 import CandidateLifecycle, CandidateRevision


def _feed(lifecycle, start_step, count, operator, *, missing_indices=(), rank_one=False,
          phase_identifiable=True):
    terminal = None
    for offset in range(count):
        if offset in missing_indices:
            source = None
            target = None
            observed = False
        else:
            x0 = float(offset + 1)
            x1 = 2.0 * x0 if rank_one else float((offset + 1) ** 2 % 17 + 0.25 * offset)
            source = np.array([x0, x1])
            target = np.asarray(operator) @ source
            observed = True
        terminal = lifecycle.observe(
            step_index=start_step + offset,
            source=source,
            residual_target=target,
            observed=observed,
            identifiable=phase_identifiable,
        )
    return terminal


def test_candidate_lifecycle_enforces_exact_32_32_64_and_untouched_post_window():
    truth = np.array([[1.3, -0.4], [0.2, 0.9]])
    incumbent = np.zeros((2, 2))
    revision = CandidateRevision(incumbent)
    lifecycle = CandidateLifecycle(revision, 2, 2)
    lifecycle.start(alarm_step=100)

    assert lifecycle.record_alarm(108) is False
    fit_transition = _feed(lifecycle, 101, 32, truth)
    assert fit_transition is None
    assert lifecycle.phase == "VALIDATION"

    validation_transition = _feed(lifecycle, 133, 32, truth)
    assert validation_transition is None
    assert lifecycle.phase == "POST_PROMOTION"
    assert revision.revision_count == 1
    assert np.allclose(revision.accepted_operator, truth, atol=1e-8)

    final = _feed(lifecycle, 165, 64, truth)
    assert final["status"] == "PROMOTED_EVALUATED"
    assert final["fit_window"]["start"] == 101
    assert final["fit_window"]["end"] == 132
    assert final["fit_window"]["slots"] == 32
    assert final["fit_window"]["observed_rows"] == 32
    assert final["validation_window"]["start"] == 133
    assert final["validation_window"]["end"] == 164
    assert final["validation_window"]["slots"] == 32
    assert final["validation_window"]["observed_rows"] == 32
    assert final["post_promotion_window"]["start"] == 165
    assert final["post_promotion_window"]["end"] == 228
    assert final["post_promotion_window"]["slots"] == 64
    assert final["post_promotion_window"]["observed_rows"] == 64
    assert final["secondary_alarm_steps"] == [108]
    assert final["promoted"] is True
    assert final["post_promotion_window"]["relative_improvement"] > 0.99


def test_candidate_lifecycle_does_not_shorten_insufficient_fit_window():
    revision = CandidateRevision(np.zeros((2, 2)))
    lifecycle = CandidateLifecycle(revision, 2, 2)
    lifecycle.start(10)
    result = _feed(
        lifecycle, 11, 32, np.eye(2), missing_indices=set(range(9))
    )
    assert result["status"] == "INSUFFICIENT_EVIDENCE_FIT"
    assert result["fit_window"]["slots"] == 32
    assert result["fit_window"]["observed_rows"] == 23
    assert revision.revision_count == 0
    assert np.array_equal(revision.accepted_operator, np.zeros((2, 2)))


def test_candidate_lifecycle_requires_24_validation_rows_and_preserves_incumbent():
    incumbent = 0.25 * np.eye(2)
    revision = CandidateRevision(incumbent)
    lifecycle = CandidateLifecycle(revision, 2, 2)
    lifecycle.start(0)
    _feed(lifecycle, 1, 32, np.eye(2))
    result = _feed(
        lifecycle, 33, 32, np.eye(2), missing_indices=set(range(9))
    )
    assert result["status"] == "INSUFFICIENT_EVIDENCE_VALIDATION"
    assert result["validation_window"]["slots"] == 32
    assert result["validation_window"]["observed_rows"] == 23
    assert revision.revision_count == 0
    assert np.array_equal(revision.accepted_operator, incumbent)


def test_candidate_lifecycle_rejects_rank_deficient_fit_even_with_lower_validation_loss():
    incumbent = np.zeros((2, 2))
    revision = CandidateRevision(incumbent)
    lifecycle = CandidateLifecycle(revision, 2, 2)
    lifecycle.start(0)
    _feed(lifecycle, 1, 32, np.eye(2), rank_one=True)
    result = _feed(lifecycle, 33, 32, np.eye(2), phase_identifiable=True)
    assert result["status"] == "REJECTED"
    assert result["fit_window"]["design_rank"] == 1
    assert result["promoted"] is False
    assert revision.revision_count == 0
    assert np.array_equal(revision.accepted_operator, incumbent)


def test_candidate_lifecycle_enforces_contiguous_chronology():
    lifecycle = CandidateLifecycle(CandidateRevision(np.zeros((1, 1))), 1, 1)
    lifecycle.start(5)
    with pytest.raises(ValueError, match="expected chronological step"):
        lifecycle.observe(
            step_index=7, source=[1.0], residual_target=[1.0], observed=True
        )


def test_candidate_lifecycle_resource_snapshot_counts_numeric_buffers():
    lifecycle = CandidateLifecycle(CandidateRevision(np.zeros((2, 2))), 2, 2)
    lifecycle.start(0)
    resources = lifecycle.resource_snapshot()
    assert resources["fit_gram_bytes"] == 2 * 2 * 8
    assert resources["fit_cross_bytes"] == 2 * 2 * 8
    assert resources["incumbent_snapshot_bytes"] == 2 * 2 * 8
    assert resources["numeric_buffer_bytes_total"] == 3 * 2 * 2 * 8
