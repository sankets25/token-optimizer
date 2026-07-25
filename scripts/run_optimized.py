"""Run every query in data/queries.json through the optimized pipeline
(semantic cache + cheap/expensive routing) and save the results."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import QUERIES_FILE, RESULTS_DIR
from src.metrics import MetricsLog
from src.pipeline import OptimizedPipeline


def main() -> None:
    with open(QUERIES_FILE, encoding="utf-8") as f:
        queries = json.load(f)

    pipeline = OptimizedPipeline()
    log = MetricsLog()

    for item in queries:
        print(f"[optimized] query {item['id']}: {item['query'][:60]!r}")
        record = pipeline.ask(item["id"], item["query"])
        log.add(record)
        print(f"  -> route={record.route} model={record.model}")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_path = os.path.join(RESULTS_DIR, "optimized_results.json")
    log.save(out_path)

    print("\n--- optimized summary ---")
    print(json.dumps(log.summary(), indent=2))
    print(f"\nSaved {len(log.records)} records to {out_path}")


if __name__ == "__main__":
    main()
