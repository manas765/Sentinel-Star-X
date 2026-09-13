"""
backend/network/topology_morpher.py

Dynamic Topology Morphing (feature 6.24).

Per the doc: "The objective is not to permanently replace Star topology.
It is to temporarily adapt it when necessary and return to a stable state
after recovery." This tracks a morph "episode": apply a
TopologyChangeCandidate (creates real links on the NetworkSimulator),
record exactly what was added, then revert() removes precisely those
links to return to the original Star - nothing more, nothing less.

State machine (per the doc's diagram):
    STAR -> {BACKUP_STAR | HYBRID | PARTIAL_MESH} -> RECOVERY -> STAR
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from backend.network.simulator import NetworkSimulator
from backend.network.topology_recommender import ChangeType, TopologyChangeCandidate

_CHANGE_TYPE_TO_MORPH_STATE = {
    ChangeType.BACKUP_LINK: "BACKUP_STAR",
    ChangeType.BACKUP_SWITCH_ACTIVATION: "BACKUP_STAR",
    ChangeType.PARTIAL_MESH_LINK: "PARTIAL_MESH",
    ChangeType.HYBRID: "HYBRID",
}


class MorphState(str, Enum):
    STAR = "STAR"
    BACKUP_STAR = "BACKUP_STAR"
    HYBRID = "HYBRID"
    PARTIAL_MESH = "PARTIAL_MESH"
    RECOVERY = "RECOVERY"


@dataclass
class MorphEpisode:
    candidate: TopologyChangeCandidate
    added_link_ids: list = field(default_factory=list)
    state: MorphState = MorphState.STAR


class TopologyMorpher:
    def __init__(self, simulator: NetworkSimulator):
        self.sim = simulator
        self.state = MorphState.STAR
        self._active_episode: MorphEpisode | None = None

    def apply(self, candidate: TopologyChangeCandidate) -> MorphEpisode:
        if self._active_episode is not None:
            raise RuntimeError(
                "A morph episode is already active - revert() it before applying a new one. "
                "Stacking un-reverted changes defeats the point of 'temporary' adaptation."
            )

        added_link_ids = []
        for source_id, target_id in candidate.new_links:
            link_id = self.sim.create_link(source_id, target_id)
            added_link_ids.append(link_id)

        new_state = MorphState(_CHANGE_TYPE_TO_MORPH_STATE.get(candidate.change_type, "HYBRID"))
        self.state = new_state
        self._active_episode = MorphEpisode(
            candidate=candidate, added_link_ids=added_link_ids, state=new_state,
        )
        return self._active_episode

    def begin_recovery(self):
        """Mark that the incident is being verified/resolved, before
        actually tearing the temporary links back down. Separate step so
        the recovery-verification module (6.28) can confirm health first."""
        if self._active_episode is None:
            raise RuntimeError("No active morph episode to recover from.")
        self.state = MorphState.RECOVERY

    def revert(self):
        """Remove exactly the links this episode added, and only those -
        never touches links the network already had, or ones added by a
        different episode."""
        if self._active_episode is None:
            raise RuntimeError("No active morph episode to revert.")

        for link_id in self._active_episode.added_link_ids:
            if link_id in self.sim.links:
                self.sim.remove_link(link_id)

        self._active_episode = None
        self.state = MorphState.STAR

    @property
    def active_episode(self) -> MorphEpisode | None:
        return self._active_episode
