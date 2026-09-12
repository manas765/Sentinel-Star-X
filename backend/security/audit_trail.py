from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .audit_trail_models import AuditEntry

_entry_counter = 0


def _next_entry_id() -> str:
    global _entry_counter
    _entry_counter += 1
    return f"AUDIT-{_entry_counter:06d}"


class AuditTrail:
    """
    Append-only, chronological record of everything the autonomous system
    does or decides — trust changes, threat escalations, survival mode
    transitions, recovery gate decisions, and more. Entries are never
    edited or removed, so the full decision history can always be
    reconstructed and explained.
    """

    def __init__(self) -> None:
        self._entries: List[AuditEntry] = []

    def record(
        self,
        source_module: str,
        entity_id: str,
        event_type: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            entry_id=_next_entry_id(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            source_module=source_module,
            entity_id=entity_id,
            event_type=event_type,
            details=details or {},
        )
        self._entries.append(entry)
        return entry

    def all_entries(self) -> List[AuditEntry]:
        return list(self._entries)

    def for_entity(self, entity_id: str) -> List[AuditEntry]:
        return [e for e in self._entries if e.entity_id == entity_id]

    def for_module(self, source_module: str) -> List[AuditEntry]:
        return [e for e in self._entries if e.source_module == source_module]

    def for_event_type(self, event_type: str) -> List[AuditEntry]:
        return [e for e in self._entries if e.event_type == event_type]

    def reconstruct_timeline(self, entity_id: str) -> str:
        """Human-readable, chronological reconstruction of everything recorded for one entity."""
        entries = self.for_entity(entity_id)
        if not entries:
            return f"No audit entries found for '{entity_id}'."
        lines = [f"AUDIT TIMELINE — {entity_id}", ""]
        for e in entries:
            detail_text = ", ".join(f"{k}={v}" for k, v in e.details.items())
            lines.append(f"[{e.timestamp}] ({e.source_module}) {e.event_type}" + (f" — {detail_text}" if detail_text else ""))
        return "\n".join(lines)