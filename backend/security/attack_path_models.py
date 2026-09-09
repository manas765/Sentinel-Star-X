from dataclasses import dataclass
from typing import List


@dataclass
class AttackPath:
    """A possible path a threat could spread along, from a compromised node."""
    nodes: List[str]
    risk_score: float  # 0.0 - 1.0, higher = more dangerous path

    @property
    def hop_count(self) -> int:
        return max(0, len(self.nodes) - 1)

    @property
    def target(self) -> str:
        return self.nodes[-1] if self.nodes else ""