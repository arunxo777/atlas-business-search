"""Business ranking by verification, completeness, rating, and reliability."""

from __future__ import annotations

from models import BusinessRecord

from utils.source_recommendations import recommend_field_sources

VERIFICATION_WEIGHT = {
    "highly_verified": 1.0,
    "verified": 0.75,
    "unverified": 0.4,
    "conflicted": 0.2,
}


def compute_rank_score(business: BusinessRecord) -> float:
    """Higher = better rank. Max theoretical ~100."""
    score = 0.0

    score += VERIFICATION_WEIGHT.get(business.verification_status, 0.4) * 30
    score += business.source_reliability_score * 20
    score += business.non_null_field_count() * 2.5

    if business.rating is not None:
        score += min(business.rating, 5.0) * 4

    if business.review_count is not None and business.review_count > 0:
        score += min(business.review_count / 50, 1.0) * 5

    if business.website:
        score += 5
    if business.phone:
        score += 5
    if business.email:
        score += 3
    if business.working_hours:
        score += 3
    if business.license_information:
        score += 4

    recs = recommend_field_sources(business)
    score += min(len(recs) * 1.5, 10)

    multi_source = len(set(business.raw_sources))
    score += min(multi_source * 2, 8)

    return round(min(score, 100.0), 2)


def rank_businesses(businesses: list[BusinessRecord]) -> list[BusinessRecord]:
    """Sort businesses by rank score descending (best first)."""
    for b in businesses:
        b.rank_score = compute_rank_score(b)
    return sorted(businesses, key=lambda b: b.rank_score, reverse=True)
