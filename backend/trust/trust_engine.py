from typing import Dict, Optional

from .models import TrustScore

TRUST_LEVELS = [
    (85, "TRUSTED"),
    (60, "NORMAL"),
    (35, "SUSPICIOUS"),
    (0, "UNTRUSTED"),
]

DECAY_STEP = 5.0
DECAY_TRIGGER_COUNT = 2
RECOVERY_STEP = 2.0
RECOVERY_TRIGGER_COUNT = 3


class TrustEngine:
    def __init__(self) -> None:
        self._entities: Dict[str, TrustScore] = {}

    def register_entity(self, entity_id: str, initial_score: float = 70.0) -> TrustScore:
        if entity_id not in self._entities:
            self._entities[entity_id] = TrustScore(entity_id=entity_id, score=initial_score)
        return self._entities[entity_id]

    def get_trust(self, entity_id: str) -> Optional[TrustScore]:
        return self._entities.get(entity_id)

    def update_trust(self, entity_id: str, reason: str, delta: float) -> TrustScore:
        entity = self.register_entity(entity_id)
        entity.record_event(reason=reason, delta=delta)
        self._apply_decay_or_recovery(entity)
        return entity

    def _apply_decay_or_recovery(self, entity: TrustScore) -> None:
        if entity.consecutive_suspicious_events >= DECAY_TRIGGER_COUNT:
            entity.record_event(
                reason=f"trust decay after {entity.consecutive_suspicious_events} consecutive suspicious events",
                delta=-DECAY_STEP,
                track_streak=False,
            )
            entity.consecutive_suspicious_events = 0
        elif entity.consecutive_normal_events >= RECOVERY_TRIGGER_COUNT:
            entity.record_event(
                reason=f"trust recovery after {entity.consecutive_normal_events} consecutive normal events",
                delta=RECOVERY_STEP,
                track_streak=False,
            )
            entity.consecutive_normal_events = 0

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