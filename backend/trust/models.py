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
    consecutive_normal_events: int = 0
    consecutive_suspicious_events: int = 0

    def record_event(self, reason: str, delta: float, track_streak: bool = True) -> None:
        self.score = max(0.0, min(100.0, self.score + delta))
        self.history.append(
            TrustEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                reason=reason,
                delta=delta,
                resulting_score=self.score,
            )
        )
        if not track_streak:
            return
        if delta < 0:
            self.consecutive_suspicious_events += 1
            self.consecutive_normal_events = 0
        elif delta > 0:
            self.consecutive_normal_events += 1
            self.consecutive_suspicious_events = 0