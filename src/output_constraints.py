"""Output-side token savings: a system prompt that tells the model to answer
tersely instead of trimming its response after the fact.

Left alone, models tend to over-explain -- restate the question, hedge with
caveats, pad a one-line answer into a paragraph. None of that costs anything
extra to remove up front, since it's the model choosing to spend output
tokens on it in the first place; asking for a constrained format directly
cuts output tokens rather than generating them and throwing them away.
"""
from __future__ import annotations

OUTPUT_CONSTRAINT_PROMPT = (
    "Answer as concisely as possible. Do not restate the question, and do "
    "not add disclaimers or caveats. If the answer fits in one sentence, "
    "use one sentence."
)
