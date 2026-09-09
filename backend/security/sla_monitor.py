from datetime import datetime, timezone
from typing import Dict, List

from .sla_models import SLATarget, SLAStatus, SLAViolation

# How far over target counts as MINOR vs MAJOR vs CRITICAL
MINOR_OVERAGE_RATIO = 1.1   # up to 10% over target
MAJOR_OVERAGE_RATIO = 1.5   # up to 50% over target
# anything beyond that is CRITICAL


class SLAMonitor:
    """
    Tracks committed SLA targets per critical service and evaluates
    live metrics against them. An SLA violation is treated as an
    early-warning signal, independent of security or hardware checks.
    """

    def __init__(self) -> None:
        self._targets: Dict[str, SLATarget] = {}

    def register_target(self, target: SLATarget) -> None:
        self._targets[target.entity_id] = target

    def get_target(self, entity_id: str) -> SLATarget:
        return self._targets.get(entity_id)

    def evaluate(
        self,
        entity_id: str,
        uptime_percent: float,
        response_time_ms: float,
        packet_loss_percent: float,
    ) -> SLAStatus:
        target = self._targets.get(entity_id)
        if target is None:
            # No SLA registered for this entity — nothing to violate.
            return SLAStatus(
                entity_id=entity_id,
                name="(no SLA registered)",
                is_compliant=True,
                uptime_percent=uptime_percent,
                current_response_time_ms=response_time_ms,
                current_packet_loss_percent=packet_loss_percent,
            )

        violations: List[SLAViolation] = []

        if uptime_percent < target.uptime_target_percent:
            violations.append(self._build_violation(
                "uptime_percent", target.uptime_target_percent, uptime_percent, lower_is_worse=False,
            ))

        if response_time_ms > target.max_response_time_ms:
            violations.append(self._build_violation(
                "response_time_ms", target.max_response_time_ms, response_time_ms, lower_is_worse=True,
            ))

        if packet_loss_percent > target.max_allowed_packet_loss_percent:
            violations.append(self._build_violation(
                "packet_loss_percent", target.max_allowed_packet_loss_percent, packet_loss_percent, lower_is_worse=True,
            ))

        return SLAStatus(
            entity_id=entity_id,
            name=target.name,
            is_compliant=len(violations) == 0,
            uptime_percent=uptime_percent,
            current_response_time_ms=response_time_ms,
            current_packet_loss_percent=packet_loss_percent,
            violations=violations,
        )

    def _build_violation(
        self, metric: str, target_value: float, actual_value: float, lower_is_worse: bool
    ) -> SLAViolation:
        if lower_is_worse:
            # actual is worse when higher than target (e.g. response time, packet loss)
            ratio = actual_value / target_value if target_value > 0 else float("inf")
        else:
            # actual is worse when lower than target (e.g. uptime)
            ratio = target_value / actual_value if actual_value > 0 else float("inf")

        if ratio >= MAJOR_OVERAGE_RATIO:
            severity = "CRITICAL"
        elif ratio >= MINOR_OVERAGE_RATIO:
            severity = "MAJOR"
        else:
            severity = "MINOR"

        return SLAViolation(
            timestamp=datetime.now(timezone.utc).isoformat(),
            metric=metric,
            target=target_value,
            actual=actual_value,
            severity=severity,
        )