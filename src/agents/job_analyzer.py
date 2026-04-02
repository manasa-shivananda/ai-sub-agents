"""Job Analyzer agent -- parses a job description into structured data.

Extracts skills, requirements, role level, red flags, and dealbreakers
from raw job description text. Uses Haiku for fast, cheap extraction.
"""

from src.agents.base import BaseAgent, ValidationError
from src.models import JobAnalysis

SYSTEM_PROMPT = """\
You are a job description analyzer. Your task is to extract structured information
from a job posting.

Analyze the job description and extract:
- title: The job title as stated
- company: The company name
- required_skills: Skills explicitly required (each with name, category, and years if mentioned)
  - category must be one of: "language", "framework", "concept", "tool"
- nice_to_have_skills: Skills mentioned as preferred/nice-to-have
- years_experience: Total years of experience required (null if not stated)
- role_level: One of "junior", "mid", "senior", "lead" based on the JD language
- red_flags: Any concerning aspects of the job posting (unrealistic expectations, vague role, etc.)
- dealbreakers: Hard requirements that would disqualify most candidates (security clearance, specific visa status, relocation required, etc.)
- raw_text: Include the original job description text

Be precise. Only list skills that are explicitly mentioned or strongly implied.
Do not infer skills that are not referenced in the text.
If the JD is vague, extract what you can and note it in red_flags."""


class JobAnalyzer(BaseAgent[JobAnalysis]):
    def __init__(self) -> None:
        super().__init__(
            name="job_analyzer",
            model="claude-haiku-4-5-20251001",
            system_prompt=SYSTEM_PROMPT,
            output_type=JobAnalysis,
        )

    def validate_output(self, result: JobAnalysis) -> JobAnalysis:
        if not result.required_skills:
            raise ValidationError(
                "required_skills is empty. Every job description has at least one "
                "required skill. Re-read the JD and extract the skills mentioned."
            )
        if not result.title:
            raise ValidationError("title is empty. Extract the job title from the posting.")
        if not result.company:
            raise ValidationError("company is empty. Extract the company name from the posting.")
        return result
