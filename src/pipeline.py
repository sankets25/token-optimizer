"""Optimized path: semantic cache first, router-selected model on a miss,
with prompt compression and output constraints applied to what actually
reaches the model on a cache miss.

    query -> SemanticCache.lookup()
               |-- hit  -> return cached response (no API call)
               |-- miss -> router.classify(query) -> cheap/expensive model
                            -> compression.compress(query) for the API call
                            -> output_constraints system prompt on the call
                            -> SemanticCache.store(query, response)  [original
                               query, so paraphrase matching is unaffected]
                            -> return response

Routing decisions are made against the original query so the compression
lever can't shift which model a query lands on -- each lever's effect stays
isolated from the others. All branches log through the same CallRecord shape
as baseline.py so results/optimized_results.json and
results/baseline_results.json are directly comparable; `compressed` and
`output_constrained` record which extra levers were active per call.
"""
from __future__ import annotations

import anthropic

from config import MAX_TOKENS
from src.cache.semantic_cache import SemanticCache
from src.compression import compress
from src.metrics import CallRecord, estimate_cost, timed
from src.output_constraints import OUTPUT_CONSTRAINT_PROMPT
from src.routing.router import classify, route_label


class OptimizedPipeline:
    def __init__(
        self,
        cache: SemanticCache | None = None,
        compress_prompts: bool = True,
        constrain_output: bool = True,
    ) -> None:
        self.cache = cache or SemanticCache()
        self.client = anthropic.Anthropic()
        self.compress_prompts = compress_prompts
        self.constrain_output = constrain_output

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

        sent_query = compress(query) if self.compress_prompts else query
        chars_saved = len(query) - len(sent_query)

        create_kwargs = {
            "model": model,
            "max_tokens": MAX_TOKENS,
            "messages": [{"role": "user", "content": sent_query}],
        }
        if self.constrain_output:
            create_kwargs["system"] = OUTPUT_CONSTRAINT_PROMPT

        with timed() as t:
            response = self.client.messages.create(**create_kwargs)

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
            compressed=self.compress_prompts,
            output_constrained=self.constrain_output,
            chars_saved_by_compression=chars_saved,
        )
