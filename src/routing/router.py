"""Cheap-vs-expensive model routing.

Classification is a zero-token heuristic, not a model call — spending tokens
on a classifier to decide whether to spend fewer tokens would work against
the point of this project. The heuristic only needs to be conservative: a
short factual query wrongly routed to the expensive model still gets a
correct answer, it just costs more, so the router can afford to over-route
tricky cases to "expensive" rather than gamble on "cheap".
"""
from __future__ import annotations

import re

from config import ROUTER_CHEAP_MODEL, ROUTER_EXPENSIVE_MODEL

# Signals that a query needs multi-step reasoning, code, or open-ended
# synthesis rather than a short factual/lookup-style answer.
COMPLEX_KEYWORDS = (
    "design",
    "architecture",
    "compare and contrast",
    "trade-off",
    "tradeoff",
    "debug",
    "analyze",
    "walk through",
    "strategy",
    "migrate",
    "scalable",
    "recommend",
    "propose",
    "runbook",
    "explain how",
    "rebalance",
)

WORD_COUNT_THRESHOLD = 30


def classify(query: str) -> str:
    """Returns ROUTER_CHEAP_MODEL or ROUTER_EXPENSIVE_MODEL."""
    lowered = query.lower()

    if "```" in query or "\n" in query.strip():
        return ROUTER_EXPENSIVE_MODEL

    if len(re.findall(r"\S+", query)) > WORD_COUNT_THRESHOLD:
        return ROUTER_EXPENSIVE_MODEL

    if any(keyword in lowered for keyword in COMPLEX_KEYWORDS):
        return ROUTER_EXPENSIVE_MODEL

    return ROUTER_CHEAP_MODEL


def route_label(model: str) -> str:
    """Maps a model id back to the "cheap"/"expensive" route name used in metrics."""
    return "cheap" if model == ROUTER_CHEAP_MODEL else "expensive"
