"""Independent non-oracle baselines for bAbI expansion Tasks 11, 14 and 19.

Prediction functions accept only observed stories/queries. Gold labels are read
only by the scoring boundary in evaluate_baselines(), never by a predictor.
"""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Callable, Iterable

from rgm.experiments.babi_expansion_adapters import (
    ExpansionQuery, ExpansionStory, GoldLabel, Prediction, Task11MentionEvent,
    Task14TemporalEvent, Task19SpatialEdge, predict_task11,
)


_NAME_GENDER = {
    "mary": "female", "sandra": "female", "julie": "female",
    "john": "male", "daniel": "male", "fred": "male", "bill": "male",
}
_PRONOUN_GENDER = {"she": "female", "he": "male"}
_INVERSE = {"north": "south", "south": "north", "east": "west", "west": "east"}
_DIRECTION_CODE = {"north": "n", "south": "s", "east": "e", "west": "w"}
_DIRECTION_ORDER = ("north", "south", "east", "west")


def recency_only_task11(story: ExpansionStory, query: ExpansionQuery) -> Prediction:
    """Deliberately weak control: latest observed location, ignoring identity."""
    if story.task_id != 11 or query.task_id != 11:
        raise ValueError("Task 11 baseline received another task's input")
    prior = [e for e in story.events if isinstance(e, Task11MentionEvent)
             and e.observed_at < query.observed_at]
    if not prior:
        return Prediction(None, (), True, "no_prior_mention")
    latest = max(prior, key=lambda e: e.observed_at)
    return Prediction(latest.location, (latest.event_id,), False)


def source_order_only_task14(story: ExpansionStory, query: ExpansionQuery) -> Prediction:
    """Choose the preceding same-actor event by source order, not event time."""
    if story.task_id != 14 or query.task_id != 14:
        raise ValueError("Task 14 baseline received another task's input")
    events = [e for e in story.events if isinstance(e, Task14TemporalEvent)
              and e.observed_at < query.observed_at]
    targets = [e for e in events if e.actor == query.entity
               and e.destination == query.target_location]
    if not targets:
        return Prediction(None, (), True, "target_event_not_observed")
    target = max(targets, key=lambda e: e.observed_at)
    prior = [e for e in events if e.actor == query.entity
             and e.observed_at < target.observed_at]
    if not prior:
        return Prediction(None, (target.event_id,), True, "no_prior_source_order_event")
    previous = max(prior, key=lambda e: e.observed_at)
    return Prediction(previous.destination, (previous.event_id, target.event_id), False,
                      temporal_edges=((previous.event_id, target.event_id),))

def lexical_temporal_cue_task14(story: ExpansionStory, query: ExpansionQuery) -> Prediction:
    """Use only the observed temporal anchor rank and its source-order tie-break."""
    if story.task_id != 14 or query.task_id != 14:
        raise ValueError("Task 14 baseline received another task's input")
    events = [e for e in story.events if isinstance(e, Task14TemporalEvent)
              and e.observed_at < query.observed_at]
    targets = [e for e in events if e.actor == query.entity
               and e.destination == query.target_location]
    if not targets:
        return Prediction(None, (), True, "target_event_not_observed")
    target = max(targets, key=lambda e: (e.event_time, e.observed_at))
    prior = [e for e in events if e.actor == query.entity
             and e.event_time < target.event_time]
    if not prior:
        return Prediction(None, (target.event_id,), True, "no_prior_temporal_location")
    previous = max(prior, key=lambda e: (e.event_time, e.observed_at))
    return Prediction(previous.destination, (previous.event_id, target.event_id), False,
                      temporal_edges=((previous.event_id, target.event_id),))

