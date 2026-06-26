"""Strip fields without source attribution — anti-hallucination policy (source-bound fields only)."""

from __future__ import annotations

from models import BusinessRecord


def validate_business_record(record: BusinessRecord) -> BusinessRecord:
    """Remove any field value that lacks at least one source URL entry."""
    su = record.source_urls

    if record.phone and not su.get("phone"):
        record.phone = []
    if record.email and not su.get("email"):
        record.email = []
    if record.address and not su.get("address"):
        record.address = None
    if record.website and not su.get("website"):
        record.website = None
    if record.working_hours and not su.get("working_hours"):
        record.working_hours = None
    if record.rating is not None and not su.get("rating"):
        record.rating = None
    if record.review_count is not None and not su.get("review_count"):
        record.review_count = None
    if record.license_information and not su.get("license_information"):
        record.license_information = None
    if record.services and not su.get("services"):
        record.services = []
    if record.specialties and not su.get("specialties"):
        record.specialties = []
    if record.certifications and not su.get("certifications"):
        record.certifications = []
    if record.awards and not su.get("awards"):
        record.awards = []
    if record.social_profiles and not su.get("social_profiles"):
        record.social_profiles = {}
    if record.image_urls and not su.get("image_urls"):
        record.image_urls = []

    if not record.business_name or not record.business_name.strip():
        record.business_name = ""

    return record


def attach_source(
    record: BusinessRecord,
    field: str,
    source_url: str,
) -> None:
    """Register a source URL for a field before setting its value."""
    if source_url and source_url not in record.source_urls.get(field, []):
        record.source_urls.setdefault(field, []).append(source_url)
    if source_url and source_url not in record.raw_sources:
        record.raw_sources.append(source_url)
