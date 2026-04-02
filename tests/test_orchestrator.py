"""Tests for the orchestrator state machine and pipeline logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.models import (
    AgentResult,
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
from src.orchestrator import (
    _build_match_report,
    _build_strategy,
    run_pipeline,
)
from src.tracer import Tracer


def _success(result):
    """Wrap a model in a successful AgentResult."""
    return AgentResult(status="success", result=result, retries_used=0, duration_s=1.0)


def _failed(error="Agent failed"):
    """Create a failed AgentResult."""
    return AgentResult(status="failed", error=error, retries_used=3, duration_s=5.0)


class TestBuildMatchReport:
    def test_without_advocate(self, sample_gap_report):
        report = _build_match_report(sample_gap_report, None)
        assert report.overall_score == sample_gap_report.overall_match_score
        assert report.recommendation == sample_gap_report.recommendation
        assert report.challenges == []

    def test_with_advocate(self, sample_gap_report, sample_advocate_challenge):
        report = _build_match_report(sample_gap_report, sample_advocate_challenge)
        assert report.overall_score == sample_advocate_challenge.adjusted_match_score
        assert report.recommendation == sample_advocate_challenge.go_no_go
        assert len(report.challenges) == 1


class TestBuildStrategy:
    def test_apply_recommendation(self):
        gap = GapReport(
            matched_skills=[
                SkillMatch(
                    skill=Skill(name="Python", category="language"),
                    evidence="5 years",
                    confidence=0.9,
                )
            ],
            gaps=[],
            overall_match_score=0.8,
            recommendation="apply",
        )
        strategy = _build_strategy(gap, None, None)
        assert "Apply. Strong match" in strategy

    def test_skip_recommendation(self):
        gap = GapReport(
            matched_skills=[],
            gaps=[
                SkillGap(
                    skill=Skill(name="Java", category="language"),
                    severity="critical",
                )
            ],
            overall_match_score=0.2,
            recommendation="skip",
        )
        strategy = _build_strategy(gap, None, None)
        assert "Skip this role" in strategy

    def test_low_confidence_company_warning(self, sample_gap_report):
        company = CompanyProfile(
            name="Unknown Co",
            culture_summary="Unknown",
            values=["test"],
            confidence=0.2,
            data_freshness="training_data",
        )
        strategy = _build_strategy(sample_gap_report, None, company)
        assert "low confidence" in strategy


class TestRunPipeline:
    @pytest.mark.asyncio
    async def test_short_circuit_on_dealbreakers(self):
        """Pipeline should exit early if dealbreakers found."""
        job_analysis = JobAnalysis(
            title="Test",
            company="Test",
            required_skills=[Skill(name="Go", category="language")],
            role_level="senior",
            dealbreakers=["Security clearance required"],
            raw_text="test",
        )

        with (
            patch("src.orchestrator.JobAnalyzer") as MockJA,
        ):
            mock_ja = MockJA.return_value
            mock_ja.run = AsyncMock(return_value=_success(job_analysis))

            tracer = Tracer()
            package = await run_pipeline("test jd", "test resume", tracer)

        assert package.match_report.recommendation == "skip"
        assert "Dealbreakers" in package.application_strategy

    @pytest.mark.asyncio
    async def test_company_researcher_degradation(self):
        """Pipeline should continue if company_researcher fails."""
        job_analysis = JobAnalysis(
            title="Test",
            company="Test",
            required_skills=[Skill(name="Python", category="language")],
            role_level="senior",
            raw_text="test",
        )
        gap_report = GapReport(
            matched_skills=[
                SkillMatch(
                    skill=Skill(name="Python", category="language"),
                    evidence="5 years",
                    confidence=0.9,
                )
            ],
            gaps=[],
            overall_match_score=0.8,
            recommendation="apply",
        )
        advocate = AdvocateChallenge(
            challenges=[
                Challenge(claim="Test", argument="Test argument", severity="low")
            ],
            rebuttals=[Rebuttal(objection="Test", response="Test")],
            adjusted_match_score=0.75,
            go_no_go="apply",
        )
        letter = CoverLetter(
            text="Dear Hiring Manager, " * 50,
            skills_referenced=["Python", "AI"],
        )

        with (
            patch("src.orchestrator.JobAnalyzer") as MockJA,
            patch("src.orchestrator.GapAnalyzer") as MockGA,
            patch("src.orchestrator.CompanyResearcher") as MockCR,
            patch("src.orchestrator.DevilsAdvocate") as MockDA,
            patch("src.orchestrator.LetterWriter") as MockLW,
        ):
            MockJA.return_value.run = AsyncMock(return_value=_success(job_analysis))
            MockGA.return_value.run = AsyncMock(return_value=_success(gap_report))
            MockCR.return_value.run = AsyncMock(return_value=_failed("Company not found"))
            MockDA.return_value.run = AsyncMock(return_value=_success(advocate))
            MockLW.return_value.run = AsyncMock(return_value=_success(letter))

            tracer = Tracer()
            package = await run_pipeline("test jd", "test resume", tracer)

        assert package.company_profile is None
        assert package.match_report.recommendation == "apply"
        assert package.cover_letter is not None

    @pytest.mark.asyncio
    async def test_job_analysis_failure_aborts(self):
        """Pipeline should abort if job_analyzer fails."""
        with patch("src.orchestrator.JobAnalyzer") as MockJA:
            MockJA.return_value.run = AsyncMock(return_value=_failed("Parse error"))

            tracer = Tracer()
            package = await run_pipeline("bad jd", "test resume", tracer)

        assert package.match_report.recommendation == "skip"
        assert "failed" in package.application_strategy.lower()
