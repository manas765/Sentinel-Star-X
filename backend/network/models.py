"""
backend/network/models.py

Static topology/device registry for SENTINEL STAR-X.

This is the SLOW-CHANGING half of the network contract: it only changes when
a node/link is added, removed, or reconfigured (not every tick). Per-tick
dynamic metrics live in backend/telemetry/schema.py instead — keeping them
separate means we don't repeat IP/MAC/device_type on every single telemetry
snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DeviceType(str, Enum):
    PC = "pc"
    SERVER_DB = "server_db"
    SERVER_AUTH = "server_auth"
    SERVER_MONITORING = "server_monitoring"
    IOT = "iot"
    CRITICAL = "critical"
    GUEST = "guest"
    BACKUP = "backup"
    CENTRAL_SWITCH = "central_switch"
    BACKUP_SWITCH = "backup_switch"


@dataclass
class Device:
    node_id: str
    device_type: DeviceType
    ip_address: str
    mac_address: str
    priority: int  # 1 (lowest) - 5 (critical), used by Critical Path Protection (6.20)
    is_central: bool  # true only for the active central switch

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["device_type"] = self.device_type.value
        return d


@dataclass
class Link:
    link_id: str          # e.g. "central<->leaf-3", stable across ticks
    source_id: str
    target_id: str
    capacity_mbps: float  # provisioned max capacity, does NOT change per tick

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class Topology:
    """Full static snapshot of the network's shape. Emitted once, then only
    re-emitted (with a bumped version) when the network is reconfigured —
    e.g. add/remove node, create/remove link, backup switch promotion."""
    version: int
    devices: list  # list[Device]
    links: list    # list[Link]

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "devices": [d.to_dict() for d in self.devices],
            "links": [l.to_dict() for l in self.links],
        }
