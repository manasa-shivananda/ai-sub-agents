"""Base agent class with retry, timeout, structured output extraction, and validation.

Every agent in the pipeline inherits from BaseAgent[T]. The base class handles:
- Calling Claude with output_config structured outputs
- Parsing and validating the response via Pydantic
- Retrying on API errors or validation failures (exponential backoff)
- Timeout enforcement per agent call
- Post-validation hooks for semantic quality checks
- Trace entry recording for observability
"""

from __future__ import annotations

import asyncio
import time
from typing import Generic, TypeVar

import anthropic

from src.models import AgentResult, AgentStatus

T = TypeVar("T")


class ValidationError(Exception):
    """Raised when validate_output rejects an agent's output."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class BaseAgent(Generic[T]):
    def __init__(
        self,
        name: str,
        model: str,
        system_prompt: str,
        output_type: type[T],
        max_retries: int = 3,
        timeout_s: float = 30.0,
    ) -> None:
        self.name = name
        self.model = model
        self.system_prompt = system_prompt
        self.output_type = output_type
        self.max_retries = max_retries
        self.timeout_s = timeout_s
        self._client = anthropic.AsyncAnthropic()

    def validate_output(self, result: T) -> T:
        """Override in subclasses for semantic quality checks.

        Raise ValidationError with a descriptive message if the output
        is semantically invalid (e.g., empty skills list, rubber-stamp approval).
        The message is included in the retry nudge to the LLM.
        """
        return result

    async def run(
        self,
        input_text: str,
        tracer: "Tracer | None" = None,
    ) -> AgentResult[T]:
        """Execute the agent with retry, timeout, and validation.

        Returns AgentResult with status, result, error info, and timing.
        """
        start_time = time.monotonic()
        last_error: str | None = None
        nudge: str | None = None

        for attempt in range(self.max_retries):
            try:
                result = await self._call_llm(input_text, nudge, tracer)
                validated = self.validate_output(result)

                duration = time.monotonic() - start_time
                if tracer:
                    tracer.record_success(self.name, duration)

                return AgentResult[self.output_type](
                    status="success",
                    result=validated,
                    retries_used=attempt,
                    duration_s=round(duration, 2),
                )

            except ValidationError as e:
                last_error = f"Validation failed: {e.message}"
                nudge = (
                    f"Your previous output was rejected: {e.message}. "
                    "Please fix this and try again."
                )
                if tracer:
                    tracer.record_retry(self.name, last_error)

            except anthropic.APIError as e:
                last_error = f"API error: {e}"
                nudge = None
                if tracer:
                    tracer.record_retry(self.name, last_error)

            except asyncio.TimeoutError:
                last_error = f"Timeout after {self.timeout_s}s"
                nudge = None
                if tracer:
                    tracer.record_retry(self.name, last_error)

            except Exception as e:
                last_error = f"Unexpected error: {e}"
                nudge = None
                if tracer:
                    tracer.record_retry(self.name, last_error)

            # Exponential backoff: 1s, 2s, 4s
            if attempt < self.max_retries - 1:
                await asyncio.sleep(2**attempt)

        # All retries exhausted
        duration = time.monotonic() - start_time
        if tracer:
            tracer.record_failure(self.name, last_error or "Unknown error", duration)

        return AgentResult[self.output_type](
            status="failed",
            error=last_error,
            retries_used=self.max_retries,
            duration_s=round(duration, 2),
        )

    @staticmethod
    def _make_strict_schema(schema: dict) -> dict:
        """Add additionalProperties: false to all object types in the schema.

        The Claude API requires strict JSON schemas where every object type
        explicitly disallows extra properties.
        """
        schema = schema.copy()

        def _fix_object(obj: dict) -> None:
            if isinstance(obj, dict):
                if obj.get("type") == "object" and "properties" in obj:
                    obj["additionalProperties"] = False
                for v in obj.values():
                    if isinstance(v, dict):
                        _fix_object(v)
                    elif isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict):
                                _fix_object(item)

        _fix_object(schema)
        if "$defs" in schema:
            for defn in schema["$defs"].values():
                _fix_object(defn)
        return schema

    async def _call_llm(
        self,
        input_text: str,
        nudge: str | None,
        tracer: "Tracer | None",
    ) -> T:
        """Make the actual Claude API call with structured output extraction."""
        messages = [{"role": "user", "content": input_text}]
        if nudge:
            messages.append({"role": "assistant", "content": "I understand. Let me fix that."})
            messages.append({"role": "user", "content": nudge})

        strict_schema = self._make_strict_schema(self.output_type.model_json_schema())

        response = await asyncio.wait_for(
            self._client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.system_prompt,
                messages=messages,
                output_config={
                    "format": {
                        "type": "json_schema",
                        "schema": strict_schema,
                    }
                },
            ),
            timeout=self.timeout_s,
        )

        # Record token usage
        if tracer and response.usage:
            tracer.record_tokens(
                self.name,
                self.model,
                tokens_in=response.usage.input_tokens,
                tokens_out=response.usage.output_tokens,
            )

        # Extract JSON from response content
        raw_text = response.content[0].text
        return self.output_type.model_validate_json(raw_text)
