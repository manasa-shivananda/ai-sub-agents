"""Shared fixtures for the test suite."""

import pytest

from src.models import (
    AdvocateChallenge,
    Challenge,
    CompanyProfile,
    CoverLetter,
    GapReport,
    JobAnalysis,
    Rebuttal,
    Skill,
    SkillGap,
    SkillMatch,
)


@pytest.fixture
def sample_jd_text() -> str:
    return (
        "Senior Full Stack Java Engineer at LogiHire Pty Ltd. "
        "5+ years of Java experience, AWS, Docker, Kubernetes in production. "
        "Messaging systems (Kafka), event-driven architecture, microservices. "
        "Frontend capability in React or TypeScript."
    )


@pytest.fixture
def sample_resume_text() -> str:
    return (
        "Full-stack developer with 3+ years experience. "
        "Python (5 years), JavaScript/TypeScript (3 years). "
        "Claude API, FastAPI, React, PostgreSQL, Docker. "
        "Basic GCP experience. Built 4 AI portfolio projects."
    )


@pytest.fixture
def sample_job_analysis() -> JobAnalysis:
    return JobAnalysis(
        title="Senior Full Stack Java Engineer",
        company="LogiHire Pty Ltd",
        required_skills=[
            Skill(name="Java", category="language", years_mentioned=5),
            Skill(name="AWS", category="tool"),
            Skill(name="Docker", category="tool"),
            Skill(name="Kubernetes", category="tool"),
            Skill(name="Kafka", category="framework"),
        ],
        nice_to_have_skills=[
            Skill(name="React", category="framework"),
            Skill(name="TypeScript", category="language"),
        ],
        years_experience=5,
        role_level="senior",
        red_flags=["Multiple hires may mean high churn"],
        dealbreakers=[],
        raw_text="Senior Full Stack Java Engineer...",
    )


@pytest.fixture
def sample_gap_report() -> GapReport:
    return GapReport(
        matched_skills=[
            SkillMatch(
                skill=Skill(name="Docker", category="tool"),
                evidence="Familiar with containerization (Docker)",
                confidence=0.7,
            ),
            SkillMatch(
                skill=Skill(name="React", category="framework"),
                evidence="Built React web applications",
                confidence=0.8,
            ),
        ],
        gaps=[
            SkillGap(
                skill=Skill(name="Java", category="language", years_mentioned=5),
                severity="critical",
                transferable="Python (5 years)",
            ),
            SkillGap(
                skill=Skill(name="AWS", category="tool"),
                severity="critical",
                transferable="Basic GCP experience",
            ),
            SkillGap(
                skill=Skill(name="Kafka", category="framework"),
                severity="moderate",
            ),
        ],
        overall_match_score=0.4,
        recommendation="apply-with-strategy",
    )


@pytest.fixture
def sample_company_profile() -> CompanyProfile:
    return CompanyProfile(
        name="LogiHire Pty Ltd",
        culture_summary="Fast-scaling logistics technology business.",
        values=["Engineering excellence", "Ownership", "Speed"],
        data_freshness="training_data",
        confidence=0.3,
    )


@pytest.fixture
def sample_advocate_challenge() -> AdvocateChallenge:
    return AdvocateChallenge(
        challenges=[
            Challenge(
                claim="Docker match at 0.7 confidence",
                argument="Familiarity is not production experience. The JD requires Docker in real production environments.",
                severity="medium",
            ),
        ],
        rebuttals=[
            Rebuttal(
                objection="You don't have Java experience",
                response="My 5 years of Python gives me strong OOP fundamentals that transfer directly to Java.",
            ),
        ],
        adjusted_match_score=0.35,
        go_no_go="apply-with-strategy",
    )


@pytest.fixture
def sample_cover_letter() -> CoverLetter:
    return CoverLetter(
        text="Dear Hiring Manager, I am excited about the Senior Full Stack Engineer role at LogiHire..." * 5,
        skills_referenced=["Docker", "React", "TypeScript"],
    )
