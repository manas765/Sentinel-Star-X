from typing import List, Tuple

from .models import NetworkActivitySnapshot, SecurityAssessment

# Sandboxed, predefined detection rules — thresholds are configurable,
# not fixed real-world attack signatures.
TRAFFIC_SPIKE_MULTIPLIER = 3.0     # traffic vs baseline
CONNECTION_SPIKE_MULTIPLIER = 2.5  # connection count vs baseline
FAILED_AUTH_THRESHOLD = 3


class SecurityAnomalyDetector:
    """
    Detects controlled, simulated security anomalies:
    - abnormal traffic volume
    - unexpected communication with unauthorized peers
    - unusual connection-count spikes
    - unauthorized device behavior
    - repeated failed authentication attempts

    This module does not perform any real intrusion or attack logic —
    it only evaluates simulated telemetry against configurable rules.
    """

    def assess(self, snapshot: NetworkActivitySnapshot) -> SecurityAssessment:
        risk = 0.0
        flags: List[str] = []

        risk, flags = self._check_traffic_spike(snapshot, risk, flags)
        risk, flags = self._check_connection_spike(snapshot, risk, flags)
        risk, flags = self._check_unexpected_communication(snapshot, risk, flags)
        risk, flags = self._check_unauthorized_device(snapshot, risk, flags)
        risk, flags = self._check_failed_auth(snapshot, risk, flags)

        risk = max(0.0, min(1.0, risk))
        return SecurityAssessment(entity_id=snapshot.entity_id, risk_score=risk, flags=flags)

    def _check_traffic_spike(
        self, s: NetworkActivitySnapshot, risk: float, flags: List[str]
    ) -> Tuple[float, List[str]]:
        if s.baseline_traffic_mbps > 0 and s.traffic_volume_mbps >= s.baseline_traffic_mbps * TRAFFIC_SPIKE_MULTIPLIER:
            risk += 0.3
            flags.append(
                f"traffic spike: {s.traffic_volume_mbps} Mbps vs baseline {s.baseline_traffic_mbps} Mbps"
            )
        return risk, flags

    def _check_connection_spike(
        self, s: NetworkActivitySnapshot, risk: float, flags: List[str]
    ) -> Tuple[float, List[str]]:
        if s.baseline_connection_count > 0 and s.connection_count >= s.baseline_connection_count * CONNECTION_SPIKE_MULTIPLIER:
            risk += 0.2
            flags.append(
                f"unusual connection count: {s.connection_count} vs baseline {s.baseline_connection_count}"
            )
        return risk, flags

    def _check_unexpected_communication(
        self, s: NetworkActivitySnapshot, risk: float, flags: List[str]
    ) -> Tuple[float, List[str]]:
        unexpected_peers = [p for p in s.communicating_with if p not in s.authorized_peers]
        if unexpected_peers:
            risk += 0.25
            flags.append(f"unexpected communication with: {', '.join(unexpected_peers)}")
        return risk, flags

    def _check_unauthorized_device(
        self, s: NetworkActivitySnapshot, risk: float, flags: List[str]
    ) -> Tuple[float, List[str]]:
        if not s.is_authorized_device:
            risk += 0.4
            flags.append("device is not on the authorized device list")
        return risk, flags

    def _check_failed_auth(
        self, s: NetworkActivitySnapshot, risk: float, flags: List[str]
    ) -> Tuple[float, List[str]]:
        if s.failed_auth_attempts >= FAILED_AUTH_THRESHOLD:
            risk += 0.3
            flags.append(f"{s.failed_auth_attempts} failed authentication attempts")
        return risk, flags