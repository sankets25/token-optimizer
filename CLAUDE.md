# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A small pipeline that reduces LLM API cost/latency for a fixed set of queries by adding four layers in front of raw Anthropic API calls: a semantic cache (Redis + local embeddings), cheap/expensive model routing (zero-token heuristic), rule-based prompt compression, and an output-constraining system prompt. `src/baseline.py` is the naive comparison point (every query -> the expensive model, no cache, no routing, no compression, no constraints) and stays untouched by any of the four levers so it remains a clean reference point. All paths log through the same `CallRecord` shape (`src/metrics.py`) so `results/baseline_results.json` and `results/optimized_results.json` stay directly comparable, and `compressed`/`output_constrained`/`chars_saved_by_compression` on each record show which of the extra two levers were active for that call.

## Commands

```bash
pip install -r requirements.txt
cp .env.example .env          # fill in ANTHROPIC_API_KEY

# Redis is required for the semantic cache (not needed for tests):
docker run -d --name token-optimizer-redis -p 6379:6379 redis:7-alpine

python scripts/run_baseline.py     # every query -> BASELINE_MODEL, no cache
python scripts/run_optimized.py    # semantic cache + cheap/expensive routing

pytest tests/                      # no Redis/network needed (fakeredis + stub embedder)
pytest tests/test_cache.py::test_store_then_lookup_near_paraphrase_is_hit  # single test
```

Both run scripts read `data/queries.json`, print a live per-query trace plus a summary (tokens, cost, avg latency, cache hit rate), and write full per-query logs to `results/*.json`. `results/comparison_table.md` is filled in by hand from those two summaries — it is not generated.

## Architecture

```
query -> SemanticCache.lookup() [src/cache/semantic_cache.py]
           |-- hit  -> return cached response, no API call, route="cache_hit"
           |-- miss -> router.classify(query) [src/routing/router.py] -> cheap or expensive model
                        -> compression.compress(query) [src/compression.py] for the API call only
                        -> OUTPUT_CONSTRAINT_PROMPT [src/output_constraints.py] as system prompt
                        -> SemanticCache.store(query, response)  [original query, unaffected by compression]
                        -> return response, route="cheap"|"expensive"
```

Routing classifies against the *original* query, before compression touches it — this keeps the routing lever's effect isolated from the compression lever's effect when comparing results.

- **`config.py`** — single source of truth for models, pricing (`MODEL_PRICING`), Redis connection, and cache tuning. Loaded from env vars via `.env` (see `.env.example`) with defaults for local dev. All other modules import from here rather than reading `os.environ` directly.
- **`src/cache/semantic_cache.py`** — embeds queries locally (`sentence-transformers`, no API cost) and does a linear cosine-similarity scan over entries stored in Redis under the `semcache:*` namespace. A hit above `SEMANTIC_CACHE_THRESHOLD` (`.env`, default 0.92) returns the stored response. The embedder is injectable (`embedder=` param) specifically so tests can swap in a deterministic stub instead of loading the real model — see `tests/test_cache.py::StubEmbedder`. The linear scan is intentional at this query volume; a production-scale cache would swap in a vector index (RediSearch/RedisVL HNSW) behind the same `lookup()`/`store()` interface rather than changing callers.
- **`src/routing/router.py`** — `classify()` is a zero-token heuristic (never a model call — that would defeat the purpose of routing to save tokens). It routes to `ROUTER_EXPENSIVE_MODEL` on any of: code fences/newlines in the query, word count over `WORD_COUNT_THRESHOLD` (30), or a match in `COMPLEX_KEYWORDS`. The heuristic is deliberately conservative — over-routing a simple query to the expensive model still gets a correct answer, just at higher cost, whereas under-routing a complex query to the cheap model risks a wrong answer. Tune `COMPLEX_KEYWORDS`/`WORD_COUNT_THRESHOLD` against real query mixes, not this repo's sample set.
- **`src/compression.py`** — `compress()` is also a zero-token heuristic (multi-word `FILLER_PHRASES` stripped first, then single `FILLER_WORDS`, then whitespace collapsed), not a model-based compressor like LLMLingua — deliberately dependency-light and offline-testable, matching the router's philosophy. Falls back to the original query if stripping would empty it out. Only affects what's sent to the model, never what's classified or cached.
- **`src/output_constraints.py`** — `OUTPUT_CONSTRAINT_PROMPT` is a fixed system prompt telling the model to answer tersely, cutting output tokens the model would otherwise spend restating the question or hedging.
- **`src/pipeline.py`** (`OptimizedPipeline`) — constructor takes `compress_prompts` and `constrain_output` (both default `True`) so either lever can be disabled independently, e.g. for an ablation comparison. **`src/baseline.py`** (`BaselineClient`) intentionally has no equivalent flags — it's the fixed, unoptimized reference point and must not gain any of the four levers. Both expose a single `ask(query_id, query) -> CallRecord` method — this shared shape is what keeps the two result sets comparable. When adding a new pipeline variant, match this interface.
- **`src/metrics.py`** — `CallRecord` is the common per-query log entry (`route` is one of `"cache_hit" | "cheap" | "expensive" | "baseline"`; `compressed`/`output_constrained`/`chars_saved_by_compression` default to `False`/`False`/`0` so baseline and cache-hit records are unaffected); `timed()` is a context manager for latency; `estimate_cost()` prices tokens from `config.MODEL_PRICING`; `MetricsLog` accumulates records, writes them to JSON, and computes the summary dict (totals, avg latency, cache hit rate, plus `compressed_calls`/`output_constrained_calls`/`total_chars_saved_by_compression` for a per-lever breakdown) printed by both scripts.
- **`scripts/run_baseline.py` / `scripts/run_optimized.py`** — thin drivers: load `data/queries.json`, run every query through the respective client/pipeline, save to `results/`, print the summary. Keep new query batches in `data/queries.json` in the same `{"id": ..., "query": ...}` shape.

## Testing notes

`tests/test_cache.py` uses `fakeredis.FakeRedis` (no real Redis) and a hand-written `StubEmbedder` mapping specific query strings to fixed vectors (no `sentence-transformers` model download, deterministic similarity scores) — follow this pattern for new cache tests rather than hitting real Redis or loading the real embedding model. `tests/test_compression.py` covers `compress()` directly — it's pure string logic with no external dependency, so no stubbing needed.
