"""Central configuration for the token-optimizer project.

Values are loaded from environment variables (see .env.example) with
sensible defaults so the project runs out of the box against a local Redis.
"""
import os

from dotenv import load_dotenv

load_dotenv()

# --- Anthropic ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Two-tier routing: cheap model handles simple/short queries, expensive model
# handles anything the router flags as complex.
ROUTER_CHEAP_MODEL = os.environ.get("ROUTER_CHEAP_MODEL", "claude-haiku-4-5")
ROUTER_EXPENSIVE_MODEL = os.environ.get("ROUTER_EXPENSIVE_MODEL", "claude-opus-4-8")

# Model the unoptimized baseline always calls, regardless of query complexity.
BASELINE_MODEL = os.environ.get("BASELINE_MODEL", "claude-opus-4-8")

MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "1024"))

# $ per 1M tokens (input, output) — used for cost estimates in metrics.py.
MODEL_PRICING = {
    "claude-opus-4-8": {"input": 5.00, "output": 25.00},
    "claude-sonnet-5": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
}

# --- Redis / semantic cache ---
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))

SEMANTIC_CACHE_THRESHOLD = float(os.environ.get("SEMANTIC_CACHE_THRESHOLD", "0.92"))
SEMANTIC_CACHE_TTL_SECONDS = int(os.environ.get("SEMANTIC_CACHE_TTL_SECONDS", "86400"))
EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")

# --- Paths ---
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
QUERIES_FILE = os.path.join(DATA_DIR, "queries.json")