def direct_edge_only_task19(story: ExpansionStory, query: ExpansionQuery) -> Prediction:
    """Return a direction only when one observed edge directly connects endpoints."""
    if story.task_id != 19 or query.task_id != 19:
        raise ValueError("Task 19 baseline received another task's input")
    candidates: list[tuple[str, str, str, str, str]] = []
    for e in story.events:
        if not isinstance(e, Task19SpatialEdge) or e.observed_at >= query.observed_at:
            continue
        if e.start == query.start_location and e.end == query.end_location:
            candidates.append((_DIRECTION_CODE[e.direction], e.event_id,
                               query.start_location or "", query.end_location or "", e.direction))
        elif e.end == query.start_location and e.start == query.end_location:
            candidates.append((_DIRECTION_CODE[_INVERSE[e.direction]], e.event_id,
                               query.start_location or "", query.end_location or "", _INVERSE[e.direction]))
    sequences = {direction for direction, _, _, _, _ in candidates}
    if not candidates:
        return Prediction(None, (), True, "no_direct_observed_edge")
    if len(sequences) != 1:
        return Prediction(None, (), True, "conflicting_direct_edges")
    direction = next(iter(sequences))
    witness = min(event_id for code, event_id, _, _, _ in candidates if code == direction)
    path_direction = next(row[4] for row in candidates if row[0] == direction and row[1] == witness)
    return Prediction(direction, (witness,), False,
                      spatial_path_edges=((query.start_location or "", query.end_location or "",
                                           path_direction, witness),))

def breadth_first_search_task19(story: ExpansionStory, query: ExpansionQuery) -> Prediction:
    """Shortest observed-edge BFS; ambiguous shortest direction sequences abstain."""
    if story.task_id != 19 or query.task_id != 19:
        raise ValueError("Task 19 baseline received another task's input")
    graph: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for e in story.events:
        if not isinstance(e, Task19SpatialEdge) or e.observed_at >= query.observed_at:
            continue
        graph[e.start].append((e.end, e.direction, e.event_id))
        graph[e.end].append((e.start, _INVERSE[e.direction], e.event_id))
    for node in graph:
        graph[node].sort(key=lambda edge: (_DIRECTION_ORDER.index(edge[1]), edge[0], edge[2]))
    queue = deque([(query.start_location, (), (), (), frozenset({query.start_location}))])
    best_depth: int | None = None
    solutions: list[tuple[tuple[str, ...], tuple[str, ...],
                          tuple[tuple[str, str, str, str], ...]]] = []
    while queue:
        node, directions, witnesses, path_edges, visited = queue.popleft()
        depth = len(directions)
        if best_depth is not None and depth > best_depth:
            break
        if node == query.end_location and directions:
            best_depth = depth
            solutions.append((directions, witnesses, path_edges))
            continue
        for next_node, direction, event_id in graph.get(node, []):
            if next_node in visited:
                continue
            edge = (node, next_node, direction, event_id)
            queue.append((
                next_node, directions + (direction,), witnesses + (event_id,),
                path_edges + (edge,), visited | {next_node},
            ))
    if not solutions:
        return Prediction(None, (), True, "no_observed_path")
    direction_sequences = {item[0] for item in solutions}
    if len(direction_sequences) > 1:
        return Prediction(None, (), True, "ambiguous_shortest_paths")
    directions, witnesses, path_edges = sorted(solutions, key=lambda item: item[1])[0]
    answer = ",".join(_DIRECTION_CODE[d] for d in directions)
    return Prediction(answer, witnesses, False, spatial_path_edges=path_edges)

BASELINES: dict[int, tuple[tuple[str, Callable], ...]] = {
    11: (("nearest-compatible-antecedent", predict_task11),
         ("recency-only", recency_only_task11)),
    14: (("source-order-only", source_order_only_task14),
         ("lexical-temporal-cue-rule", lexical_temporal_cue_task14)),
    19: (("direct-edge-only", direct_edge_only_task19),
         ("breadth-first-search", breadth_first_search_task19)),
}


