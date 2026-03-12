from __future__ import annotations

"""Helpers that consolidate session evidence into a compact replay summary."""

from typing import Any

from server.orchestrator.session_state import SessionState


def _screening_summary(screening: dict[str, Any]) -> list[dict[str, Any]]:
    summary = []
    for item_id, payload in screening.items():
        summary.append(
            {
                "item_id": item_id,
                "response": payload.get("binary_response"),
                "notes": payload.get("notes"),
            }
        )
    return summary


def _core_module_summary(evidence: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    modules: list[dict[str, Any]] = []
    for module, items in evidence.items():
        module_items = []
        for item_id, payload in items.items():
            module_items.append(
                {
                    "item_id": item_id,
                    "details": payload,
                    "positive": _is_positive(payload),
                }
            )
        modules.append({"module": module, "items": module_items})
    return modules


def _is_positive(payload: dict[str, Any]) -> bool:
    if payload.get("presence") is True:
        return True
    if payload.get("binary_response") in {"YES", "UNSURE"}:
        return True
    if isinstance(payload.get("symptom_count"), int) and payload["symptom_count"] > 0:
        return True
    return False


def _diagnostic_impression(core_modules: list[dict[str, Any]]) -> dict[str, Any]:
    impression: dict[str, Any] = {"positive": [], "negative": []}
    for module in core_modules:
        positives = [item for item in module["items"] if item["positive"]]
        if positives:
            impression["positive"].append({"module": module["module"], "items": positives})
        else:
            impression["negative"].append(module["module"])
    return impression


def build_report_from_session(session: SessionState) -> dict[str, Any]:
    evidence = session.evidence_ledger
    overview = evidence.get("Overview", {})
    screening = evidence.get("Screening", {})
    core_keys = [key for key in evidence if key.startswith("CORE_MODULE_")]
    core_evidence = {key: evidence[key] for key in core_keys}
    core_modules = _core_module_summary(core_evidence)

    return {
        "session_id": session.session_id,
        "created_at": session.created_at,
        "overview": overview,
        "screening_results": _screening_summary(screening),
        "core_modules": core_modules,
        "diagnostic_impression": _diagnostic_impression(core_modules),
        "phase_history": session.phase_history,
        "differential_result": session.differential_result,
        "clinical_significance": session.clinical_significance,
        "metadata": session.metadata,
        "transcript": session.transcript,
        "trace_log": session.trace_log,
    }
