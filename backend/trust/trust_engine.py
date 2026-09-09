from typing import Dict, Optional

from .models import TrustScore

# Trust level thresholds — adjust as the project's policy evolves
TRUST_LEVELS = [
    (85, "TRUSTED"),
    (60, "NORMAL"),
    (35, "SUSPICIOUS"),
    (0, "UNTRUSTED"),
]


class TrustEngine:
    """
    Maintains dynamic trust scores for all entities on the network.
    Trust is never a static label — it moves up or down based on
    observed behavior (auth events, anomalies, incidents, etc.).
    """

    def __init__(self) -> None:
        self._entities: Dict[str, TrustScore] = {}

    def register_entity(self, entity_id: str, initial_score: float = 70.0) -> TrustScore:
        if entity_id not in self._entities:
            self._entities[entity_id] = TrustScore(entity_id=entity_id, score=initial_score)
        return self._entities[entity_id]

    def get_trust(self, entity_id: str) -> Optional[TrustScore]:
        return self._entities.get(entity_id)

    def update_trust(self, entity_id: str, reason: str, delta: float) -> TrustScore:
        """
        Apply a trust-affecting event.
        Positive delta = trust-building behavior (e.g. successful auth).
        Negative delta = suspicious behavior (e.g. anomaly detected).
        """
        entity = self.register_entity(entity_id)
        entity.record_event(reason=reason, delta=delta)
        return entity

    def get_trust_level(self, entity_id: str) -> str:
        entity = self._entities.get(entity_id)
        if entity is None:
            return "UNKNOWN"
        for threshold, label in TRUST_LEVELS:
            if entity.score >= threshold:
                return label
        return "UNTRUSTED"

    def all_scores(self) -> Dict[str, float]:
        return {eid: t.score for eid, t in self._entities.items()}