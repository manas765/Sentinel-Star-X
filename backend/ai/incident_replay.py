"""
backend/ai/incident_replay.py

Feature 9/16 (global #38): Incident Replay.

INTERFACE FLAG -- real overlap, not guessed away: your own roadmap notes
this overlaps with Aakash's Network Memory, and Akshata already built a
Network Time Machine (rolling telemetry history, per-node queries) on her
track. To avoid duplicating either: this stores the AI's INTERPRETATION
over time (anomaly + classification + root cause + explanation per tick),
not raw telemetry -- "what did the AI conclude, tick by tick" rather than
"what were the raw numbers, tick by tick." Akshata's Time Machine is the
right place to ask for the latter. Worth a direct conversation with Aakash
before this goes further, in case his Network Memory already covers this
exact use case and this becomes redundant.

Records each analyzed tick into a rolling buffer, auto-detects incident
boundaries (anomaly-free -> anomalous -> anomaly-free again), and lets you
pull back the full tick-by-tick sequence for a given incident.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

SEVERITY_RANK = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


@dataclass
class RecordedTick:
    tick_index: int
    timestamp: float
    node_anomalies: list
    link_anomalies: list
    classifications: list
    link_classifications: list
    root_causes: list
    explanations: list
    has_anomaly: bool

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class Incident:
    incident_id: int
    start_tick: int
    end_tick: Optional[int]  # None while still ongoing
    peak_severity: str
    root_cause_ids: list = field(default_factory=list)
    tick_count: int = 0

    def to_dict(self) -> dict:
        return dict(self.__dict__)


class IncidentReplayBuffer:
    """Rolling buffer of analyzed ticks, with automatic incident grouping.

    max_ticks bounds memory use, not incident tracking -- if a tick falls
    out of the rolling window, replay() for an old incident will only
    return whatever of it is still in the window.
    """

    def __init__(self, max_ticks: int = 500):
        self.max_ticks = max_ticks
        self._ticks: list = []
        self._incidents: list = []
        self._current_incident: Optional[Incident] = None
        self._next_incident_id = 0
        self._tick_counter = 0

    def record(
        self,
        timestamp: float,
        node_anomalies: list,
        link_anomalies: list,
        classifications: list,
        link_classifications: list,
        root_causes: list,
        explanations: list,
    ) -> None:
        tick_index = self._tick_counter
        self._tick_counter += 1

        has_anomaly = any(r["is_anomalous"] for r in node_anomalies) or any(
            r["is_anomalous"] for r in link_anomalies
        )

        tick = RecordedTick(
            tick_index=tick_index,
            timestamp=timestamp,
            node_anomalies=node_anomalies,
            link_anomalies=link_anomalies,
            classifications=classifications,
            link_classifications=link_classifications,
            root_causes=root_causes,
            explanations=explanations,
            has_anomaly=has_anomaly,
        )
        self._ticks.append(tick)
        if len(self._ticks) > self.max_ticks:
            self._ticks.pop(0)

        self._update_incident(tick_index, has_anomaly, node_anomalies, link_anomalies, root_causes)

    def _update_incident(self, tick_index, has_anomaly, node_anomalies, link_anomalies, root_causes):
        if has_anomaly and self._current_incident is None:
            self._current_incident = Incident(
                incident_id=self._next_incident_id,
                start_tick=tick_index,
                end_tick=None,
                peak_severity="none",
            )
            self._next_incident_id += 1

        if has_anomaly and self._current_incident is not None:
            worst = self._current_incident.peak_severity
            for r in node_anomalies + link_anomalies:
                if SEVERITY_RANK[r["severity"]] > SEVERITY_RANK[worst]:
                    worst = r["severity"]
            self._current_incident.peak_severity = worst
            for c in root_causes:
                if c["root_cause_id"] not in self._current_incident.root_cause_ids:
                    self._current_incident.root_cause_ids.append(c["root_cause_id"])
            self._current_incident.tick_count += 1

        elif not has_anomaly and self._current_incident is not None:
            self._current_incident.end_tick = tick_index - 1
            self._incidents.append(self._current_incident)
            self._current_incident = None

    def list_incidents(self) -> list:
        all_incidents = list(self._incidents)
        if self._current_incident is not None:
            all_incidents = all_incidents + [self._current_incident]
        return [i.to_dict() for i in all_incidents]

    def replay(self, incident_id: int) -> list:
        """Every recorded tick belonging to the given incident, in order
        (only what's still in the rolling window -- see class docstring)."""
        target = None
        for i in self._incidents:
            if i.incident_id == incident_id:
                target = i
                break
        if (
            target is None
            and self._current_incident is not None
            and self._current_incident.incident_id == incident_id
        ):
            target = self._current_incident

        if target is None:
            return []

        end = target.end_tick if target.end_tick is not None else self._tick_counter - 1
        return [t.to_dict() for t in self._ticks if target.start_tick <= t.tick_index <= end]