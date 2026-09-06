"""Fuzzy text matching for UIA element discovery (WinApp parity)."""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any


def fuzzy_score(query: str, candidate: str) -> float:
    """Return similarity in [0, 1] between *query* and *candidate*."""
    if not query or not candidate:
        return 0.0
    q = query.lower().strip()
    c = candidate.lower().strip()
    if q == c:
        return 1.0
    if q in c:
        return 0.85 + 0.15 * min(1.0, len(q) / max(len(c), 1))
    # Word-reorder tolerance: compare sorted token sets
    q_tokens = sorted(q.split())
    c_tokens = sorted(c.split())
    if q_tokens and q_tokens == c_tokens:
        return 0.9
    return SequenceMatcher(None, q, c).ratio()


def fuzzy_match_elements(
    elements: list[dict[str, Any]],
    query: str,
    *,
    min_score: float = 0.55,
    max_results: int = 50,
) -> list[dict[str, Any]]:
    """Rank *elements* by fuzzy match against name and automation_id."""
    if not query.strip():
        return elements[:max_results]

    scored: list[tuple[float, dict[str, Any]]] = []
    for elem in elements:
        name = str(elem.get("name") or "")
        aid = str(elem.get("automation_id") or "")
        score = max(fuzzy_score(query, name), fuzzy_score(query, aid))
        if score >= min_score:
            row = dict(elem)
            row["fuzzy_score"] = round(score, 4)
            scored.append((score, row))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [row for _, row in scored[:max_results]]
