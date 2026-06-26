"""Firecrawl scraper — markdown context for LLM extraction."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from config import Settings, get_settings
from llm.router import LLMRouter
from models import BusinessRecord, SearchResult, utcnow
from scrapers.firecrawl_client import FirecrawlClient
from scrapers.generic import GenericScraper
from utils.field_validator import validate_business_record
from utils.source_scorer import score_source_type

logger = logging.getLogger(__name__)


class FirecrawlScraper:
    def __init__(
        self,
        llm: LLMRouter | None,
        job_id: str,
        settings: Settings | None = None,
    ) -> None:
        self.llm = llm
        self.job_id = job_id
        self.settings = settings or get_settings()
        self.client = FirecrawlClient(self.settings)
        self._generic = GenericScraper(llm, job_id) if llm else None

    async def search_urls(self, category: str, location: str) -> list[SearchResult]:
        query = f"{category} in {location}"
        results = await self.client.search(
            query, limit=self.settings.firecrawl_search_limit
        )
        reliability = score_source_type("firecrawl")
        return [
            SearchResult(
                url=r["url"],
                source_type="firecrawl",
                priority_score=reliability,
            )
            for r in results
            if r.get("url")
        ]

    async def search_businesses(
        self, category: str, location: str
    ) -> list[BusinessRecord]:
        import re

        from utils.normalizer import normalize_phone

        query = f"{category} in {location}"
        results = await self.client.search(
            query, limit=self.settings.firecrawl_search_limit
        )
        records: list[BusinessRecord] = []
        reliability = score_source_type("firecrawl")
        phone_re = re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")

        for item in results:
            name = (item.get("title") or "").strip()
            if not name or len(name) < 2:
                continue
            url = item.get("url", "")
            markdown = item.get("markdown") or item.get("snippet") or ""

            phones: list[str] = []
            for match in phone_re.finditer(markdown):
                norm = normalize_phone(match.group())
                if norm and norm not in phones:
                    phones.append(norm)

            if self._generic and markdown and len(markdown) > 200:
                extracted = await self._generic.extract_from_content(
                    markdown, url, "firecrawl"
                )
                if extracted:
                    records.extend(extracted)
                    continue

            source_urls: dict[str, list[str]] = {}
            if url:
                source_urls["business_name"] = [url]
            if phones:
                source_urls["phone"] = [url]

            records.append(
                BusinessRecord(
                    id=str(uuid4()),
                    job_id=self.job_id,
                    business_name=name,
                    phone=phones,
                    website=url if url.startswith("http") else None,
                    source_urls=source_urls,
                    source_reliability_score=reliability,
                    raw_sources=[url] if url else [],
                    discovered_at=utcnow(),
                    last_updated=utcnow(),
                )
            )

        return [validate_business_record(r) for r in records if r.business_name]

    async def scrape_url(self, url: str) -> list[BusinessRecord]:
        if not self._generic:
            return []
        doc = await self.client.scrape(url)
        if not doc or not doc.get("markdown"):
            return []

        markdown = doc["markdown"]
        source_url = doc.get("url") or url
        records = await self._generic.extract_from_content(
            markdown, source_url, "firecrawl"
        )
        return [validate_business_record(r) for r in records if r.business_name]
