"""Free local business discovery — no paid APIs (replaces SerpAPI)."""

from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import quote_plus

from models import BusinessRecord, utcnow
from scrapers.base import fetch_page_html, get_user_agent, random_delay
from scrapers.listing_parser import (
    extract_from_bing,
    extract_from_google_maps,
    extract_from_yellowpages,
    extract_from_yelp,
)
from utils.field_validator import validate_business_record
from utils.normalizer import normalize_phone

logger = logging.getLogger(__name__)


class FreeLocalSearch:
    """Scrape directory pages directly — 100% free, no API keys."""

    async def fetch_local_businesses(
        self, category: str, location: str, job_id: str
    ) -> list[BusinessRecord]:
        tasks = [
            self._scrape_yellowpages(category, location, job_id),
            self._scrape_yelp(category, location, job_id),
            self._scrape_google_maps(category, location, job_id),
            self._scrape_bing_local(category, location, job_id),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_records: list[BusinessRecord] = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Free local search task failed: %s", result)
                continue
            all_records.extend(result)

        deduped = _dedupe_by_name(all_records)
        validated = [
            validate_business_record(r)
            for r in deduped
            if r.business_name and r.business_name.strip()
        ]
        logger.info(
            "Free local search: %d businesses for '%s in %s'",
            len(validated),
            category,
            location,
        )
        return validated

    async def _scrape_yellowpages(
        self, category: str, location: str, job_id: str
    ) -> list[BusinessRecord]:
        url = (
            f"https://www.yellowpages.com/search?"
            f"search_terms={quote_plus(category)}&"
            f"geo_location_terms={quote_plus(location)}"
        )
        return await self._fetch_and_parse(
            url, extract_from_yellowpages, job_id, "yellowpages"
        )

    async def _scrape_yelp(
        self, category: str, location: str, job_id: str
    ) -> list[BusinessRecord]:
        url = (
            f"https://www.yelp.com/search?"
            f"find_desc={quote_plus(category)}&"
            f"find_loc={quote_plus(location)}"
        )
        return await self._fetch_and_parse(url, extract_from_yelp, job_id, "yelp")

    async def _scrape_google_maps(
        self, category: str, location: str, job_id: str
    ) -> list[BusinessRecord]:
        query = quote_plus(f"{category} {location}")
        url = f"https://www.google.com/maps/search/{query}"
        records = await self._fetch_and_parse(
            url, extract_from_google_maps, job_id, "google_maps"
        )
        if len(records) < 3:
            records.extend(
                _parse_google_maps_embedded(
                    await self._get_html(url), url, job_id
                )
            )
        return records

    async def _scrape_bing_local(
        self, category: str, location: str, job_id: str
    ) -> list[BusinessRecord]:
        url = (
            f"https://www.bing.com/search?q={quote_plus(f'{category} in {location}')}"
        )
        return await self._fetch_and_parse(url, extract_from_bing, job_id, "bing")

    async def _fetch_and_parse(self, url, parser, job_id, label) -> list[BusinessRecord]:
        try:
            await random_delay(0.5, 1.5)
            html = await self._get_html(url)
            if not html:
                return []
            records = parser(html, url, job_id)
            logger.info("Free search [%s]: %d records from %s", label, len(records), url[:60])
            return records
        except Exception as exc:
            logger.warning("Free search [%s] failed: %s", label, exc)
            return []

    async def _get_html(self, url: str) -> str:
        html, _ = await fetch_page_html(url, get_user_agent())
        return html


def _parse_google_maps_embedded(
    html: str, source_url: str, job_id: str
) -> list[BusinessRecord]:
    """Extract business names/phones from embedded Google Maps JSON blobs."""
    from uuid import uuid4

    from utils.source_scorer import score_source_type

    records: list[BusinessRecord] = []
    reliability = score_source_type("google_maps")
    seen: set[str] = set()

    name_pattern = re.compile(
        r'\[\s*"([A-Z][^"]{2,80})"\s*,\s*null\s*,\s*\[\s*null\s*,\s*null'
    )
    phone_pattern = re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")

    for match in name_pattern.finditer(html):
        name = match.group(1).strip()
        if name in seen or any(
            skip in name.lower()
            for skip in ("google", "http", "null", "undefined", "directions")
        ):
            continue
        seen.add(name)

        window = html[match.start() : match.start() + 800]
        phones: list[str] = []
        for phone_match in phone_pattern.finditer(window):
            norm = normalize_phone(phone_match.group())
            if norm and norm not in phones:
                phones.append(norm)

        source_urls: dict[str, list[str]] = {"business_name": [source_url]}
        if phones:
            source_urls["phone"] = [source_url]

        records.append(
            BusinessRecord(
                id=str(uuid4()),
                job_id=job_id,
                business_name=name,
                phone=phones,
                source_urls=source_urls,
                source_reliability_score=reliability,
                raw_sources=[source_url],
                discovered_at=utcnow(),
                last_updated=utcnow(),
            )
        )

    return records[:40]


def _dedupe_by_name(records: list[BusinessRecord]) -> list[BusinessRecord]:
    seen: dict[str, BusinessRecord] = {}
    for record in records:
        key = record.business_name.lower().strip()
        if not key:
            continue
        if key not in seen:
            seen[key] = record
            continue
        existing = seen[key]
        if record.non_null_field_count() > existing.non_null_field_count():
            seen[key] = record
    return list(seen.values())
