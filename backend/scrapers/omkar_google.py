"""Omkar Google Scraper adapter — maps results to our models."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from config import Settings, get_settings
from integrations.omkar_google_scraper import search_google
from models import BusinessRecord, SearchResult, utcnow
from utils.normalizer import normalize_phone
from utils.source_scorer import score_source_type

logger = logging.getLogger(__name__)


class OmkarGoogleScraper:
    """Wraps https://github.com/omkarcloud/google-scraper for our pipeline."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def search_urls(self, category: str, location: str) -> list[SearchResult]:
        query = f"{category} in {location}"
        raw = await self._run_search(query)
        return self._to_search_results(raw)

    async def fetch_businesses(
        self, category: str, location: str, job_id: str
    ) -> list[BusinessRecord]:
        query = f"{category} in {location}"
        raw = await self._run_search(query)
        return self._to_business_records(raw, job_id)

    async def _run_search(self, query: str) -> list[dict[str, Any]]:
        max_results = min(self.settings.google_scraper_max_results, 30)

        def _sync() -> list[dict[str, Any]]:
            return search_google(
                query,
                max_results=max_results,
                rapidapi_key=self.settings.rapidapi_google_key,
                prefer_rapidapi=self.settings.use_rapidapi_google,
            )

        try:
            return await asyncio.to_thread(_sync)
        except Exception as exc:
            logger.error("Omkar Google search failed: %s", exc)
            return []

    def _to_search_results(self, items: list[dict[str, Any]]) -> list[SearchResult]:
        results: list[SearchResult] = []
        seen: set[str] = set()

        for item in items:
            url = item.get("link") or item.get("url") or ""
            if not url or url in seen:
                continue
            seen.add(url)
            source_type = _classify_url(url, item.get("source", ""))
            results.append(
                SearchResult(
                    url=url,
                    source_type=source_type,
                    priority_score=score_source_type(source_type),
                )
            )
        return results

    def _to_business_records(
        self, items: list[dict[str, Any]], job_id: str
    ) -> list[BusinessRecord]:
        records: list[BusinessRecord] = []
        seen: set[str] = set()

        for item in items:
            name = (item.get("title") or item.get("name") or "").strip()
            if not name or name.lower() in seen:
                continue
            seen.add(name.lower())

            link = item.get("link") or item.get("url") or ""
            source = item.get("source", "google_search")
            reliability = score_source_type(
                "google_local" if source == "google_local" else "google_search"
            )

            phones: list[str] = []
            for p in item.get("phone") or []:
                norm = normalize_phone(str(p))
                if norm:
                    phones.append(norm)
            if not phones and item.get("phone"):
                norm = normalize_phone(str(item["phone"]))
                if norm:
                    phones.append(norm)

            address = item.get("address") or item.get("snippet")
            rating = item.get("rating")
            if rating is not None:
                try:
                    rating = float(rating)
                except (TypeError, ValueError):
                    rating = None

            source_urls: dict[str, list[str]] = {"business_name": [link or "google_search"]}
            if address:
                source_urls["address"] = [link]
            if phones:
                source_urls["phone"] = [link]
            if rating is not None:
                source_urls["rating"] = [link]

            records.append(
                BusinessRecord(
                    id=str(uuid4()),
                    job_id=job_id,
                    business_name=name,
                    address=address if isinstance(address, str) and len(address) > 5 else None,
                    phone=phones,
                    website=link if _looks_like_website(link) else None,
                    rating=rating,
                    source_urls=source_urls,
                    source_reliability_score=reliability,
                    raw_sources=[link] if link else ["google_search"],
                    discovered_at=utcnow(),
                    last_updated=utcnow(),
                )
            )
        return records


def _classify_url(url: str, source: str) -> str:
    if source == "google_local" or "google.com/maps" in url:
        return "google_maps"
    lower = url.lower()
    if "yelp.com" in lower:
        return "yelp"
    if "yellowpages.com" in lower:
        return "yellowpages"
    if "linkedin.com" in lower:
        return "linkedin"
    if "facebook.com" in lower:
        return "directory"
    return "google_search"


def _looks_like_website(url: str) -> bool:
    if not url.startswith("http"):
        return False
    domain = urlparse(url).netloc.lower()
    skip = ("google.com", "bing.com", "facebook.com", "yelp.com", "yellowpages.com")
    return not any(s in domain for s in skip)
