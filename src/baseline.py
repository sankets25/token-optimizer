"""Week 1: the naive baseline — every query hits the same expensive model,
no cache, no routing. This is the number everything else gets compared to.
"""
from __future__ import annotations

import anthropic

from config import BASELINE_MODEL, MAX_TOKENS
from src.metrics import CallRecord, estimate_cost, timed


class BaselineClient:
    def __init__(self, model: str = BASELINE_MODEL) -> None:
        self.model = model
        self.client = anthropic.Anthropic()

    def ask(self, query_id: int, query: str) -> CallRecord:
        with timed() as t:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": query}],
            )

        text = next((b.text for b in response.content if b.type == "text"), "")
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        return CallRecord(
            query_id=query_id,
            query=query,
            model=self.model,
            route="baseline",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=t["elapsed_ms"],
            cost_usd=estimate_cost(self.model, input_tokens, output_tokens),
            response_preview=text[:200],
        )
