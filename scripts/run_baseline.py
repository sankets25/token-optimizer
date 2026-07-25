"""Run every query in data/queries.json through the naive baseline
(same expensive model, no cache, no routing) and save the results."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import QUERIES_FILE, RESULTS_DIR
from src.baseline import BaselineClient
from src.metrics import MetricsLog


def main() -> None:
    with open(QUERIES_FILE, encoding="utf-8") as f:
        queries = json.load(f)

    client = BaselineClient()
    log = MetricsLog()

    for item in queries:
        print(f"[baseline] query {item['id']}: {item['query'][:60]!r}")
        record = client.ask(item["id"], item["query"])
        log.add(record)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_path = os.path.join(RESULTS_DIR, "baseline_results.json")
    log.save(out_path)

    print("\n--- baseline summary ---")
    print(json.dumps(log.summary(), indent=2))
    print(f"\nSaved {len(log.records)} records to {out_path}")


if __name__ == "__main__":
    main()
