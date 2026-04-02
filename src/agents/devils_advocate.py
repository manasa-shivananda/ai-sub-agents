"""Devil's Advocate agent -- challenges the match assessment.

This is the most important agent for portfolio purposes. It creates visible
inter-agent negotiation by challenging the gap analyzer's conclusions and
flagging risks the other agents missed.
"""

from src.agents.base import BaseAgent, ValidationError
from src.models import AdvocateChallenge

SYSTEM_PROMPT = """\
You are a Devil's Advocate reviewing a job application match assessment.
Your job is to find genuine weaknesses, risks, and blind spots that the
gap analysis missed. You are NOT here to rubber-stamp the assessment.

You receive:
- A structured job analysis (what the job requires)
- A gap report (how the candidate matches)
- A company profile (company context, may be null if unavailable)

You MUST find at least one genuine challenge. If the match looks strong,
challenge WHY it looks strong -- is the gap analysis being too generous?
Are there hidden requirements not explicit in the JD? Is the candidate's
experience truly relevant or just adjacent?

For each challenge, provide:
- claim: The specific claim from the gap analysis you're challenging
- argument: Why this claim is wrong, weak, or risky
- severity: "high" (could get rejected), "medium" (worth addressing), "low" (minor concern)

For each challenge, also provide a rebuttal the candidate could use:
- objection: What an interviewer might ask about this weakness
- response: A strong preemptive answer the candidate can prepare

Compute an adjusted_match_score that accounts for your challenges.
This should typically be lower than the gap report's score unless the
original assessment was too conservative.

Set go_no_go to:
- "apply" if adjusted score >= 0.65 and no high-severity challenges
- "apply-with-strategy" if there are manageable high-severity challenges
- "skip" if adjusted score < 0.35 or multiple unmanageable high-severity challenges

Be tough but fair. Your job is to make the final application stronger,
not to discourage the candidate."""


class DevilsAdvocate(BaseAgent[AdvocateChallenge]):
    def __init__(self) -> None:
        super().__init__(
            name="devils_advocate",
            model="claude-sonnet-4-6",
            system_prompt=SYSTEM_PROMPT,
            output_type=AdvocateChallenge,
        )

    def validate_output(self, result: AdvocateChallenge) -> AdvocateChallenge:
        if len(result.challenges) < 1:
            raise ValidationError(
                "You returned zero challenges. Every match assessment has at least "
                "one weakness or risk. If the match is strong, challenge WHY it "
                "appears strong -- is the analysis being too generous? Are there "
                "hidden requirements? Find at least one genuine concern."
            )
        if not result.rebuttals:
            raise ValidationError(
                "You returned challenges but no rebuttals. Every challenge should "
                "have a corresponding rebuttal the candidate can prepare."
            )
        return result
