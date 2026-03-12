from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

"""Comorbidity appendix helpers that inspect collected evidence per cluster."""

from server.orchestrator.session_state import SessionState
from server.utils.logger import get_logger

logger = get_logger(__name__)


def load_comorbidity_config(path: Path) -> dict[str, Any]:
    """Read the JSON definition describing comorbidity clusters/thresholds."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def explore_comorbidity(session: SessionState, config: dict[str, Any]) -> dict[str, Any] | None:
    """Return appendix data when enough modules inside a cluster are positive."""
    clusters = config.get("clusters", [])
    findings: List[dict[str, Any]] = []
    evidence = session.evidence_ledger

    for cluster in clusters:
        modules = cluster.get("modules", [])
        threshold = cluster.get("threshold", len(modules))
        if not modules:
            continue

        positive_modules: List[dict[str, Any]] = []
        for module in modules:
            module_evidence = evidence.get(module, {})
            positives = [item for item, payload in module_evidence.items() if isinstance(payload, dict) and payload.get("presence")]
            if positives:
                positive_modules.append({"module": module, "positive_items": positives})

        if len(positive_modules) >= threshold:
            findings.append(
                {
                    "cluster": cluster.get("name", "comorbidity_cluster"),
                    "modules": positive_modules,
                    "notes": cluster.get("notes"),
                }
            )

    if not findings:
        logger.info("comorbidity.no_findings", session_id=session.session_id)
        return None

    result = {
        "generated_by": "comorbidity_appendix",
        "clusters": findings,
    }
    session.metadata["comorbidity_appendix"] = result
    return result
