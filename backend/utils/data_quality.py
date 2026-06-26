"""Data quality summary for research reports."""

from __future__ import annotations

from models import BusinessRecord, ResearchJob
from utils.source_recommendations import build_global_recommendations


def compute_data_quality(businesses: list[BusinessRecord]) -> dict[str, float]:
    """Return percentage of records that have each field populated."""
    if not businesses:
        return {
            "records_with_website": 0.0,
            "records_with_phone": 0.0,
            "records_with_email": 0.0,
            "records_with_working_hours": 0.0,
            "records_with_license": 0.0,
            "records_with_address": 0.0,
            "records_with_rating": 0.0,
            "records_highly_verified": 0.0,
        }

    n = len(businesses)

    def pct(count: int) -> float:
        return round((count / n) * 100, 1)

    return {
        "records_with_website": pct(sum(1 for b in businesses if b.website)),
        "records_with_phone": pct(sum(1 for b in businesses if b.phone)),
        "records_with_email": pct(sum(1 for b in businesses if b.email)),
        "records_with_working_hours": pct(sum(1 for b in businesses if b.working_hours)),
        "records_with_license": pct(sum(1 for b in businesses if b.license_information)),
        "records_with_address": pct(sum(1 for b in businesses if b.address)),
        "records_with_rating": pct(sum(1 for b in businesses if b.rating is not None)),
        "records_highly_verified": pct(
            sum(1 for b in businesses if b.verification_status == "highly_verified")
        ),
    }


def build_research_report(
    job: ResearchJob,
    businesses: list[BusinessRecord],
    active_sources: list[str] | None = None,
) -> dict:
    """Full research report matching CodeFest PDF requirements."""
    quality = compute_data_quality(businesses)
    source_recommendations = build_global_recommendations(businesses)
    return {
        "search_summary": {
            "query": job.query,
            "category": job.category,
            "location": job.location,
            "businesses_found": job.businesses_found,
            "businesses_verified": job.businesses_verified,
            "duplicates_removed": job.duplicates_removed,
            "sources_searched": job.sources_searched,
            "research_duration_seconds": job.duration_seconds,
            "llm_provider": job.llm_provider,
            "active_sources": active_sources or [],
        },
        "data_quality_summary": quality,
        "source_recommendations": source_recommendations,
        "business_count": len(businesses),
        "top_businesses": [b.model_dump(mode="json") for b in businesses[:10]],
    }