def predict_task11_supervision(story: ExpansionStory, query: ExpansionQuery) -> dict:
    """Predict Task 11 L0/L1/L2 targets from observed inputs only.

    This function deliberately accepts no GoldLabel or evaluator bundle. The
    caller issues these forecasts before opening the separately sealed targets.
    """
    prediction = predict_task11(story, query)
    if prediction.abstained:
        raise RuntimeError(f"Task 11 target forecast abstained: {prediction.reason}")
    event_by_id = {event.event_id: event for event in story.events}
    if not prediction.witness_event_ids:
        raise RuntimeError("Task 11 target forecast has no recoverable mention witness")
    target_event_id = prediction.witness_event_ids[-1]
    target_event = event_by_id.get(target_event_id)
    if not isinstance(target_event, Task11MentionEvent):
        raise RuntimeError("Task 11 target witness is not a source mention event")

    antecedent_by_mention = {
        mention_event_id: antecedent_event_id
        for mention_event_id, antecedent_event_id in prediction.antecedent_edges
    }
    if target_event.is_pronoun:
        antecedent_id = antecedent_by_mention.get(target_event_id)
        antecedent = event_by_id.get(antecedent_id or "")
        if not isinstance(antecedent, Task11MentionEvent) or antecedent.is_pronoun:
            raise RuntimeError("Task 11 target pronoun has no predicted name anchor")
        entity_id = antecedent.surface_mention.casefold()
        l1 = {
            "mention_event_id": target_event_id,
            "antecedent_event_id": antecedent_id,
            "entity_id": entity_id,
            "relation": "corefers_with",
        }
    else:
        entity_id = target_event.surface_mention.casefold()
        l1 = {
            "mention_event_id": target_event_id,
            "antecedent_event_id": None,
            "entity_id": entity_id,
            "relation": "self_anchor",
        }
    if entity_id != query.entity:
        raise RuntimeError("Task 11 predicted target mention does not resolve to queried entity")
    return {
        "l0_mention_binding": {
            "mention_event_id": target_event_id,
            "entity_id": entity_id,
        },
        "l1_coreference_edge": l1,
        "l2_entity_state": {
            "entity_id": query.entity,
            "location": prediction.answer,
            "witness_event_ids": list(prediction.witness_event_ids),
        },
        "answer": prediction.answer,
    }


