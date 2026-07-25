"""Optimized path: semantic cache first, router-selected model on a miss.

    query -> SemanticCache.lookup()
               |-- hit  -> return cached response (no API call)
               |-- miss -> router.classify() -> cheap/expensive model call
                            -> SemanticCache.store()
                            -> return response

Both branches log through the same CallRecord shape as baseline.py so
results/optimized_results.json and results/baseline_results.json are
directly comparable.
"""
from __future__ import annotations

import anthropic

from config import MAX_TOKENS
from src.cache.semantic_cache import SemanticCache
from src.metrics import CallRecord, estimate_cost, timed
from src.routing.router import classify, route_label


class OptimizedPipeline:
    def __init__(self, cache: SemanticCache | None = None) -> None:
        self.cache = cache or SemanticCache()
        self.client = anthropic.Anthropic()

    def ask(self, query_id: int, query: str) -> CallRecord:
        with timed() as t:
            cached_response = self.cache.lookup(query)

        if cached_response is not None:
            return CallRecord(
                query_id=query_id,
                query=query,
                model=None,
                route="cache_hit",
                input_tokens=0,
                output_tokens=0,
                latency_ms=t["elapsed_ms"],
                cost_usd=0.0,
                response_preview=cached_response[:200],
            )

        model = classify(query)

        with timed() as t:
            response = self.client.messages.create(
                model=model,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": query}],
            )

        text = next((b.text for b in response.content if b.type == "text"), "")
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        self.cache.store(query, text)

        return CallRecord(
            query_id=query_id,
            query=query,
            model=model,
            route=route_label(model),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=t["elapsed_ms"],
            cost_usd=estimate_cost(model, input_tokens, output_tokens),
            response_preview=text[:200],
        )
