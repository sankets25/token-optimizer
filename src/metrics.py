"""Token/cost/latency logging shared by the baseline and optimized pipelines.

Both pipelines log through CallRecord so results/*.json stay in a single,
comparable shape regardless of which path (cache hit, cheap model, expensive
model) a query took.
"""
from __future__ import annotations

import json
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from typing import Iterator, Optional

from config import MODEL_PRICING


@dataclass
class CallRecord:
    query_id: int
    query: str
    model: Optional[str]  # None when served entirely from cache
    route: str  # "cache_hit" | "cheap" | "expensive" | "baseline"
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    response_preview: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def estimate_cost(model: Optional[str], input_tokens: int, output_tokens: int) -> float:
    if model is None or model not in MODEL_PRICING:
        return 0.0
    pricing = MODEL_PRICING[model]
    return (input_tokens / 1_000_000) * pricing["input"] + (
        output_tokens / 1_000_000
    ) * pricing["output"]


@contextmanager
def timed() -> Iterator[dict]:
    """Yields a dict that `elapsed_ms` gets written into on exit."""
    start = time.perf_counter()
    box: dict = {}
    try:
        yield box
    finally:
        box["elapsed_ms"] = (time.perf_counter() - start) * 1000


class MetricsLog:
    """Accumulates CallRecords and writes them to a JSON file."""

    def __init__(self) -> None:
        self.records: list[CallRecord] = []

    def add(self, record: CallRecord) -> None:
        self.records.append(record)

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in self.records], f, indent=2)

    def summary(self) -> dict:
        total_input = sum(r.input_tokens for r in self.records)
        total_output = sum(r.output_tokens for r in self.records)
        total_cost = sum(r.cost_usd for r in self.records)
        total_latency = sum(r.latency_ms for r in self.records)
        n = len(self.records) or 1
        cache_hits = sum(1 for r in self.records if r.route == "cache_hit")
        return {
            "num_queries": len(self.records),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "total_cost_usd": round(total_cost, 6),
            "avg_latency_ms": round(total_latency / n, 2),
            "cache_hits": cache_hits,
            "cache_hit_rate": round(cache_hits / n, 4),
        }
