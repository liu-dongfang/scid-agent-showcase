"""Centralised Pydantic models backing LLM structured outputs."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, conint


class BinaryResponseEnum(str, Enum):
    YES = "YES"
    NO = "NO"
    UNSURE = "UNSURE"


class OverviewEvidence(BaseModel):
    """Schema for overview stage evidence collection."""

    presenting_problem: Optional[str] = Field(
        default=None,
        description="Primary reason for visit captured verbatim when possible.",
        min_length=1,
    )
    onset_and_context: Optional[str] = Field(
        default=None,
        description="Narrative describing when the issue started and precipitating context.",
        min_length=1,
    )
    prior_history: Optional[str] = Field(
        None,
        description="Previous treatment or relevant history if explicitly mentioned.",
        min_length=1,
    )
    suicide_history: Optional[str] = Field(
        None,
        description="Historical reference to self-harm or suicidal ideation if acknowledged.",
        min_length=1,
    )
    recent_suicidal_thoughts: Optional[bool] = Field(
        None,
        description="Whether participant reported suicidal thoughts within the last week.",
    )
    substance_use_summary: Optional[str] = Field(
        None,
        description="Summary of substance or alcohol use noted during overview.",
    )
    medication_history: Optional[str] = Field(
        None,
        description="Prior medication usage or hospitalisation details if provided.",
    )


class ScreeningResponse(BaseModel):
    """Binary screening response captured during screening phase."""

    binary_response: BinaryResponseEnum = Field(
        ...,
        description="One of YES/NO/UNSURE values representing participant selection.",
    )
    notes: Optional[str] = Field(
        None,
        description="Optional clarifying short note mirrored from user when provided.",
    )


class FrequencyEnum(str, Enum):
    ALMOST_DAILY = "almost_daily"
    SEVERAL_TIMES_WEEK = "several_times_week"
    OCCASIONAL = "occasional"
    RARE = "rare"


class ImpairmentDomainEnum(str, Enum):
    WORK = "work"
    SOCIAL = "social"
    SELF_CARE = "self_care"
    FAMILY = "family"
    EDUCATION = "education"


class CoreSymptomEvidence(BaseModel):
    """Generic schema for DSM core symptom evidence with severity details."""

    presence: bool = Field(..., description="Whether the symptom is present in the target window.")
    duration_weeks: Optional[conint(ge=0)] = Field(
        None, description="Duration of the symptom in weeks. Include 0 if less than one week."
    )
    frequency: Optional[FrequencyEnum] = Field(
        None,
        description="Approximate frequency categorisation in the observation period.",
    )
    impairment_domains: Optional[list[ImpairmentDomainEnum]] = Field(
        default=None,
        description="Functional domains impaired due to the symptom. Empty or null if none.",
    )
    source_snippet: Optional[str] = Field(
        None,
        description="Verbatim snippet supporting the extraction for audit trail.",
    )


class PanicAttackEvidence(BaseModel):
    """Schema capturing panic attack characteristics."""

    unexpected_onset: bool = Field(..., description="Whether the episode onset felt unexpected.")
    peak_in_minutes: bool = Field(..., description="Symptom intensity reached peak within minutes.")
    symptom_count: conint(ge=0, le=13) = Field(
        ..., description="Number of simultaneous DSM panic symptoms the user mentioned."
    )
    avoidance_behavior: Optional[bool] = Field(
        None,
        description="Whether participant avoided situations due to fear of future attacks.",
    )
    impairment_domains: Optional[list[ImpairmentDomainEnum]] = Field(
        default=None, description="Functional impact domains relevant to panic episodes."
    )
    source_snippet: Optional[str] = Field(
        None, description="Direct participant quote supporting the extraction."
    )


class RiskTypeEnum(str, Enum):
    SUICIDAL_IDEATION = "suicidal_ideation"
    SUICIDAL_PLAN = "suicidal_plan"
    SELF_HARM = "self_harm"
    HOPELESSNESS = "hopelessness"
    NONE = "none"


class RiskAssessment(BaseModel):
    """Risk monitor LLM confirmation schema."""

    risk_detected: bool = Field(..., description="Whether any risk signal is present.")
    risk_type: RiskTypeEnum = Field(
        ...,
        description="Most severe detected risk type according to configured priority.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score assigned by the reviewer model.",
    )
    evidence: str = Field(
        ...,
        min_length=1,
        description="Verbatim evidence snippet supporting the risk assessment.",
    )
    clinical_reasoning: Optional[str] = Field(
        None,
        description="Brief clinical reasoning process (1-2 sentences) explaining the assessment.",
    )


class ComfortResponse(BaseModel):
    """Structured payload for de-escalation prompts."""

    message: str = Field(..., min_length=5, description="Comforting message to send to the user.")


class CriterionFitness(BaseModel):
    """Fitness sub-score for a single criterion."""

    covered: Optional[bool | str] = Field(
        None,
        description="Whether the criterion has been covered (bool) or partial/uncertain (string).",
    )
    quality: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Quality/confidence of evidence for this criterion (0-1).",
    )
    evidence: Optional[str] = Field(
        None,
        description="Optional short evidence note.",
    )


class FitnessScore(BaseModel):
    """Aggregate fitness score across required criteria."""

    by_criterion: Dict[str, CriterionFitness] = Field(
        default_factory=dict,
        description="Per-criterion coverage/quality map.",
    )
    overall: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Weighted overall fitness score (0-1).",
    )


class EvaluatorDecision(BaseModel):
    """Schema for Evaluator/Decision agent output (fitness-driven)."""

    fitness: FitnessScore = Field(..., description="Coverage/quality scores.")
    missing_info_hints: list[str] = Field(
        default_factory=list,
        description="Natural language hints of missing information (≤2 preferred).",
    )
    style_guidelines: list[str] = Field(
        default_factory=list,
        description="MI/TIC style reminders to inject into interviewer prompt.",
    )

    decision: Literal["move_on", "follow_up"] = Field(
        ..., description="Next-step instruction for the orchestrator."
    )
    reason: str = Field(
        ...,
        min_length=2,
        description="One-sentence rationale for the decision.",
    )
    error_flag: bool = Field(False, description="True when evaluator parsing is uncertain or schema deviated.")
    safety_hint: Optional[str] = Field(
        None, description="Safety escalation hint when risk is detected."
    )
    error_notes: Optional[list[str]] = Field(
        default=None,
        description="Optional parser/model error notes for observability.",
    )


class MDECriterionA1(CoreSymptomEvidence):
    """Symptom schema specifically for Major Depressive Episode criterion A1 (depressed mood)."""

    symptom_code: Literal["MDE_A1"] = Field(
        "MDE_A1",
        description="Fixed identifier referencing DSM-5 A1 criterion for depressed mood.",
    )
