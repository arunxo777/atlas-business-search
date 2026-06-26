"""Per-field source recommendations — which source is best for which data."""

from __future__ import annotations

from models import BusinessRecord

# Ordered best → worst per field (CodeFest + practical reliability)
FIELD_SOURCE_PRIORITY: dict[str, list[str]] = {
    "business_name": [
        "official_website",
        "google_maps",
        "firecrawl",
        "yelp",
        "yellowpages",
        "serpapi",
        "google_local",
        "linkedin",
    ],
    "phone": [
        "official_website",
        "google_maps",
        "firecrawl",
        "yellowpages",
        "yelp",
        "serpapi",
        "google_local",
        "bing",
    ],
    "email": [
        "official_website",
        "firecrawl",
        "linkedin",
        "google_search",
        "directory",
    ],
    "address": [
        "google_maps",
        "serpapi",
        "official_website",
        "firecrawl",
        "yellowpages",
        "yelp",
    ],
    "website": [
        "official_website",
        "firecrawl",
        "google_maps",
        "yelp",
        "yellowpages",
    ],
    "working_hours": [
        "google_maps",
        "serpapi",
        "official_website",
        "firecrawl",
        "yelp",
    ],
    "rating": [
        "google_maps",
        "yelp",
        "serpapi",
        "firecrawl",
        "yellowpages",
    ],
    "review_count": [
        "google_maps",
        "yelp",
        "serpapi",
        "firecrawl",
    ],
    "services": [
        "official_website",
        "firecrawl",
        "yelp",
        "healthcare_directory",
        "legal_directory",
    ],
    "specialties": [
        "official_website",
        "firecrawl",
        "google_maps",
        "healthcare_directory",
    ],
    "license_information": [
        "official_website",
        "firecrawl",
        "healthcare_directory",
        "legal_directory",
        "government",
    ],
    "certifications": [
        "official_website",
        "firecrawl",
        "linkedin",
        "healthcare_directory",
    ],
    "social_profiles": [
        "linkedin",
        "firecrawl",
        "official_website",
        "google_search",
    ],
    "image_urls": [
        "official_website",
        "firecrawl",
        "google_maps",
        "yelp",
    ],
}

SOURCE_LABELS: dict[str, str] = {
    "official_website": "Official Website",
    "google_maps": "Google Maps",
    "firecrawl": "Firecrawl",
    "yelp": "Yelp",
    "yellowpages": "Yellow Pages",
    "serpapi": "SerpAPI",
    "google_local": "Google Local",
    "google_search": "Google Search",
    "linkedin": "LinkedIn",
    "bing": "Bing",
    "healthcare_directory": "Healthcare Directory",
    "legal_directory": "Legal Directory",
    "directory": "Industry Directory",
    "government": "Government License DB",
}


def _infer_source_type(url: str) -> str:
    lower = url.lower()
    if "yelp.com" in lower:
        return "yelp"
    if "yellowpages.com" in lower:
        return "yellowpages"
    if "google.com/maps" in lower or "maps.google" in lower:
        return "google_maps"
    if "linkedin.com" in lower:
        return "linkedin"
    if "healthgrades" in lower or "zocdoc" in lower:
        return "healthcare_directory"
    if "avvo.com" in lower or "lawyers.com" in lower:
        return "legal_directory"
    if "serpapi" in lower:
        return "serpapi"
    if "firecrawl" in lower:
        return "firecrawl"
    return "official_website"


def recommend_field_sources(business: BusinessRecord) -> dict[str, dict[str, str]]:
    """For each populated field, recommend the best source used."""
    recs: dict[str, dict[str, str]] = {}

    for field, urls in business.source_urls.items():
        if field == "business_name" or not urls:
            continue

        used_types = {_infer_source_type(u) for u in urls}
        priority = FIELD_SOURCE_PRIORITY.get(field, [])
        best = None
        for src in priority:
            if src in used_types:
                best = src
                break
        if not best and used_types:
            best = next(iter(used_types))

        if best:
            best_url = urls[0]
            for u in urls:
                if _infer_source_type(u) == best:
                    best_url = u
                    break
            recs[field] = {
                "recommended_source": SOURCE_LABELS.get(best, best),
                "source_type": best,
                "url": best_url,
                "reason": f"Highest reliability for {field} among collected sources",
            }

    return recs


def build_global_recommendations(
    businesses: list[BusinessRecord],
) -> dict[str, str]:
    """Which source type to prefer per field for this research job."""
    field_counts: dict[str, dict[str, int]] = {}

    for business in businesses:
        for field, urls in business.source_urls.items():
            if not urls:
                continue
            field_counts.setdefault(field, {})
            for url in urls:
                st = _infer_source_type(url)
                field_counts[field][st] = field_counts[field].get(st, 0) + 1

    global_recs: dict[str, str] = {}
    for field, priority in FIELD_SOURCE_PRIORITY.items():
        counts = field_counts.get(field, {})
        if not counts:
            global_recs[field] = SOURCE_LABELS.get(priority[0], priority[0])
            continue
        scored = [
            (s, counts.get(s, 0) * (len(priority) - priority.index(s)))
            for s in priority
            if counts.get(s, 0) > 0
        ]
        best = max(scored, key=lambda x: x[1])[0] if scored else priority[0]
        global_recs[field] = SOURCE_LABELS.get(best, best)

    return global_recs


def attach_recommendations(businesses: list[BusinessRecord]) -> list[BusinessRecord]:
    for b in businesses:
        recs = recommend_field_sources(b)
        if recs:
            b.verification_details["field_source_recommendations"] = recs
    return businesses
