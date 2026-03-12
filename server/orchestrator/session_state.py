from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AgendaItem:
    phase: str
    module: str | None
    item_id: str
    item_type: str
    schema_name: str
    requires: list[str]
    anchors: list[str]
    followups: dict[str, str]
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionState:
    session_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    current_phase: str | None = None
    current_module: str | None = None
    current_item_index: int = 0
    follow_up_attempts: dict[str, int] = field(default_factory=dict)
    pending_evidence: dict[str, dict[str, Any]] = field(default_factory=dict)
    activation_queue: list[str] = field(default_factory=list)
    evidence_ledger: dict[str, dict[str, Any]] = field(default_factory=dict)
    transcript: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    asked_fields: dict[str, set[str]] = field(default_factory=dict)
    schema_violation_counts: dict[str, int] = field(default_factory=dict)
    invalid_response_counts: dict[str, int] = field(default_factory=dict)
    stall_counts: dict[str, int] = field(default_factory=dict)
    repair_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    insufficient_evidence_items: set[str] = field(default_factory=set)
    phase_history: list[str] = field(default_factory=list)
    whodas_score: dict[str, Any] | None = None
    differential_result: dict[str, Any] | None = None
    clinical_significance: dict[str, Any] | None = None
    risk_resume_snapshot: dict[str, Any] | None = None
    trace_log: list[dict[str, Any]] = field(default_factory=list)

    def record_exchange(self, role: str, content: str) -> None:
        self.transcript.append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def increment_followup(self, item_id: str) -> int:
        count = self.follow_up_attempts.get(item_id, 0) + 1
        self.follow_up_attempts[item_id] = count
        return count

    def reset_followup(self, item_id: str) -> None:
        if item_id in self.follow_up_attempts:
            self.follow_up_attempts.pop(item_id)

    def increment_schema_violation(self, item_id: str) -> int:
        count = self.schema_violation_counts.get(item_id, 0) + 1
        self.schema_violation_counts[item_id] = count
        return count

    def increment_invalid_response(self, item_id: str) -> int:
        count = self.invalid_response_counts.get(item_id, 0) + 1
        self.invalid_response_counts[item_id] = count
        return count
