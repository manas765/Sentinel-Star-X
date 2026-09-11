from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List


@dataclass
class IncidentReportSection:
    heading: str
    content: str


@dataclass
class IncidentReport:
    report_id: str
    entity_id: str
    generated_at: str
    summary: str
    sections: List[IncidentReportSection] = field(default_factory=list)

    def to_text(self) -> str:
        lines = [f"INCIDENT REPORT — {self.report_id}", f"Entity: {self.entity_id}", f"Generated: {self.generated_at}", "", "SUMMARY", self.summary, ""]
        for section in self.sections:
            lines.append(section.heading.upper())
            lines.append(section.content)
            lines.append("")
        return "\n".join(lines)