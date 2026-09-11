from typing import List

from .models import NetworkActivitySnapshot
from .red_blue_models import RedTeamScenarioStep


def brute_force_then_breach_scenario(entity_id: str = "PC-99") -> List[RedTeamScenarioStep]:
    """
    A predefined, sandboxed sequence simulating a gradually escalating
    intrusion attempt: repeated failed logins, then a traffic spike and
    unauthorized communication once the attacker gets in.
    """
    return [
        RedTeamScenarioStep(
            label="baseline_normal_activity",
            snapshot=NetworkActivitySnapshot(
                entity_id=entity_id,
                traffic_volume_mbps=5.0,
                baseline_traffic_mbps=5.0,
                connection_count=3,
                baseline_connection_count=3,
                communicating_with=["SERVER-01"],
                authorized_peers=["SERVER-01"],
            ),
        ),
        RedTeamScenarioStep(
            label="repeated_failed_logins",
            snapshot=NetworkActivitySnapshot(
                entity_id=entity_id,
                traffic_volume_mbps=5.0,
                baseline_traffic_mbps=5.0,
                connection_count=3,
                baseline_connection_count=3,
                communicating_with=["SERVER-01"],
                authorized_peers=["SERVER-01"],
                failed_auth_attempts=5,
            ),
        ),
        RedTeamScenarioStep(
            label="unauthorized_peer_contact",
            snapshot=NetworkActivitySnapshot(
                entity_id=entity_id,
                traffic_volume_mbps=6.0,
                baseline_traffic_mbps=5.0,
                connection_count=4,
                baseline_connection_count=3,
                communicating_with=["SERVER-01", "UNKNOWN-HOST"],
                authorized_peers=["SERVER-01"],
                failed_auth_attempts=5,
            ),
        ),
        RedTeamScenarioStep(
            label="data_exfiltration_traffic_spike",
            snapshot=NetworkActivitySnapshot(
                entity_id=entity_id,
                traffic_volume_mbps=40.0,
                baseline_traffic_mbps=5.0,
                connection_count=10,
                baseline_connection_count=3,
                communicating_with=["SERVER-01", "UNKNOWN-HOST"],
                authorized_peers=["SERVER-01"],
                failed_auth_attempts=5,
                is_authorized_device=False,
            ),
        ),
    ]