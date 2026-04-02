"""Tests for Pydantic v2 model contracts."""

import pytest
from pydantic import ValidationError

from src.models import (
    AgentResult,
    AdvocateChallenge,
    ApplicationPackage,
    Challenge,
    CompanyProfile,
    CoverLetter,
    ExecutionTrace,
    GapReport,
    JobAnalysis,
    MatchReport,
    Rebuttal,
    Skill,
    SkillGap,
    SkillMatch,
    TraceEntry,
)


class TestSkill:
    def test_valid_skill(self):
        s = Skill(name="Python", category="language", years_mentioned=5)
        assert s.name == "Python"
        assert s.category == "language"

    def test_invalid_category_rejected(self):
        with pytest.raises(ValidationError):
            Skill(name="Python", category="invalid_category")

    def test_years_optional(self):
        s = Skill(name="Docker", category="tool")
        assert s.years_mentioned is None


class TestSkillMatch:
    def test_valid_match(self):
        m = SkillMatch(
            skill=Skill(name="Python", category="language"),
            evidence="Used Python for 5 years",
            confidence=0.9,
        )
        assert m.confidence == 0.9


class TestGapReport:
    def test_valid_report(self, sample_gap_report):
        assert sample_gap_report.overall_match_score == 0.4
        assert sample_gap_report.recommendation == "apply-with-strategy"

    def test_score_too_high_rejected(self):
        with pytest.raises(ValidationError):
            GapReport(
                matched_skills=[],
                gaps=[],
                overall_match_score=1.5,
                recommendation="apply",
            )

    def test_score_too_low_rejected(self):
        with pytest.raises(ValidationError):
            GapReport(
                matched_skills=[],
                gaps=[],
                overall_match_score=-0.1,
                recommendation="apply",
            )

    def test_invalid_recommendation_rejected(self):
        with pytest.raises(ValidationError):
            GapReport(
                matched_skills=[],
                gaps=[],
                overall_match_score=0.5,
                recommendation="maybe",
            )


class TestCompanyProfile:
    def test_valid_profile(self, sample_company_profile):
        assert sample_company_profile.data_freshness == "training_data"

    def test_confidence_range(self):
        with pytest.raises(ValidationError):
            CompanyProfile(
                name="Test",
                culture_summary="Test",
                values=["test"],
                confidence=1.5,
            )


class TestAdvocateChallenge:
    def test_valid_challenge(self, sample_advocate_challenge):
        assert len(sample_advocate_challenge.challenges) >= 1
        assert sample_advocate_challenge.go_no_go == "apply-with-strategy"

    def test_score_range(self):
        with pytest.raises(ValidationError):
            AdvocateChallenge(
                challenges=[
                    Challenge(claim="test", argument="test", severity="high")
                ],
                rebuttals=[
                    Rebuttal(objection="test", response="test")
                ],
                adjusted_match_score=2.0,
                go_no_go="apply",
            )


class TestAgentResult:
    def test_success_result(self, sample_job_analysis):
        result = AgentResult[JobAnalysis](
            status="success",
            result=sample_job_analysis,
            retries_used=0,
            duration_s=2.1,
        )
        assert result.status == "success"
        assert result.result is not None
        assert result.result.title == "Senior Full Stack Java Engineer"

    def test_failed_result(self):
        result = AgentResult[JobAnalysis](
            status="failed",
            error="API timeout",
            retries_used=3,
            duration_s=90.0,
        )
        assert result.status == "failed"
        assert result.result is None
        assert result.error == "API timeout"

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            AgentResult[JobAnalysis](status="unknown", retries_used=0, duration_s=0)


class TestJobAnalysis:
    def test_valid_analysis(self, sample_job_analysis):
        assert sample_job_analysis.company == "LogiHire Pty Ltd"
        assert len(sample_job_analysis.required_skills) == 5

    def test_invalid_role_level(self):
        with pytest.raises(ValidationError):
            JobAnalysis(
                title="Test",
                company="Test",
                required_skills=[],
                role_level="intern",
                raw_text="test",
            )

    def test_empty_dealbreakers_default(self):
        ja = JobAnalysis(
            title="Test",
            company="Test",
            required_skills=[],
            role_level="junior",
            raw_text="test",
        )
        assert ja.dealbreakers == []


class TestRoundTrip:
    """Test JSON serialization/deserialization round-trips."""

    def test_job_analysis_round_trip(self, sample_job_analysis):
        json_str = sample_job_analysis.model_dump_json()
        restored = JobAnalysis.model_validate_json(json_str)
        assert restored.title == sample_job_analysis.title
        assert len(restored.required_skills) == len(sample_job_analysis.required_skills)

    def test_gap_report_round_trip(self, sample_gap_report):
        json_str = sample_gap_report.model_dump_json()
        restored = GapReport.model_validate_json(json_str)
        assert restored.overall_match_score == sample_gap_report.overall_match_score

    def test_agent_result_round_trip(self, sample_job_analysis):
        result = AgentResult[JobAnalysis](
            status="success",
            result=sample_job_analysis,
            retries_used=1,
            duration_s=3.5,
        )
        json_str = result.model_dump_json()
        restored = AgentResult[JobAnalysis].model_validate_json(json_str)
        assert restored.status == "success"
        assert restored.retries_used == 1
