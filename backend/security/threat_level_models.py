from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import List


class ThreatLevel(IntEnum):
    NORMAL = 0
    MONITOR = 1
    SUSPICIOUS = 2
    RESTRICT = 3
    QUARANTINE = 4
    EMERGENCY = 5


@dataclass
class ThreatLevelChange:
    timestamp: str
    from_level: str
    to_level: str
    reason: str


@dataclass
class ThreatLevelState:
    entity_id: str
    level: ThreatLevel = ThreatLevel.NORMAL
    history: List[ThreatLevelChange] = field(default_factory=list)

    def transition_to(self, new_level: ThreatLevel, reason: str) -> None:
        if new_level == self.level:
            return
        self.history.append(
            ThreatLevelChange(
                timestamp=datetime.now(timezone.utc).isoformat(),
                from_level=self.level.name,
                to_level=new_level.name,
                reason=reason,
            )
        )
        self.level = new_level