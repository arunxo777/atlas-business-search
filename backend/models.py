"""Pydantic v2 models for the Business Research Agent."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


VerificationStatus = Literal[
    "highly_verified", "verified", "unverified", "conflicted"
]

JobStatus = Literal[
    "queued",
    "searching",
    "scraping",
    "enriching",
    "deduplicating",
    "complete",
    "failed",
]


class BusinessRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    job_id: str
    business_name: str
    address: str | None = None
    phone: list[str] = Field(default_factory=list)
    email: list[str] = Field(default_factory=list)
    website: str | None = None
    working_hours: dict[str, str] | None = None
    rating: float | None = None
    review_count: int | None = None
    services: list[str] = Field(default_factory=list)
    specialties: list[str] = Field(default_factory=list)
    license_information: str | None = None
    certifications: list[str] = Field(default_factory=list)
    awards: list[str] = Field(default_factory=list)
    social_profiles: dict[str, str] = Field(default_factory=dict)
    image_urls: list[str] = Field(default_factory=list)
    source_urls: dict[str, list[str]] = Field(default_factory=dict)
    verification_status: VerificationStatus = "unverified"
    verification_details: dict[str, Any] = Field(default_factory=dict)
    source_reliability_score: float = 0.0
    rank_score: float = 0.0
    rank_position: int = 0
    raw_sources: list[str] = Field(default_factory=list)
    discovered_at: datetime = Field(default_factory=utcnow)
    last_updated: datetime = Field(default_factory=utcnow)

    def non_null_field_count(self) -> int:
        count = 0
        if self.business_name:
            count += 1
        if self.address:
            count += 1
        if self.phone:
            count += 1
        if self.email:
            count += 1
        if self.website:
            count += 1
        if self.working_hours:
            count += 1
        if self.rating is not None:
            count += 1
        if self.review_count is not None:
            count += 1
        if self.services:
            count += 1
        if self.specialties:
            count += 1
        if self.license_information:
            count += 1
        if self.certifications:
            count += 1
        if self.awards:
            count += 1
        return count


class ResearchJob(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    query: str
    category: str = ""
    location: str = ""
    status: JobStatus = "queued"
    progress_pct: float = 0.0
    businesses_found: int = 0
    businesses_verified: int = 0
    duplicates_removed: int = 0
    sources_searched: int = 0
    duration_seconds: float | None = None
    llm_provider: str = "auto"
    created_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None
    error: str | None = None


class ResearchRequest(BaseModel):
    query: str
    max_results: int = 100
    llm_provider: str | None = None


class ResearchResponse(BaseModel):
    job_id: str
    status: str
    cached: bool = False


class SSEEvent(BaseModel):
    event: str
    data: dict[str, Any]


class SearchResult(BaseModel):
    url: str
    source_type: str
    priority_score: float = 0.6


class ResearchReport(BaseModel):
    search_summary: dict[str, Any]
    data_quality_summary: dict[str, float]
    business_count: int
    top_businesses: list[dict[str, Any]] = Field(default_factory=list)


class PaginatedResults(BaseModel):
    items: list[BusinessRecord]
    total: int
    page: int
    page_size: int
    total_pages: int


class HealthResponse(BaseModel):
    status: str
    db: str
    llm: str


class LLMStatusResponse(BaseModel):
    provider: str
    model: str
    latency_ms: float | None = None
    available_providers: list[str] = Field(default_factory=list)
