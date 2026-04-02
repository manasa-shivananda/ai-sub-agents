"""Observability layer for the agent pipeline.

Records every agent call with token counts, latency, cost estimates, and status.
Weekend 1: in-memory traces with CLI output.
Weekend 2: SQLite persistence + WebSocket streaming to dashboard.
"""

from __future__ import annotations

import time

from src.models import ExecutionTrace, TraceEntry

# Last verified: 2026-04-02 — https://docs.anthropic.com/en/docs/about-claude/pricing
PRICING: dict[str, dict[str, float]] = {
    "claude-haiku-4-5-20251001": {"input": 0.80 / 1_000_000, "output": 4.00 / 1_000_000},
    "claude-sonnet-4-6": {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000},
}


class Tracer:
    """Collects trace entries for a single pipeline run."""

    def __init__(self) -> None:
        self._entries: list[TraceEntry] = []
        self._start_time: float = time.monotonic()
        self._pending_tokens: dict[str, dict[str, int | str]] = {}

    def _elapsed(self) -> float:
        return round(time.monotonic() - self._start_time, 1)

    def record_dispatch(self, agent_name: str, tokens_in: int | None = None) -> None:
        self._entries.append(
            TraceEntry(
                timestamp_s=self._elapsed(),
                source="ORCHESTRATOR",
                target=agent_name,
                tokens_in=tokens_in,
                status="dispatched",
            )
        )

    def record_tokens(
        self,
        agent_name: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
    ) -> None:
        self._pending_tokens[agent_name] = {
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        }

    def record_success(self, agent_name: str, duration_s: float) -> None:
        token_info = self._pending_tokens.pop(agent_name, {})
        tokens_in = token_info.get("tokens_in")
        tokens_out = token_info.get("tokens_out")
        model = token_info.get("model", "")
        cost = self._estimate_cost(str(model), tokens_in, tokens_out)

        self._entries.append(
            TraceEntry(
                timestamp_s=self._elapsed(),
                source=agent_name,
                target="ORCHESTRATOR",
                tokens_in=int(tokens_in) if tokens_in else None,
                tokens_out=int(tokens_out) if tokens_out else None,
                status="success",
                cost_usd=cost,
            )
        )

    def record_retry(self, agent_name: str, error: str) -> None:
        self._entries.append(
            TraceEntry(
                timestamp_s=self._elapsed(),
                source=agent_name,
                target="ORCHESTRATOR",
                status="retry",
                error=error,
            )
        )

    def record_failure(
        self, agent_name: str, error: str, duration_s: float
    ) -> None:
        self._pending_tokens.pop(agent_name, None)
        self._entries.append(
            TraceEntry(
                timestamp_s=self._elapsed(),
                source=agent_name,
                target="ORCHESTRATOR",
                status="failed",
                error=error,
            )
        )

    def _estimate_cost(
        self,
        model: str,
        tokens_in: int | str | None,
        tokens_out: int | str | None,
    ) -> float | None:
        pricing = PRICING.get(model)
        if not pricing or tokens_in is None or tokens_out is None:
            return None
        return round(
            int(tokens_in) * pricing["input"] + int(tokens_out) * pricing["output"],
            6,
        )

    def build_trace(self) -> ExecutionTrace:
        success_entries = [e for e in self._entries if e.status == "success"]
        failed_entries = [e for e in self._entries if e.status == "failed"]
        retry_entries = [e for e in self._entries if e.status == "retry"]

        total_tokens = sum(
            (e.tokens_in or 0) + (e.tokens_out or 0)
            for e in self._entries
            if e.status == "success"
        )
        total_cost = sum(e.cost_usd or 0.0 for e in self._entries if e.cost_usd)

        return ExecutionTrace(
            entries=self._entries,
            total_duration_s=self._elapsed(),
            total_tokens=total_tokens,
            total_cost_usd=round(total_cost, 4),
            agents_succeeded=len(success_entries),
            agents_failed=len(failed_entries),
            retries_used=len(retry_entries),
        )

    def print_trace(self) -> None:
        """Print a formatted execution trace to stdout."""
        for entry in self._entries:
            ts = f"[{entry.timestamp_s:05.1f}s]"
            if entry.status == "dispatched":
                parallel = ""
                # Check if there's another dispatch at the same timestamp
                same_ts = [
                    e
                    for e in self._entries
                    if e.status == "dispatched"
                    and e.timestamp_s == entry.timestamp_s
                    and e.target != entry.target
                ]
                if same_ts:
                    parallel = " [PARALLEL]"
                tokens = f"({entry.tokens_in} tokens in)" if entry.tokens_in else ""
                print(f"{ts} ORCHESTRATOR -> {entry.target} {tokens}{parallel}")

            elif entry.status == "success":
                tokens = f"({entry.tokens_out} tokens out, " if entry.tokens_out else "("
                cost = f"${entry.cost_usd:.4f}" if entry.cost_usd else ""
                print(f"{ts} {entry.source} -> ORCHESTRATOR {tokens}SUCCESS{f', {cost}' if cost else ''})")

            elif entry.status == "retry":
                error_short = (entry.error or "")[:60]
                print(f"{ts} {entry.source} -> ORCHESTRATOR (RETRY: {error_short})")

            elif entry.status == "failed":
                error_short = (entry.error or "")[:60]
                print(f"{ts} {entry.source} -> ORCHESTRATOR (FAILED: {error_short})")

        # Summary line
        trace = self.build_trace()
        print(
            f"[{trace.total_duration_s:05.1f}s] COMPLETE -- "
            f"{trace.agents_succeeded + trace.agents_failed} agent calls, "
            f"{trace.retries_used} retries, "
            f"{trace.total_duration_s:.1f}s total, "
            f"${trace.total_cost_usd:.4f} estimated cost"
        )
