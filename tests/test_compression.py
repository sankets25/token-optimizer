"""Unit tests for the rule-based prompt compressor. Pure string logic, no
network or model dependency."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.compression import compress


def test_strips_filler_phrase_and_words() -> None:
    result = compress("Could you please kindly explain what is the capital of France?")

    assert result == "explain what is the capital of France?"


def test_strips_multiple_filler_words() -> None:
    result = compress("I just really want to know the answer, honestly.")

    assert "just" not in result.lower()
    assert "really" not in result.lower()
    assert "honestly" not in result.lower()


def test_leaves_query_without_filler_unchanged() -> None:
    query = "What is the capital of Japan?"

    assert compress(query) == query


def test_collapses_whitespace_left_behind_by_stripped_phrase() -> None:
    result = compress("Can you  tell me the time?")

    assert "  " not in result


def test_falls_back_to_original_when_stripping_leaves_nothing() -> None:
    query = "Please kindly."

    assert compress(query) == query
