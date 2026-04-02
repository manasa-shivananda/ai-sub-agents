"""Gap Analyzer agent -- compares resume against job description.

Identifies matched skills with evidence, gaps with severity ratings,
and transferable skills that partially cover gaps.
"""

from src.agents.base import BaseAgent, ValidationError
from src.models import GapReport

SYSTEM_PROMPT = """\
You are a resume-to-job-description gap analyzer. You receive a structured job analysis
and a candidate's resume. Your task is to produce a detailed gap report.

For each required skill in the job analysis:
1. Check if the resume demonstrates this skill
2. If YES: create a SkillMatch with the skill, a direct quote or reference from the resume
   as evidence, and a confidence score (0.0-1.0)
3. If NO: create a SkillGap with the skill, severity ("critical" for hard requirements,
   "moderate" for important but learnable, "minor" for nice-to-haves), and any
   transferable skill from the resume that partially covers the gap

Also check nice-to-have skills from the job analysis.

Compute an overall_match_score (0.0-1.0) based on how well the resume matches the JD.
Weight critical skill matches higher than nice-to-haves.

Set recommendation to:
- "apply" if match score >= 0.7 and no critical gaps
- "apply-with-strategy" if match score >= 0.5 or has transferable skills for critical gaps
- "skip" if match score < 0.4 and multiple critical gaps

Be honest and specific. Every match must have real evidence from the resume.
Do not fabricate evidence or inflate confidence scores."""


class GapAnalyzer(BaseAgent[GapReport]):
    def __init__(self) -> None:
        super().__init__(
            name="gap_analyzer",
            model="claude-sonnet-4-6",
            system_prompt=SYSTEM_PROMPT,
            output_type=GapReport,
        )

    def validate_output(self, result: GapReport) -> GapReport:
        # Check that high-confidence matches have non-empty evidence
        for match in result.matched_skills:
            if match.confidence > 0.7 and not match.evidence.strip():
                raise ValidationError(
                    f"Skill match '{match.skill.name}' has confidence {match.confidence} "
                    "but empty evidence. Every high-confidence match must cite specific "
                    "resume content as evidence."
                )
        # Must have at least one match or one gap
        if not result.matched_skills and not result.gaps:
            raise ValidationError(
                "Both matched_skills and gaps are empty. A resume always has some "
                "overlap or gaps with a job description. Analyze more carefully."
            )
        return result
