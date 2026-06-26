"""SerpAPI Google Search + Google Maps integration."""

from __future__ import annotations

import logging
from uuid import uuid4

import httpx

from config import Settings, get_settings
from models import BusinessRecord, SearchResult, utcnow
from utils.normalizer import normalize_phone
from utils.source_scorer import score_source_type

logger = logging.getLogger(__name__)

SERPAPI_BASE = "https://serpapi.com/search"


class SerpAPIClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        return bool(self.settings.serpapi_key)

    async def _get(self, params: dict) -> dict:
        params = {**params, "api_key": self.settings.serpapi_key}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(SERPAPI_BASE, params=params)
            resp.raise_for_status()
            return resp.json()

    async def search_urls(self, category: str, location: str) -> list[SearchResult]:
        if not self.enabled:
            return []

        query = f"{category} in {location}"
        results: list[SearchResult] = []
        extra_queries = [
            query,
            f"{category} {location} site:linkedin.com",
            f"{category} {location} site:facebook.com",
            f"{category} {location} directory",
        ]

        for q in extra_queries:
            try:
                data = await self._get({"engine": "google", "q": q, "num": 10})
                for item in data.get("organic_results", []):
                    url = item.get("link", "")
                    if url:
                        st = _classify_url(url)
                        results.append(
                            SearchResult(url=url, source_type=st, priority_score=score_source_type(st))
                        )
            except Exception as exc:
                logger.warning("SerpAPI Google search failed for '%s': %s", q, exc)

        try:
            maps_data = await self._get({"engine": "google_maps", "q": query, "type": "search"})
            for item in maps_data.get("local_results", []):
                maps_link = item.get("place_id_search") or item.get("link", "")
                if maps_link:
                    results.append(
                        SearchResult(
                            url=maps_link,
                            source_type="google_maps",
                            priority_score=score_source_type("google_maps"),
                        )
                    )
        except Exception as exc:
            logger.warning("SerpAPI Maps search failed: %s", exc)

        return results

    async def fetch_local_businesses(
        self, category: str, location: str, job_id: str
    ) -> list[BusinessRecord]:
        if not self.enabled:
            return []

        query = f"{category} in {location}"
        records: list[BusinessRecord] = []
        reliability = score_source_type("google_maps")

        try:
            data = await self._get({"engine": "google_maps", "q": query, "type": "search"})

            for item in data.get("local_results", []):
                name = item.get("title") or item.get("name")
                if not name:
                    continue

                place_url = item.get("place_id_search") or item.get("link") or f"serpapi://maps/{name}"

                phones: list[str] = []
                if item.get("phone"):
                    norm = normalize_phone(item["phone"])
                    if norm:
                        phones.append(norm)

                website = item.get("website")
                address = item.get("address")
                rating = item.get("rating")
                review_count = item.get("reviews")
                if isinstance(review_count, str):
                    review_count = int("".join(c for c in review_count if c.isdigit()) or 0) or None

                working_hours = None
                hours_raw = item.get("hours") or item.get("operating_hours")
                if isinstance(hours_raw, dict):
                    working_hours = {str(k): str(v) for k, v in hours_raw.items()}
                elif isinstance(hours_raw, str) and hours_raw:
                    working_hours = {"hours": hours_raw}

                image_urls: list[str] = []
                if item.get("thumbnail"):
                    image_urls.append(item["thumbnail"])

                services: list[str] = []
                specialties: list[str] = []
                if item.get("type"):
                    specialties.append(item["type"])
                if item.get("types"):
                    specialties.extend(t for t in item["types"] if t not in specialties)

                source_urls: dict[str, list[str]] = {}
                if address:
                    source_urls["address"] = [place_url]
                if phones:
                    source_urls["phone"] = [place_url]
                if website:
                    source_urls["website"] = [place_url]
                if working_hours:
                    source_urls["working_hours"] = [place_url]
                if rating is not None:
                    source_urls["rating"] = [place_url]
                if review_count is not None:
                    source_urls["review_count"] = [place_url]
                if image_urls:
                    source_urls["image_urls"] = [place_url]
                if specialties:
                    source_urls["specialties"] = [place_url]

                records.append(
                    BusinessRecord(
                        id=str(uuid4()),
                        job_id=job_id,
                        business_name=str(name).strip(),
                        address=address,
                        phone=phones,
                        website=website,
                        working_hours=working_hours,
                        rating=float(rating) if rating is not None else None,
                        review_count=review_count,
                        services=services,
                        specialties=specialties,
                        image_urls=image_urls,
                        source_urls=source_urls,
                        source_reliability_score=reliability,
                        raw_sources=[place_url],
                        discovered_at=utcnow(),
                        last_updated=utcnow(),
                    )
                )

            logger.info("SerpAPI: extracted %d local businesses for '%s'", len(records), query)
        except Exception as exc:
            logger.warning("SerpAPI local business fetch failed: %s", exc)

        return records


def _classify_url(url: str) -> str:
    url_lower = url.lower()
    if "yellowpages.com" in url_lower:
        return "yellowpages"
    if "yelp.com" in url_lower:
        return "yelp"
    if "google.com/maps" in url_lower or "maps.google" in url_lower:
        return "google_maps"
    if "linkedin.com" in url_lower:
        return "linkedin"
    if "facebook.com" in url_lower:
        return "directory"
    return "search_result"