def _prf(predicted: set, gold: set) -> dict[str, float | int]:
    true_positive = len(predicted & gold)
    precision = true_positive / len(predicted) if predicted else (1.0 if not gold else 0.0)
    recall = true_positive / len(gold) if gold else (1.0 if not predicted else 0.0)
    f1 = (2.0 * precision * recall / (precision + recall)
          if precision + recall else 0.0)
    return {
        "true_positive": true_positive,
        "predicted_count": len(predicted),
        "gold_count": len(gold),
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _gold_task14_relation(story: ExpansionStory, query: ExpansionQuery) -> tuple[str, str] | None:
    events = [event for event in story.events
              if isinstance(event, Task14TemporalEvent)
              and event.actor == query.entity and event.observed_at < query.observed_at]
    targets = [event for event in events if event.destination == query.target_location]
    if not targets:
        return None
    target = max(targets, key=lambda event: (event.event_time, event.observed_at))
    predecessors = [event for event in events if event.event_time < target.event_time]
    if not predecessors:
        return None
    previous = max(predecessors, key=lambda event: (event.event_time, event.observed_at))
    return previous.event_id, target.event_id


def evaluate_baselines(
    stories: Iterable[ExpansionStory],
    labels: Iterable[GoldLabel],
    *,
    evaluate_labels: bool = True,
    target_labels: Iterable[dict] | None = None,
) -> dict:
    """Score answer, witnesses and task-specific targets in an isolated evaluator pass."""
    story_rows = list(stories)
    label_rows = list(labels)
    stories_by_id = {story.story_id: story for story in story_rows}
    queries_by_id = {
        query.query_id: (story, query)
        for story in story_rows for query in story.queries
    }
    if len(queries_by_id) != sum(len(story.queries) for story in story_rows):
        raise ValueError("duplicate query IDs in baseline input")
    labels_by_id = {label.query_id: label for label in label_rows}
    if len(labels_by_id) != len(label_rows):
        raise ValueError("duplicate evaluator labels")
    if evaluate_labels and set(labels_by_id) != set(queries_by_id):
        raise ValueError("baseline scorer requires exactly one evaluator label per query")
    if not evaluate_labels and labels_by_id:
        raise ValueError("non-evaluating baseline pass must not receive evaluator labels")
    target_rows = list(target_labels or ())
    target_by_query = {row["query_id"]: row for row in target_rows}
    if len(target_by_query) != len(target_rows):
        raise ValueError("duplicate task-target evaluator labels")
    if set(target_by_query) - set(queries_by_id):
        raise ValueError("task-target labels include an unknown query ID")

    results = {}
    for task_id in (11, 14, 19):
        task_queries = [(query_id, pair) for query_id, pair in queries_by_id.items()
                        if pair[0].task_id == task_id]
        if not task_queries:
            continue
        results[str(task_id)] = {}
        for name, predictor in BASELINES[task_id]:
            query_count = correct = covered = supported = support_total = false_witnesses = 0
            predicted_witnesses = 0
            target_predicted: set = set()
            target_gold: set = set()
            target_scored_queries = target_exact_queries = 0
            path_exact_queries = path_scored_queries = 0
            for query_id, (story, query) in task_queries:
                prediction = predictor(story, query)
                query_count += 1
                covered += int(not prediction.abstained)
                if not evaluate_labels:
                    continue
                label = labels_by_id[query_id]
                correct += int(not prediction.abstained and prediction.answer == label.answer)
                story_prefix = query_id.rsplit(":line", 1)[0]
                gold_witness_order = tuple(
                    f"{story_prefix}:line{line_no:06d}"
                    for line_no in label.support_line_numbers
                )
                gold_witnesses = set(gold_witness_order)
                predicted = set(prediction.witness_event_ids)
                predicted_witnesses += len(predicted)
                supported += len(predicted & gold_witnesses)
                support_total += len(gold_witnesses)
                false_witnesses += len(predicted - gold_witnesses)

                if task_id == 11:
                    target_label = target_by_query.get(query_id)
                    if target_label is not None and "mention_binding_edges" in target_label:
                        target_scored_queries += 1
                        predicted_edges = set(prediction.antecedent_edges)
                        gold_edges = {
                            (str(edge["mention_event_id"]), str(edge["antecedent_event_id"]))
                            for edge in target_label["mention_binding_edges"]
                        }
                        target_predicted.update(predicted_edges)
                        target_gold.update(gold_edges)
                        target_exact_queries += int(predicted_edges == gold_edges)
                elif task_id == 14:
                    gold_relation = _gold_task14_relation(story, query)
                    if gold_relation is not None:
                        target_scored_queries += 1
                        predicted_relations = set(prediction.temporal_edges)
                        target_predicted.update(predicted_relations)
                        target_gold.add(gold_relation)
                        target_exact_queries += int(predicted_relations == {gold_relation})
                elif task_id == 19:
                    target_scored_queries += 1
                    predicted_edges = set(prediction.witness_event_ids)
                    target_predicted.update(predicted_edges)
                    target_gold.update(gold_witnesses)
                    path_scored_queries += 1
                    path_exact_queries += int(
                        not prediction.abstained
                        and prediction.answer == label.answer
                        and tuple(prediction.witness_event_ids) == gold_witness_order
                    )

            target_metric = {
                "task_id": task_id,
                "scored_queries": target_scored_queries,
                "status": "PASS_METRICS_AVAILABLE" if target_scored_queries else "NOT_AVAILABLE",
            }
            if target_scored_queries:
                target_metric.update(_prf(target_predicted, target_gold))
                target_metric["target_exact_match"] = target_exact_queries / target_scored_queries
            if task_id == 11 and not target_scored_queries:
                target_metric["reason"] = (
                    "The official bAbI Task 11 answer labels do not annotate antecedent edges; "
                    "coreference-edge metrics require a separately reviewed target-label stream."
                )
            if task_id == 14 and target_scored_queries:
                target_metric["temporal_relation_exact_match"] = target_exact_queries / target_scored_queries
            if task_id == 19 and path_scored_queries:
                target_metric["ordered_path_exact_match"] = path_exact_queries / path_scored_queries
                target_metric["target_exact_match"] = path_exact_queries / path_scored_queries

            results[str(task_id)][name] = {
                "queries": query_count,
                "predictions_covered": covered,
                "coverage": covered / query_count if query_count else 0.0,
                "prediction_presentations": query_count,
                "labels_scored": query_count if evaluate_labels else 0,
                "answer_exact_matches": correct if evaluate_labels else None,
                "answer_exact_match": correct / query_count if evaluate_labels and query_count else None,
                "support_witnesses_recalled": supported if evaluate_labels else None,
                "support_witness_total": support_total if evaluate_labels else None,
                "support_witness_recall": supported / support_total if evaluate_labels and support_total else None,
                "false_witness_count": false_witnesses if evaluate_labels else None,
                "false_witness_rate": (
                    false_witnesses / predicted_witnesses
                    if evaluate_labels and predicted_witnesses else None
                ),
                "target_metrics": target_metric,
            }
    return {
        "schema": "HLG-BABI-EXPANSION-BASELINE-EVALUATION-v2",
        "label_scoring_enabled": evaluate_labels,
        "target_label_query_count": len(target_by_query),
        "task_results": results,
    }
