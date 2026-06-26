"""Source reliability scoring based on source type."""

from __future__ import annotations

SOURCE_SCORES: dict[str, float] = {
    "official_website": 1.0,
    "firecrawl": 0.95,
    "yellowpages": 0.9,
    "yelp": 0.9,
    "serpapi": 0.87,
    "google_maps": 0.85,
    "google_search": 0.88,
    "google_local": 0.9,
    "linkedin": 0.85,
    "directory": 0.8,
    "healthcare_directory": 0.82,
    "legal_directory": 0.82,
    "bing": 0.65,
    "search_result": 0.6,
    "generic": 0.5,
}


def score_source_type(source_type: str) -> float:
    return SOURCE_SCORES.get(source_type, 0.5)


def weighted_average(scores: list[tuple[float, float]]) -> float:
    """Compute weighted average from (value, weight) pairs."""
    if not scores:
        return 0.0
    total_weight = sum(w for _, w in scores)
    if total_weight == 0:
        return 0.0
    return sum(v * w for v, w in scores) / total_weight
