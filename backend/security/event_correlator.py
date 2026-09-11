from datetime import datetime, timezone
from typing import Dict, List, Set

from .event_correlation_models import FusedIncident, SecurityEvent

# Only correlate events happening close together in time.
TIME_WINDOW_SECONDS = 60
MIN_RISK_TO_CONSIDER = 0.25

_incident_counter = 0


def _next_incident_id() -> str:
    global _incident_counter
    _incident_counter += 1
    return f"FUSED-{_incident_counter:04d}"


class EventCorrelator:
    """
    Groups security events that are likely part of the same underlying
    incident — either because the affected entities communicated with
    each other, or because they were flagged within a short time window
    of each other — instead of reporting every flagged entity as an
    isolated, unrelated incident.
    """

    def correlate(self, events: List[SecurityEvent]) -> List[FusedIncident]:
        relevant = [e for e in events if e.risk_score >= MIN_RISK_TO_CONSIDER]
        if not relevant:
            return []

        groups = self._group_by_relationship(relevant)

        incidents = []
        for group in groups:
            entity_ids = [e.entity_id for e in group]
            combined_risk = min(1.0, sum(e.risk_score for e in group) / len(group) + 0.05 * (len(group) - 1))
            reason = self._describe_correlation(group)
            incidents.append(
                FusedIncident(
                    incident_id=_next_incident_id(),
                    entity_ids=entity_ids,
                    combined_risk_score=round(combined_risk, 4),
                    correlation_reason=reason,
                    event_count=len(group),
                )
            )
        return incidents

    def _group_by_relationship(self, events: List[SecurityEvent]) -> List[List[SecurityEvent]]:
        # Union-find style grouping: connect events that share a peer relationship
        # or fall within the same time window.
        parent: Dict[str, str] = {e.entity_id: e.entity_id for e in events}

        def find(x: str) -> str:
            while parent[x] != x:
                x = parent[x]
            return x

        def union(a: str, b: str) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        entity_ids: Set[str] = {e.entity_id for e in events}
        for event in events:
            for peer in event.related_peers:
                if peer in entity_ids:
                    union(event.entity_id, peer)

        for i, a in enumerate(events):
            for b in events[i + 1:]:
                if self._within_time_window(a.timestamp, b.timestamp):
                    union(a.entity_id, b.entity_id)

        grouped: Dict[str, List[SecurityEvent]] = {}
        for event in events:
            root = find(event.entity_id)
            grouped.setdefault(root, []).append(event)

        return list(grouped.values())

    def _within_time_window(self, ts_a: str, ts_b: str) -> bool:
        try:
            time_a = datetime.fromisoformat(ts_a)
            time_b = datetime.fromisoformat(ts_b)
        except ValueError:
            return False
        return abs((time_a - time_b).total_seconds()) <= TIME_WINDOW_SECONDS

    def _describe_correlation(self, group: List[SecurityEvent]) -> str:
        if len(group) == 1:
            return "isolated event, no correlation found"
        entity_list = ", ".join(e.entity_id for e in group)
        return f"{len(group)} events correlated across [{entity_list}] via shared peers or close timing"