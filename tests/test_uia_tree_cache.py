"""Tests for UIA tree cache."""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"))


def test_descendant_cache_reuses_within_ttl():
    from detection.uia_tree_cache import get_descendants, invalidate_all

    invalidate_all()
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        return ["a", "b"]

    first = get_descendants(123, fetch, ttl_s=2.0)
    second = get_descendants(123, fetch, ttl_s=2.0)
    assert first == second == ["a", "b"]
    assert calls["n"] == 1


def test_invalidate_forces_refetch():
    from detection.uia_tree_cache import get_descendants, invalidate, invalidate_all

    invalidate_all()
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        return [1]

    get_descendants(5, fetch)
    invalidate(5)
    get_descendants(5, fetch)
    assert calls["n"] == 2
