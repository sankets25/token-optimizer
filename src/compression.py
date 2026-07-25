"""Rule-based prompt compression: strips low-information filler words and
phrases from a query before it's sent to the model.

Human language carries a lot of padding for a machine reader -- politeness
phrases, hedges, intensifiers -- that the model doesn't need to understand
the actual ask. Stripping it shrinks the input token count on every API call.

This is a heuristic stand-in for model-based compressors like LLMLingua: it
trades compression ratio for being zero-cost and fully offline, which keeps
it in line with router.py's zero-token classification and keeps tests
network-free. Swap `compress()` for a model-based implementation behind the
same signature if a higher compression ratio is worth the added dependency
and latency.

Compression is only applied to what's sent to the model -- the semantic
cache always embeds/stores the original query so paraphrase matching isn't
affected by what this module strips.
"""
from __future__ import annotations

import re

# Multi-word phrases stripped first, since they carry no single filler word
# a word-by-word pass would catch (e.g. "in order to" has no individual
# filler word in it, but the phrase itself is padding). Longer/more specific
# phrases are listed before their substrings (e.g. "could you please" before
# "could you") so the more specific match consumes the text first.
FILLER_PHRASES = (
    "could you please",
    "could you",
    "can you please",
    "can you",
    "would you please",
    "would you",
    "i would like to know",
    "i want to know",
    "i was wondering",
    "just wondering",
    "in order to",
    "sort of",
    "kind of",
    "to be honest",
    "at the end of the day",
    "for what it's worth",
    "i think that",
    "i guess",
)

FILLER_WORDS = frozenset(
    {
        "please",
        "kindly",
        "really",
        "very",
        "quite",
        "simply",
        "just",
        "actually",
        "basically",
        "essentially",
        "honestly",
        "literally",
        "so",
    }
)


def compress(query: str) -> str:
    """Strips filler phrases/words and collapses whitespace. Falls back to
    the original query if stripping would leave nothing behind."""
    text = query
    for phrase in FILLER_PHRASES:
        text = re.sub(re.escape(phrase), "", text, flags=re.IGNORECASE)

    words = text.split()
    kept = [w for w in words if re.sub(r"[^\w']", "", w).lower() not in FILLER_WORDS]

    result = " ".join(kept)
    result = re.sub(r"\s+([?.!,])", r"\1", result)  # drop space before punctuation
    result = re.sub(r"\s{2,}", " ", result).strip()

    return result or query
