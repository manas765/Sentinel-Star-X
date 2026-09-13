"""
backend/network/config_versioning.py

Configuration Versioning (feature 6.47).

Maintains an append-only history of topology configurations: what changed,
when, why, tied to which incident (if any), and who/what made the change
(a human via the dashboard, or the system autonomously via Topology
Morphing). This is intentionally decoupled from NetworkSimulator itself -
call record() explicitly at the moments that matter (morph apply/revert,
manual topology edits) rather than snapshotting every tick, since most
ticks have no configuration change at all.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class ConfigVersion:
    version: int
    timestamp: float
    topology_version: int   # cross-reference to network/models.py Topology.version
    change_description: str
    reason: str
    incident_id: str | None
    author: str              # e.g. "system:topology_morpher" or "user:akshata"
    devices_snapshot: list = field(default_factory=list)
    links_snapshot: list = field(default_factory=list)


class ConfigVersionStore:
    def __init__(self):
        self._history: list = []
        self._next_version = 1

    def record(
        self,
        topology: dict,
        change_description: str,
        reason: str,
        author: str,
        incident_id: str | None = None,
    ) -> ConfigVersion:
        entry = ConfigVersion(
            version=self._next_version,
            timestamp=time.time(),
            topology_version=topology["version"],
            change_description=change_description,
            reason=reason,
            incident_id=incident_id,
            author=author,
            devices_snapshot=topology["devices"],
            links_snapshot=topology["links"],
        )
        self._history.append(entry)
        self._next_version += 1
        return entry

    def get_history(self) -> list:
        return list(self._history)

    def get_version(self, version: int) -> ConfigVersion | None:
        for entry in self._history:
            if entry.version == version:
                return entry
        return None

    def latest(self) -> ConfigVersion | None:
        return self._history[-1] if self._history else None

    def diff(self, version_a: int, version_b: int) -> dict:
        """Simple set-diff of device IDs and link IDs between two versions."""
        a, b = self.get_version(version_a), self.get_version(version_b)
        if a is None or b is None:
            return {"error": "one or both versions not found"}

        devices_a = {d["node_id"] for d in a.devices_snapshot}
        devices_b = {d["node_id"] for d in b.devices_snapshot}
        links_a = {l["link_id"] for l in a.links_snapshot}
        links_b = {l["link_id"] for l in b.links_snapshot}

        return {
            "devices_added": sorted(devices_b - devices_a),
            "devices_removed": sorted(devices_a - devices_b),
            "links_added": sorted(links_b - links_a),
            "links_removed": sorted(links_a - links_b),
        }
