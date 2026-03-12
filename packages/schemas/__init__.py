"""Schema package exposing Pydantic models and registry utilities."""

from .models import (
    BinaryResponseEnum,
    ComfortResponse,
    CoreSymptomEvidence,
    EvaluatorDecision,
    MDECriterionA1,
    OverviewEvidence,
    PanicAttackEvidence,
    RiskAssessment,
    RiskTypeEnum,
    ScreeningResponse,
)
from .registry import SchemaRegistry

__all__ = [
    "SchemaRegistry",
    "OverviewEvidence",
    "ScreeningResponse",
    "CoreSymptomEvidence",
    "MDECriterionA1",
    "PanicAttackEvidence",
    "RiskAssessment",
    "RiskTypeEnum",
    "BinaryResponseEnum",
    "ComfortResponse",
    "EvaluatorDecision",
    "register_default_schemas",
]


def register_default_schemas(registry: SchemaRegistry) -> None:
    registry.register("overview_evidence", lambda: OverviewEvidence)
    registry.register("screening_response", lambda: ScreeningResponse)
    registry.register("core_symptom_evidence", lambda: CoreSymptomEvidence)
    registry.register("mde_criterion_a1", lambda: MDECriterionA1)
    registry.register("panic_attack_evidence", lambda: PanicAttackEvidence)
    registry.register("risk_assessment", lambda: RiskAssessment)
    registry.register("comfort_response", lambda: ComfortResponse)
    registry.register("evaluator_decision", lambda: EvaluatorDecision)
