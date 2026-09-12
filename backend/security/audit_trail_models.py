from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AuditEntry:
    """One immutable record of something the system did or decided."""
    entry_id: str
    timestamp: str
    source_module: str
    entity_id: str
    event_type: str
    details: Dict[str, Any] = field(default_factory=dict)