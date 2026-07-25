# Baseline vs. Optimized — Comparison

Fill this in after running both `scripts/run_baseline.py` and
`scripts/run_optimized.py` against the same `data/queries.json`. Pull the
numbers from `results/baseline_results.json` / `results/optimized_results.json`
(each run also prints this summary to stdout).

| Metric               | Baseline | Optimized | Change |
|----------------------|---------:|----------:|-------:|
| Total tokens         |   15,357 |    13,109 | -14.6% |
| Total cost (USD)     |  $0.3630 |   $0.2605 | -28.2% |
| Avg latency (ms)     |   6,188  |    4,937  | -20.2% |
| Cache hit rate       |    n/a   | 17.1% (6/35) | — |
| Queries routed cheap |    n/a   | 17/35 (Haiku 4.5) | — |

Run on 2026-07-24: 35 queries from `data/queries.json`, cold cache for the
optimized run (a warm-cache rerun would show a higher hit rate and lower
cost, since 6 of the 35 queries are near-duplicates by design).

## Notes

- Run both scripts against the *same* `data/queries.json` so the comparison is apples-to-apples.
- The optimized run's cost/latency on a cold cache (first pass) will look worse than a warm-cache second pass — run it twice and report the warm-cache numbers if that's the scenario you're optimizing for.

## Ablation — compression + output constraints (added 2026-07-24)

`OptimizedPipeline` gained two more levers on top of cache + routing: rule-based prompt
compression (`src/compression.py`) and an output-constraining system prompt
(`src/output_constraints.py`). Ran both variants against the same 35 queries, cache
cleared before each run so cache hits from one run couldn't mask the other's numbers.
Full per-query breakdown: `results/ablation_compression_constraint.json`.

This ablation isolates *only* the compression/output-constraint delta — both columns
below already include the semantic cache and cheap/expensive routing from the table
above (i.e. both are variants of "Optimized", not a rerun of "Baseline"):

- **"Old"** = `OptimizedPipeline(compress_prompts=False, constrain_output=False)` — cache +
  routing only, i.e. exactly the pipeline's behavior *before* this session added the
  compression and output-constraint code. This is the fair pre-change baseline for the
  new levers specifically, not the naive `BaselineClient` from the table above.
- **"New"** = `OptimizedPipeline(compress_prompts=True, constrain_output=True)` — the
  current default: cache + routing + compression + output constraints, all four levers
  active.

| Metric                      | Old: cache + routing only | New: cache + routing + compression + output constraints |     Change |
|------------------------------|---------------------------------:|---------------:|-----------:|
| Total tokens                 |                           12,652 |          10,584 |    -16.3% |
| Total cost (USD)             |                          $0.2571 |         $0.1982 |    -22.9% |
| Avg latency (ms)             |                           4,899  |           3,877 |    -20.9% |
| Input tokens                 |                              871 |           2,177 |   +150.0% |
| Output tokens                |                           11,781 |           8,407 |    -28.6% |
| Chars saved by compression   |                               0  |         20 (30 calls) |    — |

**Net optimized — but read the "why" before assuming compression did the work:**

- **Output constraints are almost the entire win.** Several queries that previously ran
  all the way to the 1024-token `max_tokens` ceiling (records 18–25, 32 in the ablation
  JSON) finish in far fewer output tokens once the model is told to answer tersely. That's
  where nearly all of the ~3,374 output-token / ~$0.059 savings comes from.
- **Compression barely moved the needle on this dataset.** Only 20 characters were
  stripped across 30 non-cache-hit calls. `data/queries.json`'s queries are already short,
  direct questions ("What is the capital of France?") rather than conversationally padded
  ones ("Could you please kindly tell me...") — there's very little filler for a
  filler-word/phrase heuristic to find. The lever is real (see `tests/test_compression.py`
  for cases where it clearly strips padding), it just doesn't have much to work with in
  this sample set.
- **Input tokens went up, not down**, because the output-constraint system prompt itself
  costs ~40–100 input tokens per call, and this dataset's queries are so short (14–22
  input tokens originally) that the fixed prompt overhead outweighs whatever compression
  removes. On longer, more verbose real-world queries this would flip, since the constraint
  prompt's cost is fixed while compression's savings scale with query length.
- **Takeaway:** these two levers are genuinely useful, but this repo's sample queries are
  too small and too terse to showcase compression specifically — treat the compression
  number here as a demonstration of the mechanism working correctly (see the unit tests),
  not evidence of how much it saves in general. It'll show a real effect on longer,
  more conversationally-phrased input than this dataset's.
