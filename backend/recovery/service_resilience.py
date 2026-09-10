from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class ServiceStatus(BaseModel):
    service_name: str
    is_up: bool
    uptime_percent: float = 100.0
    last_checked: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    degraded: bool = False


class ResilienceReport(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_services: int
    services_up: int
    services_down: int
    services_degraded: int
    overall_resilience_score: float  # 0.0 - 100.0
    weakest_service: Optional[str] = None


class ServiceLevelResilience:
    """
    Feature #50 - Service-Level Resilience.
    Tracks which services are up, down, or degraded and
    produces an overall resilience score for the network.
    """

    def __init__(self) -> None:
        self._services: Dict[str, ServiceStatus] = {}

    def register(self, service_name: str) -> ServiceStatus:
        status = ServiceStatus(service_name=service_name, is_up=True)
        self._services[service_name] = status
        return status

    def update(self, service_name: str, is_up: bool, uptime_percent: float = 100.0, degraded: bool = False) -> ServiceStatus:
        if service_name not in self._services:
            self.register(service_name)
        svc = self._services[service_name]
        svc.is_up = is_up
        svc.uptime_percent = uptime_percent
        svc.degraded = degraded
        svc.last_checked = datetime.now(timezone.utc)
        return svc

    def get(self, service_name: str) -> Optional[ServiceStatus]:
        return self._services.get(service_name)

    def all_up(self) -> bool:
        return all(s.is_up for s in self._services.values())

    def report(self) -> ResilienceReport:
        services = list(self._services.values())
        up = [s for s in services if s.is_up]
        down = [s for s in services if not s.is_up]
        degraded = [s for s in services if s.degraded]

        if not services:
            return ResilienceReport(
                total_services=0, services_up=0, services_down=0,
                services_degraded=0, overall_resilience_score=100.0
            )

        score = (len(up) / len(services)) * 100
        # Penalise degraded services
        score -= len(degraded) * 5
        score = max(0.0, min(100.0, score))

        weakest = min(services, key=lambda s: s.uptime_percent).service_name

        return ResilienceReport(
            total_services=len(services),
            services_up=len(up),
            services_down=len(down),
            services_degraded=len(degraded),
            overall_resilience_score=round(score, 2),
            weakest_service=weakest,
        )
