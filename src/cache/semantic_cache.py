"""Embedding-based semantic cache backed by Redis.

Exact-match caching misses obvious paraphrases ("What's the capital of
France?" vs "What is the capital city of France?"). This cache embeds each
query locally (no API cost) and does a nearest-neighbor scan against
previously-cached queries in Redis; a hit above SEMANTIC_CACHE_THRESHOLD
returns the stored response instead of calling the model again.

At the query volumes here (tens to low thousands of cached entries), a linear
scan over stored embeddings is fast enough. A production deployment with a
large cache should swap the scan in `lookup()` for a vector index (e.g.
RediSearch/RedisVL's HNSW support) instead of changing the public interface.
"""
from __future__ import annotations

import json
import uuid
from typing import Optional

import numpy as np
import redis
from sentence_transformers import SentenceTransformer

from config import (
    EMBEDDING_MODEL_NAME,
    REDIS_DB,
    REDIS_HOST,
    REDIS_PORT,
    SEMANTIC_CACHE_THRESHOLD,
    SEMANTIC_CACHE_TTL_SECONDS,
)

NAMESPACE = "semcache"


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


class SemanticCache:
    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        threshold: float = SEMANTIC_CACHE_THRESHOLD,
        ttl_seconds: int = SEMANTIC_CACHE_TTL_SECONDS,
        model_name: str = EMBEDDING_MODEL_NAME,
        embedder: Optional[object] = None,
    ) -> None:
        self.redis = redis_client or redis.Redis(
            host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True
        )
        self.threshold = threshold
        self.ttl_seconds = ttl_seconds
        # `embedder` is injectable so tests can swap in a lightweight stub
        # instead of loading the real sentence-transformers model.
        self.embedder = embedder or SentenceTransformer(model_name)

    def _embed(self, text: str) -> np.ndarray:
        return self.embedder.encode(text, normalize_embeddings=True)

    def lookup(self, query: str) -> Optional[str]:
        """Returns the cached response text for the closest stored query
        above the similarity threshold, or None on a miss."""
        query_vec = self._embed(query)

        best_score = -1.0
        best_response: Optional[str] = None
        for key in self.redis.scan_iter(match=f"{NAMESPACE}:*"):
            raw = self.redis.get(key)
            if not raw:
                continue
            entry = json.loads(raw)
            stored_vec = np.array(entry["embedding"], dtype=np.float32)
            score = _cosine_similarity(query_vec, stored_vec)
            if score > best_score:
                best_score = score
                best_response = entry["response"]

        if best_score >= self.threshold:
            return best_response
        return None

    def store(self, query: str, response: str) -> None:
        vec = self._embed(query)
        key = f"{NAMESPACE}:{uuid.uuid4().hex}"
        payload = json.dumps(
            {
                "query": query,
                "embedding": vec.tolist(),
                "response": response,
            }
        )
        self.redis.set(key, payload, ex=self.ttl_seconds)

    def clear(self) -> None:
        for key in self.redis.scan_iter(match=f"{NAMESPACE}:*"):
            self.redis.delete(key)
