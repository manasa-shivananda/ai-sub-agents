"""Letter Writer agent -- generates a tailored cover letter.

Takes all upstream agent outputs and produces a cover letter that
addresses top skill matches and preempts identified gaps.
"""

from src.agents.base import BaseAgent, ValidationError
from src.models import CoverLetter

SYSTEM_PROMPT = """\
You are a cover letter writer. You receive the full analysis of a job application:
- Job analysis (what the role requires)
- Gap report (candidate's strengths and weaknesses)
- Company profile (company culture and values, may be null if unavailable)
- Devil's advocate challenges (weaknesses to preempt)

Write a tailored cover letter that:
1. Opens with a specific connection to the company or role (not generic)
2. Highlights the top 3-4 matched skills with concrete evidence from the resume
3. Preemptively addresses the top 1-2 gaps identified by the devil's advocate
   by framing transferable skills or learning agility
4. Connects the candidate's experience to the company's values (if company profile available)
5. Closes with enthusiasm and a specific call to action

The letter should be:
- Professional but not stiff
- Specific to THIS role at THIS company (no generic phrases)
- 300-500 words
- Written in first person

Also return skills_referenced: a list of skill names from the job description
that you explicitly referenced in the letter. This is used to verify coverage.

If company profile is unavailable, focus the letter on the role requirements
and the candidate's technical fit instead of company culture.

IMPORTANT: Do not use phrases like "I am writing to express my interest" or
"I believe I would be a great fit." Be direct and specific."""


class LetterWriter(BaseAgent[CoverLetter]):
    def __init__(self) -> None:
        super().__init__(
            name="letter_writer",
            model="claude-sonnet-4-6",
            system_prompt=SYSTEM_PROMPT,
            output_type=CoverLetter,
        )

    def validate_output(self, result: CoverLetter) -> CoverLetter:
        if len(result.text) < 200:
            raise ValidationError(
                "Cover letter is too short (under 200 characters). "
                "Write a substantive 300-500 word letter."
            )
        if len(result.skills_referenced) < 2:
            raise ValidationError(
                "Cover letter references fewer than 2 skills from the job description. "
                "A good cover letter should explicitly mention at least 2-3 key skills "
                "from the JD with specific evidence."
            )
        return result
