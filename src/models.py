"""Typed contracts for inter-agent communication.

Every agent in the pipeline communicates through these Pydantic v2 models.
Literal types enforce valid values at parse time, catching bad LLM output immediately.
"""

from __future__ import annotations

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, field_validator

# --- Shared type aliases ---
Recommendation = Literal["apply", "skip", "apply-with-strategy"]
Severity = Literal["critical", "moderate", "minor"]
SkillCategory = Literal["language", "framework", "concept", "tool"]
RoleLevel = Literal["junior", "mid", "senior", "lead"]
AgentStatus = Literal["success", "failed", "degraded"]
ChallengeSeverity = Literal["high", "medium", "low"]
TraceStatus = Literal["dispatched", "success", "failed", "retry"]
DataFreshness = Literal["training_data", "web_search"]

T = TypeVar("T")


# --- Sub-models ---


class Skill(BaseModel):
    name: str
    category: SkillCategory
    years_mentioned: int | None = None


class SkillMatch(BaseModel):
    skill: Skill
    evidence: str
    confidence: float


class SkillGap(BaseModel):
    skill: Skill
    severity: Severity
    transferable: str | None = None


class Challenge(BaseModel):
    claim: str
    argument: str
    severity: ChallengeSeverity


class Rebuttal(BaseModel):
    objection: str
    response: str


# --- Observability models ---


class TraceEntry(BaseModel):
    timestamp_s: float
    source: str
    target: str
    tokens_in: int | None = None
    tokens_out: int | None = None
    status: TraceStatus
    cost_usd: float | None = None
    error: str | None = None


class ExecutionTrace(BaseModel):
    entries: list[TraceEntry]
    total_duration_s: float
    total_tokens: int
    total_cost_usd: float
    agents_succeeded: int
    agents_failed: int
    retries_used: int


# --- Agent result wrapper ---


class AgentResult(BaseModel, Generic[T]):
    """Wraps every agent's output with status, error info, and timing."""

    status: AgentStatus
    result: T | None = None
    error: str | None = None
    retries_used: int = 0
    duration_s: float = 0.0


# --- Top-level agent contracts ---


class JobAnalysis(BaseModel):
    title: str
    company: str
    required_skills: list[Skill]
    nice_to_have_skills: list[Skill] = []
    years_experience: int | None = None
    role_level: RoleLevel
    red_flags: list[str] = []
    dealbreakers: list[str] = []
    raw_text: str


class GapReport(BaseModel):
    matched_skills: list[SkillMatch]
    gaps: list[SkillGap]
    overall_match_score: float
    recommendation: Recommendation

    @field_validator("overall_match_score")
    @classmethod
    def score_in_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"overall_match_score must be 0.0-1.0, got {v}")
        return v


class CompanyProfile(BaseModel):
    name: str
    culture_summary: str
    values: list[str]
    recent_news: list[str] = []
    glassdoor_sentiment: str | None = None
    interview_tips: list[str] = []
    data_freshness: DataFreshness = "training_data"
    confidence: float = 0.5

    @field_validator("confidence")
    @classmethod
    def confidence_in_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence must be 0.0-1.0, got {v}")
        return v


class AdvocateChallenge(BaseModel):
    challenges: list[Challenge]
    rebuttals: list[Rebuttal]
    adjusted_match_score: float
    go_no_go: Recommendation

    @field_validator("adjusted_match_score")
    @classmethod
    def score_in_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"adjusted_match_score must be 0.0-1.0, got {v}")
        return v


class CoverLetter(BaseModel):
    text: str
    skills_referenced: list[str]


class MatchReport(BaseModel):
    overall_score: float
    matched_skills: list[SkillMatch]
    gaps: list[SkillGap]
    challenges: list[Challenge]
    recommendation: Recommendation


class ApplicationPackage(BaseModel):
    cover_letter: CoverLetter | None = None
    match_report: MatchReport
    application_strategy: str
    trace: ExecutionTrace
    company_profile: CompanyProfile | None = None
    advocate_challenge: AdvocateChallenge | None = None
