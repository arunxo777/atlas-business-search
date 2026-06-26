"""Category-specific industry and professional directory URLs."""

from __future__ import annotations

from urllib.parse import quote_plus

from models import SearchResult
from utils.source_scorer import score_source_type

HEALTHCARE_KEYWORDS = (
    "doctor", "physician", "cardio", "dentist", "dental", "surgeon",
    "health", "medical", "clinic", "hospital", "orthodont", "pediatr",
)
LEGAL_KEYWORDS = (
    "lawyer", "attorney", "legal", "law firm", "solicitor", "barrister",
)
CONTRACTOR_KEYWORDS = (
    "contractor", "plumber", "roof", "electrician", "hvac", "remodel",
    "construction", "handyman",
)


def get_directory_urls(category: str, location: str) -> list[SearchResult]:
    """Return relevant directory search URLs based on business category."""
    cat = category.lower()
    loc = quote_plus(location)
    term = quote_plus(category)
    results: list[SearchResult] = []

    def add(url: str, source_type: str) -> None:
        results.append(
            SearchResult(
                url=url,
                source_type=source_type,
                priority_score=score_source_type(source_type),
            )
        )

    if any(k in cat for k in HEALTHCARE_KEYWORDS):
        add(
            f"https://www.healthgrades.com/search?what={term}&where={loc}",
            "healthcare_directory",
        )
        add(
            f"https://www.zocdoc.com/search?address={loc}&query={term}",
            "healthcare_directory",
        )
        add(
            f"https://www.vitals.com/search?query={term}&location={loc}",
            "healthcare_directory",
        )

    if any(k in cat for k in LEGAL_KEYWORDS):
        add(
            f"https://www.avvo.com/search?query={term}&loc={loc}",
            "legal_directory",
        )
        add(
            f"https://www.lawyers.com/search/?q={term}&loc={loc}",
            "legal_directory",
        )
        add(
            f"https://www.martindale.com/search/attorneys/?term={term}&loc={loc}",
            "legal_directory",
        )

    if any(k in cat for k in CONTRACTOR_KEYWORDS):
        add(
            f"https://www.bbb.org/search?find_text={term}&find_loc={loc}",
            "directory",
        )
        add(
            f"https://www.angi.com/companylist/{loc.replace('+', '-')}/{term.replace('+', '-')}.htm",
            "directory",
        )

    add(
        f"https://www.bbb.org/search?find_text={term}&find_loc={loc}",
        "directory",
    )

    return results
