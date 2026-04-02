"""Pipeline orchestrator -- coordinates all agents through a state machine.

Pure Python. No LLM calls. Deterministic state transitions.
Handles parallel execution, graceful degradation, and short-circuit on dealbreakers.

State machine:
  ANALYZE -> SHORT_CIRCUIT_CHECK -> PARALLEL_RESEARCH -> ADVOCATE -> WRITE -> COMPILE
"""

from __future__ import annotations

import asyncio
import json
from enum import Enum

from src.agents.company_researcher import CompanyResearcher
from src.agents.devils_advocate import DevilsAdvocate
from src.agents.gap_analyzer import GapAnalyzer
from src.agents.job_analyzer import JobAnalyzer
from src.agents.letter_writer import LetterWriter
from src.models import (
    AgentResult,
    ApplicationPackage,
    AdvocateChallenge,
    CompanyProfile,
    CoverLetter,
    GapReport,
    JobAnalysis,
    MatchReport,
)
from src.tracer import Tracer


class PipelineState(Enum):
    ANALYZE = "analyze"
    SHORT_CIRCUIT_CHECK = "short_circuit_check"
    PARALLEL_RESEARCH = "parallel_research"
    ADVOCATE = "advocate"
    WRITE = "write"
    COMPILE = "compile"


async def run_pipeline(
    job_text: str,
    resume_text: str,
    tracer: Tracer | None = None,
) -> ApplicationPackage:
    """Run the full agent pipeline and return an ApplicationPackage."""
    if tracer is None:
        tracer = Tracer()

    # Initialize agents
    job_analyzer = JobAnalyzer()
    gap_analyzer = GapAnalyzer()
    company_researcher = CompanyResearcher()
    devils_advocate = DevilsAdvocate()
    letter_writer = LetterWriter()

    # --- ANALYZE ---
    tracer.record_dispatch("job_analyzer")
    job_result: AgentResult[JobAnalysis] = await job_analyzer.run(job_text, tracer)

    if job_result.status != "success" or job_result.result is None:
        return _compile_early_exit(
            tracer, error=f"Job analysis failed: {job_result.error}"
        )

    job_analysis = job_result.result

    # --- SHORT_CIRCUIT_CHECK ---
    if job_analysis.dealbreakers:
        return _compile_early_exit(
            tracer,
            job_analysis=job_analysis,
            error=f"Dealbreakers found: {', '.join(job_analysis.dealbreakers)}",
        )

    # --- PARALLEL_RESEARCH ---
    gap_input = _build_gap_input(job_analysis, resume_text)
    company_input = job_analysis.company

    tracer.record_dispatch("gap_analyzer")
    tracer.record_dispatch("company_researcher")

    gap_task = gap_analyzer.run(gap_input, tracer)
    company_task = company_researcher.run(company_input, tracer)

    results = await asyncio.gather(gap_task, company_task, return_exceptions=True)

    # Process gap_analyzer result
    if isinstance(results[0], Exception):
        return _compile_early_exit(
            tracer,
            job_analysis=job_analysis,
            error=f"Gap analysis failed: {results[0]}",
        )
    gap_result: AgentResult[GapReport] = results[0]

    if gap_result.status != "success" or gap_result.result is None:
        return _compile_early_exit(
            tracer,
            job_analysis=job_analysis,
            error=f"Gap analysis failed: {gap_result.error}",
        )

    gap_report = gap_result.result

    # Process company_researcher result (graceful degradation)
    company_profile: CompanyProfile | None = None
    if isinstance(results[1], Exception):
        tracer.record_failure("company_researcher", str(results[1]), 0)
    else:
        company_result: AgentResult[CompanyProfile] = results[1]
        if company_result.status == "success" and company_result.result is not None:
            company_profile = company_result.result

    # --- ADVOCATE ---
    advocate_challenge: AdvocateChallenge | None = None
    advocate_input = _build_advocate_input(job_analysis, gap_report, company_profile)

    tracer.record_dispatch("devils_advocate")
    advocate_result: AgentResult[AdvocateChallenge] = await devils_advocate.run(
        advocate_input, tracer
    )

    if advocate_result.status == "success" and advocate_result.result is not None:
        advocate_challenge = advocate_result.result

    # --- WRITE ---
    letter: CoverLetter | None = None
    letter_input = _build_letter_input(
        job_analysis, gap_report, company_profile, advocate_challenge
    )

    tracer.record_dispatch("letter_writer")
    letter_result: AgentResult[CoverLetter] = await letter_writer.run(
        letter_input, tracer
    )

    if letter_result.status == "success" and letter_result.result is not None:
        letter = letter_result.result

    # --- COMPILE ---
    match_report = _build_match_report(gap_report, advocate_challenge)
    strategy = _build_strategy(gap_report, advocate_challenge, company_profile)

    return ApplicationPackage(
        cover_letter=letter,
        match_report=match_report,
        application_strategy=strategy,
        trace=tracer.build_trace(),
        company_profile=company_profile,
        advocate_challenge=advocate_challenge,
    )


