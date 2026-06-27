"""Enrichment agent — cross-reference and enrich business records from official sites."""

from __future__ import annotations

import asyncio
import logging
from urllib.parse import quote_plus, urlparse

import httpx

from agents.search_agent import SearchAgent
from agents.scraper_agent import ScraperAgent
from config import Settings, get_settings
from llm.router import LLMRouter
from models import BusinessRecord, utcnow
from scrapers.base import fetch_page_html, get_user_agent
from utils.field_validator import attach_source, validate_business_record
from utils.source_scorer import score_source_type
from utils.website_parser import parse_website_html

logger = logging.getLogger(__name__)


class EnrichmentAgent:
    def __init__(
        self,
        llm: LLMRouter,
        job_id: str,
        search_agent: SearchAgent | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.llm = llm
        self.job_id = job_id
        self.settings = settings or get_settings()
        self.search_agent = search_agent or SearchAgent(self.settings)
        self.scraper_agent = ScraperAgent(llm, job_id, self.settings)
        self.semaphore = asyncio.Semaphore(5)

    async def enrich(
        self,
        businesses: list[BusinessRecord],
        location: str = "",
    ) -> list[BusinessRecord]:
        enrich_targets: list[BusinessRecord] = []
        incomplete_seen = 0
        for business in businesses:
            if not self._needs_enrichment(business):
                continue
            if (
                self.settings.fast_mode
                and incomplete_seen >= self.settings.max_enrich_businesses
            ):
                continue
            incomplete_seen += 1
            enrich_targets.append(business)

        if enrich_targets:
            results = await asyncio.gather(
                *[self._enrich_one(b, location) for b in enrich_targets],
                return_exceptions=True,
            )
            enriched_map: dict[int, BusinessRecord] = {}
            for business, result in zip(enrich_targets, results):
                if isinstance(result, Exception):
                    logger.error(
                        "Enrichment failed for %s: %s",
                        business.business_name,
                        result,
                    )
                    enriched_map[id(business)] = validate_business_record(business)
                else:
                    enriched_map[id(business)] = validate_business_record(result)

            return [
                enriched_map.get(id(b), validate_business_record(b))
                for b in businesses
            ]

        return [validate_business_record(b) for b in businesses]

    @staticmethod
    def _needs_enrichment(business: BusinessRecord) -> bool:
        return not (
            business.website
            and business.phone
            and business.address
            and business.email
        )

    async def _enrich_one(
        self, business: BusinessRecord, location: str
    ) -> BusinessRecord:
        async with self.semaphore:
            if (
                business.website
                and business.phone
                and business.address
                and business.email
            ):
                business.last_updated = utcnow()
                return business

            website = business.website
            if not website:
                website = await self.search_agent.search_website(
                    business.business_name, location
                )
                if website:
                    business.website = website
                    attach_source(business, "website", website)

            if website:
                await self._enrich_from_website(business, website)

            await self._enrich_social_profiles(business, location)
            business.last_updated = utcnow()
            return business

    async def _enrich_from_website(
        self, business: BusinessRecord, website: str
    ) -> None:
        reliability = score_source_type("official_website")
        business.source_reliability_score = max(
            business.source_reliability_score, reliability
        )

        firecrawl_merged = False
        if (
            not self.settings.fast_mode
            and self.settings.use_firecrawl
            and self.settings.firecrawl_api_key
        ):
            try:
                from scrapers.firecrawl_scraper import FirecrawlScraper

                fc = FirecrawlScraper(self.scraper_agent.llm, business.job_id, self.settings)
                records = await fc.scrape_url(website)
                if records:
                    self._merge_enrichment(business, records[0], website)
                    firecrawl_merged = True
            except Exception as exc:
                logger.warning("Firecrawl enrich failed for %s: %s", website, exc)

        if not firecrawl_merged:
            try:
                html, _ = await fetch_page_html(website, get_user_agent())
                if html:
                    parsed = parse_website_html(html, website)
                    self._merge_parsed(business, parsed, website)
            except Exception as exc:
                logger.warning(
                    "Website parse failed for %s: %s", business.business_name, exc
                )

    def _merge_parsed(
        self, primary: BusinessRecord, parsed: dict, source_url: str
    ) -> None:
        if not primary.address and parsed.get("address"):
            primary.address = parsed["address"]
            attach_source(primary, "address", source_url)

        for phone in parsed.get("phone", []):
            if phone and phone not in primary.phone:
                primary.phone.append(phone)
                attach_source(primary, "phone", source_url)

        for email in parsed.get("email", []):
            if email and email not in primary.email:
                primary.email.append(email)
                attach_source(primary, "email", source_url)

        if not primary.working_hours and parsed.get("working_hours"):
            primary.working_hours = parsed["working_hours"]
            attach_source(primary, "working_hours", source_url)

        for platform, url in (parsed.get("social_profiles") or {}).items():
            if url and not primary.social_profiles.get(platform):
                primary.social_profiles[platform] = url
                attach_source(primary, "social_profiles", url)

        for img in parsed.get("image_urls", []):
            if img and img not in primary.image_urls:
                primary.image_urls.append(img)
                attach_source(primary, "image_urls", source_url)

        if not primary.license_information and parsed.get("license_information"):
            primary.license_information = parsed["license_information"]
            attach_source(primary, "license_information", source_url)

        for cert in parsed.get("certifications", []):
            if cert and cert not in primary.certifications:
                primary.certifications.append(cert)
                attach_source(primary, "certifications", source_url)

        for svc in parsed.get("services", []):
            if svc and svc not in primary.services:
                primary.services.append(svc)
                attach_source(primary, "services", source_url)

    def _merge_enrichment(
        self,
        primary: BusinessRecord,
        enriched: BusinessRecord,
        source_url: str,
    ) -> None:
        if not primary.address and enriched.address:
            primary.address = enriched.address
            attach_source(primary, "address", source_url)

        for phone in enriched.phone:
            if phone and phone not in primary.phone:
                primary.phone.append(phone)
                attach_source(primary, "phone", source_url)

        for email in enriched.email:
            if email and email not in primary.email:
                primary.email.append(email)
                attach_source(primary, "email", source_url)

        if not primary.working_hours and enriched.working_hours:
            primary.working_hours = enriched.working_hours
            attach_source(primary, "working_hours", source_url)

        for svc in enriched.services:
            if svc and svc not in primary.services:
                primary.services.append(svc)
                attach_source(primary, "services", source_url)

        for spec in enriched.specialties:
            if spec and spec not in primary.specialties:
                primary.specialties.append(spec)
                attach_source(primary, "specialties", source_url)

        if enriched.license_information and not primary.license_information:
            primary.license_information = enriched.license_information
            attach_source(primary, "license_information", source_url)

        for cert in enriched.certifications:
            if cert and cert not in primary.certifications:
                primary.certifications.append(cert)
                attach_source(primary, "certifications", source_url)

        for award in enriched.awards:
            if award and award not in primary.awards:
                primary.awards.append(award)
                attach_source(primary, "awards", source_url)

        for platform, url in enriched.social_profiles.items():
            if url and not primary.social_profiles.get(platform):
                primary.social_profiles[platform] = url
                attach_source(primary, "social_profiles", url)

        for img in enriched.image_urls:
            if img and img not in primary.image_urls:
                primary.image_urls.append(img)
                attach_source(primary, "image_urls", source_url)

        if enriched.rating is not None and primary.rating is None:
            primary.rating = enriched.rating
            attach_source(primary, "rating", source_url)

        if enriched.review_count is not None and primary.review_count is None:
            primary.review_count = enriched.review_count
            attach_source(primary, "review_count", source_url)

    async def _enrich_social_profiles(
        self, business: BusinessRecord, location: str
    ) -> None:
        if not self.settings.enrich_social_profiles:
            return

        if business.social_profiles.get("linkedin") and business.social_profiles.get(
            "facebook"
        ):
            return

        name = quote_plus(business.business_name)
        loc = quote_plus(location) if location else ""

        queries = []
        if not business.social_profiles.get("linkedin"):
            queries.append(("linkedin", f"{business.business_name} {location} site:linkedin.com"))
        if not business.social_profiles.get("facebook"):
            queries.append(("facebook", f"{business.business_name} {location} site:facebook.com"))

        for platform, query in queries:
            url = await self._search_profile_url(query, platform)
            if url:
                business.social_profiles[platform] = url
                attach_source(business, "social_profiles", url)

    async def _search_profile_url(self, query: str, platform: str) -> str | None:
        if self.settings.serpapi_enabled:
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.get(
                        "https://serpapi.com/search",
                        params={
                            "engine": "google",
                            "q": query,
                            "num": 5,
                            "api_key": self.settings.serpapi_key,
                        },
                    )
                    if resp.status_code == 200:
                        for item in resp.json().get("organic_results", []):
                            link = item.get("link", "")
                            if self._is_valid_social_url(link, platform):
                                return link.split("?")[0].rstrip("/")
            except Exception as exc:
                logger.warning("SerpAPI social search failed: %s", exc)

        return await self.search_agent.search_social_profile(query, platform)

    @staticmethod
    def _is_valid_social_url(url: str, platform: str) -> bool:
        if not url:
            return False
        lower = url.lower()
        if platform == "linkedin":
            return "linkedin.com/company/" in lower or "linkedin.com/in/" in lower
        if platform == "facebook":
            domain = urlparse(url).netloc.lower()
            return "facebook.com" in domain and "/sharer" not in lower
        return False
