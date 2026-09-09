from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List


@dataclass
class TrustEvent:
    """A single event that affected an entity's trust score."""
    timestamp: str
    reason: str
    delta: float
    resulting_score: float


@dataclass
class TrustScore:
    """Tracks the current trust score and history for one network entity."""
    entity_id: str
    score: float = 70.0  # neutral starting trust (0-100 scale)
    history: List[TrustEvent] = field(default_factory=list)

    def record_event(self, reason: str, delta: float) -> None:
        self.score = max(0.0, min(100.0, self.score + delta))
        self.history.append(
            TrustEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                reason=reason,
                delta=delta,
                resulting_score=self.score,
            )
        )