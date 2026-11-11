"""Explicit rules governing relation algebra and functional predicates."""
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass(frozen=True)
class RelationSchema:
    """Declared inverse/composition semantics and functional predicates."""
    inverses: dict[str, str] = field(default_factory=dict)
    compositions: dict[tuple[str, str], str] = field(default_factory=dict)
    functional_predicates: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        for source, inverse in self.inverses.items():
            if not source or not inverse:
                raise ValueError("inverse predicate names must be non-empty")
        for pair, result in self.compositions.items():
            if len(pair) != 2 or not all(pair) or not result:
                raise ValueError("composition rules require two predicates and a result")
        if any(not item for item in self.functional_predicates):
            raise ValueError("functional predicate names must be non-empty")

    def inverse_of(self, predicate: str) -> str:
        try:
            return self.inverses[predicate]
        except KeyError as exc:
            raise ValueError(f"no inverse semantics declared for {predicate!r}") from exc

    def composition_of(self, left: str, right: str) -> str:
        try:
            return self.compositions[(left, right)]
        except KeyError as exc:
            raise ValueError(f"no composition rule declared for ({left!r}, {right!r})") from exc
