"""Tests for the base agent class -- retry, timeout, validation."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base import BaseAgent, ValidationError
from src.models import JobAnalysis, Skill


class MockAgent(BaseAgent[JobAnalysis]):
    """Test agent with controllable validation."""

    def __init__(self, fail_validation: bool = False, validation_msg: str = "") -> None:
        super().__init__(
            name="test_agent",
            model="claude-haiku-4-5-20251001",
            system_prompt="Test prompt",
            output_type=JobAnalysis,
            max_retries=3,
            timeout_s=5.0,
        )
        self._fail_validation = fail_validation
        self._validation_msg = validation_msg

    def validate_output(self, result: JobAnalysis) -> JobAnalysis:
        if self._fail_validation:
            raise ValidationError(self._validation_msg)
        return result


def _make_mock_response(job_analysis: JobAnalysis) -> MagicMock:
    """Create a mock Claude API response."""
    response = MagicMock()
    response.content = [MagicMock(text=job_analysis.model_dump_json())]
    response.usage = MagicMock(input_tokens=100, output_tokens=50)
    return response


@pytest.fixture
def valid_job_analysis() -> JobAnalysis:
    return JobAnalysis(
        title="Test Engineer",
        company="TestCorp",
        required_skills=[Skill(name="Python", category="language")],
        role_level="senior",
        raw_text="Test job description",
    )


class TestBaseAgentRun:
    @pytest.mark.asyncio
    async def test_happy_path(self, valid_job_analysis):
        agent = MockAgent()
        mock_response = _make_mock_response(valid_job_analysis)

        with patch.object(agent._client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            result = await agent.run("Test input")

        assert result.status == "success"
        assert result.result is not None
        assert result.result.title == "Test Engineer"
        assert result.retries_used == 0

    @pytest.mark.asyncio
    async def test_retry_on_api_error(self, valid_job_analysis):
        agent = MockAgent()
        mock_response = _make_mock_response(valid_job_analysis)

        with patch.object(agent._client.messages, "create", new_callable=AsyncMock) as mock_create:
            # Fail first, succeed second
            from anthropic import APIError

            mock_create.side_effect = [
                APIError(message="rate limited", request=MagicMock(), body=None),
                mock_response,
            ]
            result = await agent.run("Test input")

        assert result.status == "success"
        assert result.retries_used == 1

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self):
        agent = MockAgent()

        with patch.object(agent._client.messages, "create", new_callable=AsyncMock) as mock_create:
            from anthropic import APIError

            mock_create.side_effect = APIError(
                message="server error", request=MagicMock(), body=None
            )
            result = await agent.run("Test input")

        assert result.status == "failed"
        assert result.retries_used == 3
        assert "API error" in (result.error or "")

    @pytest.mark.asyncio
    async def test_validation_failure_retries(self, valid_job_analysis):
        agent = MockAgent(fail_validation=True, validation_msg="empty skills")
        mock_response = _make_mock_response(valid_job_analysis)

        with patch.object(agent._client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            result = await agent.run("Test input")

        assert result.status == "failed"
        assert "Validation failed" in (result.error or "")

    @pytest.mark.asyncio
    async def test_timeout(self, valid_job_analysis):
        agent = MockAgent()
        agent.timeout_s = 0.01  # Very short timeout

        with patch.object(agent._client.messages, "create", new_callable=AsyncMock) as mock_create:
            async def slow_response(*args, **kwargs):
                await asyncio.sleep(1)
                return _make_mock_response(valid_job_analysis)

            mock_create.side_effect = slow_response
            result = await agent.run("Test input")

        assert result.status == "failed"
        assert "Timeout" in (result.error or "")
