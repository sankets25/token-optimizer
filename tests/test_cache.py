"""Unit tests for SemanticCache. Uses fakeredis (no real Redis needed) and a
stub embedder (no sentence-transformers model download needed) so these run
fast and offline.
"""
import os
import sys

import fakeredis
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cache.semantic_cache import SemanticCache


class StubEmbedder:
    """Maps known strings to hand-picked vectors so similarity is
    deterministic and test-controlled; unknown strings get a vector that's
    orthogonal to everything defined here."""

    VECTORS = {
        "capital of france": np.array([1.0, 0.0, 0.0], dtype=np.float32),
        "capital city of france": np.array([0.99, 0.05, 0.0], dtype=np.float32),
        "capital of japan": np.array([0.0, 1.0, 0.0], dtype=np.float32),
    }

    def encode(self, text: str, normalize_embeddings: bool = True) -> np.ndarray:
        vec = self.VECTORS.get(text.lower(), np.array([0.0, 0.0, 1.0], dtype=np.float32))
        if normalize_embeddings:
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
        return vec


@pytest.fixture
def cache() -> SemanticCache:
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    return SemanticCache(
        redis_client=fake_redis,
        threshold=0.9,
        embedder=StubEmbedder(),
    )


def test_lookup_on_empty_cache_is_miss(cache: SemanticCache) -> None:
    assert cache.lookup("capital of france") is None


def test_store_then_lookup_near_paraphrase_is_hit(cache: SemanticCache) -> None:
    cache.store("capital of france", "Paris")

    result = cache.lookup("capital city of france")

    assert result == "Paris"


def test_lookup_dissimilar_query_is_miss(cache: SemanticCache) -> None:
    cache.store("capital of france", "Paris")

    result = cache.lookup("capital of japan")

    assert result is None


def test_clear_removes_all_entries(cache: SemanticCache) -> None:
    cache.store("capital of france", "Paris")
    cache.clear()

    assert cache.lookup("capital of france") is None


def test_higher_threshold_rejects_a_previously_matching_near_paraphrase() -> None:
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    strict_cache = SemanticCache(
        redis_client=fake_redis,
        threshold=0.999,
        embedder=StubEmbedder(),
    )
    strict_cache.store("capital of france", "Paris")

    result = strict_cache.lookup("capital city of france")

    assert result is None
