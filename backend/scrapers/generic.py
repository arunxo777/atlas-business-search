"""Generic crawl4ai scraper for any URL with LLM extraction."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from llm.prompts import extract_business_prompt
from llm.router import LLMRouter
from models import BusinessRecord, utcnow
from scrapers.base import check_robots_txt, fetch_page_html, get_user_agent, random_delay
from utils.field_validator import validate_business_record
from utils.normalizer import normalize_phone
from utils.source_scorer import score_source_type

logger = logging.getLogger(__name__)


class GenericScraper:
    def __init__(self, llm: LLMRouter, job_id: str) -> None:
        self.llm = llm
        self.job_id = job_id
        self._ua_index = 0

    def _next_ua(self) -> str:
        ua = get_user_agent(self._ua_index)
        self._ua_index += 1
        return ua

    async def scrape_url(
        self,
        url: str,
        source_type: str = "generic",
    ) -> list[BusinessRecord]:
        await random_delay()
        ua = self._next_ua()
        allowed = await check_robots_txt(url, ua)
        if not allowed:
            return []

        try:
            html, markdown = await fetch_page_html(url, ua)
            content = markdown or html
            if not content.strip():
                return []
            return await self.extract_from_content(content, url, source_type)
        except Exception as exc:
            logger.error("Generic scrape error for %s: %s", url, exc)
            return []

    async def extract_from_content(
        self,
        content: str,
        source_url: str,
        source_type: str,
    ) -> list[BusinessRecord]:
        return await self._extract_businesses(content, source_url, source_type)

    async def _extract_businesses(
        self,
        html: str,
        source_url: str,
        source_type: str,
    ) -> list[BusinessRecord]:
        messages = extract_business_prompt(html, query=source_url)
        try:
            data = await self.llm.complete_json(messages)
        except Exception as exc:
            logger.error("LLM extraction failed for %s: %s", source_url, exc)
            return []

        if not data:
            from scrapers.listing_parser import _extract_generic_listings
            return _extract_generic_listings(html, source_url, self.job_id, source_type)

        if isinstance(data, dict):
            if "businesses" in data:
                items = data["businesses"]
            else:
                items = [data]
        elif isinstance(data, list):
            items = data
        else:
            return []

        records: list[BusinessRecord] = []
        reliability = score_source_type(source_type)

        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get("business_name") or item.get("name")
            if not name or not str(name).strip():
                continue

            record = self._dict_to_record(item, source_url, source_type, reliability)
            record.job_id = self.job_id
            record = validate_business_record(record)
            if record.business_name:
                records.append(record)

        return records

    def _dict_to_record(
        self,
        item: dict[str, Any],
        source_url: str,
        source_type: str,
        reliability: float,
    ) -> BusinessRecord:
        phones = item.get("phone") or []
        if isinstance(phones, str):
            phones = [phones] if phones else []
        phones = [normalize_phone(p) for p in phones if p]
        phones = [p for p in phones if p]

        emails = item.get("email") or []
        if isinstance(emails, str):
            emails = [emails] if emails else []

        source_urls: dict[str, list[str]] = {"business_name": [source_url]}
        field_map = {
            "phone": phones,
            "email": [str(e).strip() for e in emails if e],
            "address": item.get("address"),
            "website": item.get("website"),
            "working_hours": item.get("working_hours"),
            "rating": item.get("rating"),
            "review_count": item.get("review_count"),
            "services": item.get("services") or [],
            "specialties": item.get("specialties") or [],
            "license_information": item.get("license_information"),
            "certifications": item.get("certifications") or [],
            "awards": item.get("awards") or [],
            "social_profiles": item.get("social_profiles") or {},
            "image_urls": item.get("image_urls") or [],
        }
        for field, value in field_map.items():
            if value:
                source_urls[field] = [source_url]

        return BusinessRecord(
            id=str(uuid4()),
            job_id=self.job_id,
            business_name=str(item.get("business_name") or item.get("name", "")).strip(),
            address=item.get("address"),
            phone=phones,
            email=[str(e).strip() for e in emails if e],
            website=item.get("website"),
            working_hours=item.get("working_hours"),
            rating=float(item["rating"]) if item.get("rating") is not None else None,
            review_count=int(item["review_count"]) if item.get("review_count") is not None else None,
            services=item.get("services") or [],
            specialties=item.get("specialties") or [],
            license_information=item.get("license_information"),
            certifications=item.get("certifications") or [],
            awards=item.get("awards") or [],
            social_profiles=item.get("social_profiles") or {},
            image_urls=item.get("image_urls") or [],
            source_urls=source_urls,
            source_reliability_score=reliability,
            raw_sources=[source_url],
            discovered_at=utcnow(),
            last_updated=utcnow(),
        )
