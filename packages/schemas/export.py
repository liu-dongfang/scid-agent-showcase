"""Utilities for exporting Pydantic schema definitions to JSON files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Tuple

from jsonschema import Draft202012Validator

from packages.schemas import (
    ComfortResponse,
    CoreSymptomEvidence,
    EvaluatorDecision,
    MDECriterionA1,
    OverviewEvidence,
    PanicAttackEvidence,
    RiskAssessment,
    ScreeningResponse,
)

ROOT_DIR = Path(__file__).resolve().parents[2]
SCHEMA_OUTPUT_DIR = ROOT_DIR / "configs" / "schemas"


def _model_map() -> Dict[str, Any]:
    return {
        "overview_evidence": OverviewEvidence,
        "screening_response": ScreeningResponse,
        "core_symptom_evidence": CoreSymptomEvidence,
        "mde_criterion_a1": MDECriterionA1,
        "panic_attack_evidence": PanicAttackEvidence,
        "risk_assessment": RiskAssessment,
        "comfort_response": ComfortResponse,
        "evaluator_decision": EvaluatorDecision,
    }


def _sample_payloads() -> Dict[str, Dict[str, Any]]:
    return {
        "overview_evidence": {
            "presenting_problem": "Difficulty sleeping and reduced motivation.",
            "onset_and_context": "Symptoms started about five weeks ago after a major deadline.",
        },
        "screening_response": {
            "binary_response": "YES",
        },
        "mde_criterion_a1": {
            "presence": True,
            "duration_weeks": 4,
            "frequency": "almost_daily",
            "impairment_domains": ["work"],
            "source_snippet": "I feel flat almost every day at work.",
        },
        "core_symptom_evidence": {
            "presence": True,
            "duration_weeks": 2,
            "frequency": "several_times_week",
            "impairment_domains": ["social"],
            "source_snippet": "I keep skipping plans with friends.",
        },
        "panic_attack_evidence": {
            "unexpected_onset": True,
            "peak_in_minutes": True,
            "symptom_count": 4,
            "avoidance_behavior": False,
            "impairment_domains": ["family"],
            "source_snippet": "My chest tightened and I had to leave the room.",
        },
        "risk_assessment": {
            "risk_detected": False,
            "risk_type": "none",
            "confidence": 0.1,
            "evidence": "No acute safety language detected in the sample.",
        },
        "comfort_response": {
            "message": "Thanks for explaining that. We can go one step at a time.",
        },
        "evaluator_decision": {
            "fitness": {
                "overall": 0.82,
                "by_criterion": {
                    "presenting_problem": {"covered": True, "quality": 0.9},
                    "onset_and_context": {"covered": True, "quality": 0.75},
                },
            },
            "missing_info_hints": ["Clarify whether sleep disruption is nightly."],
            "style_guidelines": ["Use short, neutral follow-up wording."],
            "decision": "move_on",
            "reason": "The core overview fields are sufficiently covered in the sample.",
        },
    }


def render_schemas() -> Dict[str, Dict[str, Any]]:
    return {name: model.model_json_schema() for name, model in _model_map().items()}


def validate_schema_payloads(schemas: Dict[str, Dict[str, Any]]) -> None:
    samples = _sample_payloads()
    for name, schema in schemas.items():
        Draft202012Validator.check_schema(schema)
        model = _model_map()[name]
        model.model_validate(samples[name])


def write_schemas(schemas: Dict[str, Dict[str, Any]]) -> None:
    SCHEMA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, schema in schemas.items():
        output_path = SCHEMA_OUTPUT_DIR / f"{name}.json"
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(schema, handle, indent=2, ensure_ascii=False)


def compare_schemas(schemas: Dict[str, Dict[str, Any]]) -> Tuple[bool, list[str]]:
    mismatches: list[str] = []
    for name, schema in schemas.items():
        path = SCHEMA_OUTPUT_DIR / f"{name}.json"
        if not path.exists():
            mismatches.append(name)
            continue

        with path.open("r", encoding="utf-8") as handle:
            current = json.load(handle)
        if current != schema:
            mismatches.append(name)
    return len(mismatches) == 0, mismatches


def main() -> None:
    parser = argparse.ArgumentParser(description="Export JSON schema definitions")
    parser.add_argument("--check", action="store_true", help="Check for drift without writing files")
    args = parser.parse_args()

    schemas = render_schemas()
    validate_schema_payloads(schemas)

    if args.check:
        ok, mismatches = compare_schemas(schemas)
        if not ok:
            mismatches_text = ", ".join(mismatches)
            raise SystemExit(f"Schema drift detected for: {mismatches_text}. Run without --check to export.")
        return

    write_schemas(schemas)
    print(f"Exported {len(schemas)} schemas to {SCHEMA_OUTPUT_DIR}")


if __name__ == "__main__":
    main()