def _compile_early_exit(
    tracer: Tracer,
    job_analysis: JobAnalysis | None = None,
    error: str = "Pipeline failed",
) -> ApplicationPackage:
    """Build a minimal ApplicationPackage for early exits."""
    from src.models import MatchReport

    match_report = MatchReport(
        overall_score=0.0,
        matched_skills=[],
        gaps=[],
        challenges=[],
        recommendation="skip",
    )

    return ApplicationPackage(
        match_report=match_report,
        application_strategy=f"NOT RECOMMENDED: {error}",
        trace=tracer.build_trace(),
    )


def _build_gap_input(job_analysis: JobAnalysis, resume_text: str) -> str:
    """Construct input text for the gap analyzer."""
    ja_json = job_analysis.model_dump_json(indent=2)
    return (
        f"## Job Analysis\n{ja_json}\n\n"
        f"## Candidate Resume\n{resume_text}"
    )


def _build_advocate_input(
    job_analysis: JobAnalysis,
    gap_report: GapReport,
    company_profile: CompanyProfile | None,
) -> str:
    """Construct input text for the devil's advocate."""
    parts = [
        f"## Job Analysis\n{job_analysis.model_dump_json(indent=2)}",
        f"## Gap Report\n{gap_report.model_dump_json(indent=2)}",
    ]
    if company_profile:
        parts.append(f"## Company Profile\n{company_profile.model_dump_json(indent=2)}")
    else:
        parts.append("## Company Profile\nCompany research was unavailable.")
    return "\n\n".join(parts)


def _build_letter_input(
    job_analysis: JobAnalysis,
    gap_report: GapReport,
    company_profile: CompanyProfile | None,
    advocate_challenge: AdvocateChallenge | None,
) -> str:
    """Construct input text for the letter writer."""
    parts = [
        f"## Job Analysis\n{job_analysis.model_dump_json(indent=2)}",
        f"## Gap Report\n{gap_report.model_dump_json(indent=2)}",
    ]
    if company_profile:
        parts.append(f"## Company Profile\n{company_profile.model_dump_json(indent=2)}")
    else:
        parts.append(
            "## Company Profile\nCompany research was unavailable. "
            "Focus the cover letter on skills match only."
        )
    if advocate_challenge:
        parts.append(
            f"## Devil's Advocate Challenges\n{advocate_challenge.model_dump_json(indent=2)}"
        )
    else:
        parts.append("## Devil's Advocate Challenges\nNo challenges available.")
    return "\n\n".join(parts)


def _build_match_report(
    gap_report: GapReport,
    advocate_challenge: AdvocateChallenge | None,
) -> MatchReport:
    """Assemble the final match report from gap analysis and advocate challenge."""
    score = gap_report.overall_match_score
    recommendation = gap_report.recommendation
    challenges = []

    if advocate_challenge:
        score = advocate_challenge.adjusted_match_score
        recommendation = advocate_challenge.go_no_go
        challenges = advocate_challenge.challenges

    return MatchReport(
        overall_score=score,
        matched_skills=gap_report.matched_skills,
        gaps=gap_report.gaps,
        challenges=challenges,
        recommendation=recommendation,
    )


def _build_strategy(
    gap_report: GapReport,
    advocate_challenge: AdvocateChallenge | None,
    company_profile: CompanyProfile | None,
) -> str:
    """Build a plain-text application strategy summary."""
    parts = []

    recommendation = gap_report.recommendation
    if advocate_challenge:
        recommendation = advocate_challenge.go_no_go

    if recommendation == "apply":
        parts.append("RECOMMENDATION: Apply. Strong match overall.")
    elif recommendation == "apply-with-strategy":
        parts.append("RECOMMENDATION: Apply with strategy. Address gaps proactively.")
    else:
        parts.append("RECOMMENDATION: Skip this role. Poor match.")

    # Top strengths
    top_matches = sorted(
        gap_report.matched_skills, key=lambda m: m.confidence, reverse=True
    )[:3]
    if top_matches:
        parts.append("\nKEY STRENGTHS:")
        for m in top_matches:
            parts.append(f"  - {m.skill.name} (confidence: {m.confidence:.0%})")

    # Critical gaps
    critical_gaps = [g for g in gap_report.gaps if g.severity == "critical"]
    if critical_gaps:
        parts.append("\nCRITICAL GAPS TO ADDRESS:")
        for g in critical_gaps:
            transferable = f" (transferable: {g.transferable})" if g.transferable else ""
            parts.append(f"  - {g.skill.name}{transferable}")

    # Advocate warnings
    if advocate_challenge:
        high_severity = [c for c in advocate_challenge.challenges if c.severity == "high"]
        if high_severity:
            parts.append("\nHIGH-SEVERITY CONCERNS:")
            for c in high_severity:
                parts.append(f"  - {c.claim}: {c.argument}")

    # Company notes
    if company_profile and company_profile.confidence < 0.4:
        parts.append(
            "\nNOTE: Company research is based on training data with low confidence. "
            "Do additional research before the interview."
        )

    return "\n".join(parts)
