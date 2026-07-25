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
