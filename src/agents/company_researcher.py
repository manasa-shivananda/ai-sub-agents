"""Company Researcher agent -- researches company culture and values.

Uses Claude's training knowledge to provide company context.
Sets data_freshness="training_data" to be transparent about the source.
"""

from src.agents.base import BaseAgent, ValidationError
from src.models import CompanyProfile

SYSTEM_PROMPT = """\
You are a company research analyst. Given a company name, provide a profile
based on your knowledge. Be transparent about what you know vs. what you're
uncertain about.

Provide:
- name: The company name
- culture_summary: A 2-3 sentence summary of the company culture and work environment
- values: Key company values or principles (extract from what you know)
- recent_news: Any notable recent developments you're aware of (may be outdated)
- glassdoor_sentiment: Brief sentiment if you have knowledge of employee reviews (null if unknown)
- interview_tips: Practical tips for interviewing at this company
- confidence: How confident you are in this information (0.0-1.0).
  Use 0.7+ for well-known companies, 0.3-0.6 for less-known companies,
  below 0.3 if you have very little information.

IMPORTANT: If you don't know much about this company, say so honestly.
Set confidence low and note in culture_summary that information is limited.
Do not fabricate details about companies you don't know well.
It is better to return low-confidence honest information than high-confidence guesses."""


class CompanyResearcher(BaseAgent[CompanyProfile]):
    def __init__(self) -> None:
        super().__init__(
            name="company_researcher",
            model="claude-sonnet-4-6",
            system_prompt=SYSTEM_PROMPT,
            output_type=CompanyProfile,
        )

    def validate_output(self, result: CompanyProfile) -> CompanyProfile:
        if not result.values:
            raise ValidationError(
                "values list is empty. Even with limited knowledge, provide at least "
                "one general value or principle the company likely holds."
            )
        # Force data_freshness to training_data since v1 has no web search
        result.data_freshness = "training_data"
        return result
