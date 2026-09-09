from dataclasses import dataclass
from .trust_engine import TrustEngine

# Configurable thresholds — tune these based on real/simulated telemetry later
CPU_WARNING = 75.0          # % utilization
CPU_CRITICAL = 90.0
MEMORY_WARNING = 75.0
MEMORY_CRITICAL = 90.0
PACKET_LOSS_WARNING = 2.0   # %
PACKET_LOSS_CRITICAL = 5.0
LATENCY_WARNING_MS = 50.0
LATENCY_CRITICAL_MS = 150.0
FAILURE_RISK_WARNING = 0.4  # 0-1 probability
FAILURE_RISK_CRITICAL = 0.7


@dataclass
class SwitchMetrics:
    """A snapshot of the central switch's current telemetry."""
    switch_id: str
    cpu_percent: float
    memory_percent: float
    packet_loss_percent: float
    latency_ms: float
    failure_risk: float  # 0.0 - 1.0, from the prediction module (feature #7)
    security_risk: float = 0.0  # 0.0 - 1.0, from security anomaly detection (feature #13)


class CentralSwitchTrustMonitor:
    """
    Applies central-switch-specific telemetry to the shared TrustEngine.
    The central switch is the single point of failure in a Star topology,
    so its trust score should react more sensitively than a normal device.
    """

    def __init__(self, trust_engine: TrustEngine) -> None:
        self.trust_engine = trust_engine

    def evaluate(self, metrics: SwitchMetrics) -> None:
        self.trust_engine.register_entity(metrics.switch_id)

        self._check_metric(
            metrics.switch_id, "CPU", metrics.cpu_percent,
            CPU_WARNING, CPU_CRITICAL,
        )
        self._check_metric(
            metrics.switch_id, "memory", metrics.memory_percent,
            MEMORY_WARNING, MEMORY_CRITICAL,
        )
        self._check_metric(
            metrics.switch_id, "packet loss", metrics.packet_loss_percent,
            PACKET_LOSS_WARNING, PACKET_LOSS_CRITICAL,
        )
        self._check_metric(
            metrics.switch_id, "latency", metrics.latency_ms,
            LATENCY_WARNING_MS, LATENCY_CRITICAL_MS,
        )
        self._check_metric(
            metrics.switch_id, "predicted failure risk", metrics.failure_risk,
            FAILURE_RISK_WARNING, FAILURE_RISK_CRITICAL,
        )

        if metrics.security_risk >= 0.5:
            self.trust_engine.update_trust(
                metrics.switch_id,
                reason=f"elevated security risk ({metrics.security_risk:.2f})",
                delta=-15.0,
            )

    def _check_metric(
        self, switch_id: str, label: str, value: float,
        warning_threshold: float, critical_threshold: float,
    ) -> None:
        if value >= critical_threshold:
            self.trust_engine.update_trust(
                switch_id,
                reason=f"{label} critical ({value})",
                delta=-15.0,
            )
        elif value >= warning_threshold:
            self.trust_engine.update_trust(
                switch_id,
                reason=f"{label} elevated ({value})",
                delta=-5.0,
            )
        else:
            self.trust_engine.update_trust(
                switch_id,
                reason=f"{label} normal ({value})",
                delta=0.5,
            )