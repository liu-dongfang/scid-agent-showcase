from __future__ import annotations

from typing import Any, Dict, List

from server.orchestrator.session_state import SessionState
from server.utils.logger import get_logger

logger = get_logger(__name__)


def run_differential(session: SessionState) -> Dict[str, Any]:
    """
    Generate a lightweight differential diagnosis summary based on collected evidence.
    The goal is not to replace a full ruleset but to provide a deterministic and auditable
    explanation for downstream reporting.
    """

    evidence = session.evidence_ledger
    candidates: List[str] = []
    explanation: List[str] = []
    logic: Dict[str, Any] = {}

    mood_evidence = evidence.get("CORE_MODULE_MOOD", {})
    bipolar_evidence = evidence.get("CORE_MODULE_BIPOLAR", {})
    anxiety_evidence = evidence.get("CORE_MODULE_ANXIETY", {})

    mood_positive = _positive_items(mood_evidence)
    if mood_positive:
        diagnosis = "Major Depressive Disorder（初步）"
        candidates.append(diagnosis)
        logic[diagnosis] = {
            "source_module": "CORE_MODULE_MOOD",
            "positive_items": mood_positive,
        }
        explanation.append("抑郁核心模块存在多个症状为阳性，提示重性抑郁发作。")

    mania_positive = _positive_items(bipolar_evidence)
    if mania_positive:
        diagnosis = "Bipolar Spectrum Disorder（待排）"
        candidates.append(diagnosis)
        logic[diagnosis] = {
            "source_module": "CORE_MODULE_BIPOLAR",
            "positive_items": mania_positive,
        }
        explanation.append("存在躁狂/轻躁狂相关症状，需要排查双相情感障碍。")

    anxiety_positive = _positive_items(anxiety_evidence)
    if anxiety_positive and "Generalised anxiety" not in candidates:
        diagnosis = "Anxiety Disorder（初步）"
        candidates.append(diagnosis)
        logic[diagnosis] = {
            "source_module": "CORE_MODULE_ANXIETY",
            "positive_items": anxiety_positive,
        }
        explanation.append("焦虑模块提示持续性担忧或惊恐相关症状。")

    if not candidates:
        explanation.append("当前证据不足以支持明确的诊断结论，建议补充核心模块访谈。")

    result = {
        "candidate_diagnoses": candidates,
        "dx_explanation": "；".join(explanation) if explanation else "",
        "differential_logic": logic,
    }
    if not candidates:
        result["status"] = "inconclusive"

    logger.info(
        "differential.result",
        session_id=session.session_id,
        candidates=candidates,
        status=result.get("status", "conclusive"),
    )
    return result


def _positive_items(module_evidence: Dict[str, Dict[str, Any]]) -> List[str]:
    positives: List[str] = []
    for item_id, payload in module_evidence.items():
        if isinstance(payload, dict) and payload.get("presence") is True:
            positives.append(item_id)
    return positives

