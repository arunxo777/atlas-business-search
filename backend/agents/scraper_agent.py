"""Scraper agent — routes URLs to appropriate scrapers with concurrency control."""

from __future__ import annotations

import asyncio
import logging

from config import Settings, get_settings
from llm.router import LLMRouter
from models import BusinessRecord, SearchResult
from scrapers.base import check_robots_txt, fetch_page_html, get_user_agent, random_delay
from scrapers.generic import GenericScraper
from scrapers.google_maps import GoogleMapsScraper
from scrapers.linkedin import LinkedInScraper
from scrapers.listing_parser import extract_from_bing
from scrapers.yellowpages import YellowPagesScraper
from scrapers.yelp import YelpScraper
from utils.url_filters import is_high_value_scrape_url

logger = logging.getLogger(__name__)

_DIRECTORY_TYPES = frozenset(
    {"yellowpages", "yelp", "google_maps", "bing", "google_local"}
)


class ScraperAgent:
    def __init__(
        self,
        llm: LLMRouter,
        job_id: str,
        settings: Settings | None = None,
    ) -> None:
        self.llm = llm
        self.job_id = job_id
        self.settings = settings or get_settings()
        self.semaphore = asyncio.Semaphore(self.settings.max_concurrent_scrapers)
        self.generic = GenericScraper(llm, job_id)
        self.yellowpages = YellowPagesScraper(llm, job_id)
        self.yelp = YelpScraper(llm, job_id)
        self.google_maps = GoogleMapsScraper(llm, job_id)
        self.linkedin = LinkedInScraper(llm, job_id)
        self._firecrawl = None

    def _get_firecrawl(self):
        if self._firecrawl is None:
            from scrapers.firecrawl_scraper import FirecrawlScraper

            self._firecrawl = FirecrawlScraper(
                self.llm, self.job_id, self.settings
            )
        return self._firecrawl

    async def scrape(
        self,
        url: str,
        source_type: str,
        category: str = "",
        location: str = "",
    ) -> list[BusinessRecord]:
        async with self.semaphore:
            try:
                if not self.settings.fast_mode:
                    if source_type == "firecrawl" and self.settings.use_firecrawl:
                        fc = self._get_firecrawl()
                        records = await fc.scrape_url(url)
                        if records:
                            return records

                    if (
                        self.settings.use_firecrawl
                        and self.settings.firecrawl_api_key
                        and source_type in (
                            "official_website",
                            "generic",
                            "search_result",
                            "directory",
                            "google_search",
                        )
                    ):
                        fc = self._get_firecrawl()
                        records = await fc.scrape_url(url)
                        if records:
                            return records
                elif source_type not in _DIRECTORY_TYPES:
                    return []

                if source_type == "yellowpages":
                    if "/search" in url or "/search?" in url:
                        return await self.yellowpages.scrape_search(category, location)
                    return await self.yellowpages.scrape_url(url)
                if source_type == "yelp":
                    if "/search" in url:
                        return await self.yelp.scrape_search(category, location)
                    return await self.yelp.scrape_url(url)
                if source_type == "google_maps":
                    if "/search" in url:
                        return await self.google_maps.scrape_search(category, location)
                    return await self.google_maps.scrape_url(url)
                if source_type == "bing" or "bing.com/search" in url:
                    ua = get_user_agent()
                    await check_robots_txt(url, ua)
                    html, _ = await fetch_page_html(url, ua)
                    return extract_from_bing(html, url, self.job_id)
                if source_type == "linkedin":
                    return await self.linkedin.scrape_url(url)
                if source_type in ("google_search", "google_local"):
                    return await self.generic.scrape_url(url, source_type)
                return await self.generic.scrape_url(url, source_type)
            except Exception as exc:
                logger.error("Scrape failed for %s (%s): %s", url, source_type, exc)
                return []

    async def scrape_all(
        self,
        search_results: list[SearchResult],
        category: str,
        location: str,
        on_business_found=None,
        max_results: int = 500,
    ) -> list[BusinessRecord]:
        all_businesses: list[BusinessRecord] = []

        filtered = [
            sr
            for sr in search_results
            if is_high_value_scrape_url(sr.url, sr.source_type)
        ]
        if self.settings.fast_mode:
            filtered = [
                sr
                for sr in filtered
                if sr.source_type in _DIRECTORY_TYPES
                or any(
                    d in sr.url
                    for d in (
                        "yellowpages.com",
                        "yelp.com",
                        "bing.com/search",
                        "google.com/maps",
                    )
                )
            ]
        filtered = sorted(filtered, key=lambda x: x.priority_score, reverse=True)
        filtered = filtered[: self.settings.max_scrape_urls]

        async def _scrape_one(sr: SearchResult) -> list[BusinessRecord]:
            records = await self.scrape(sr.url, sr.source_type, category, location)
            if on_business_found:
                for record in records:
                    await on_business_found(record)
            return records

        tasks = [_scrape_one(sr) for sr in filtered]

        if (
            not self.settings.fast_mode
            and self.settings.use_firecrawl
            and self.settings.firecrawl_api_key
        ):
            from utils.url_filters import is_firecrawl_supported

            top_urls = [
                sr.url
                for sr in filtered[:12]
                if is_firecrawl_supported(sr.url)
            ]
            if top_urls:
                tasks.append(self._firecrawl_batch(top_urls, on_business_found))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error("Scrape task error: %s", result)
                continue
            all_businesses.extend(result)
            if len(all_businesses) >= max_results:
                break

        return all_businesses[:max_results]

    async def _firecrawl_batch(
        self,
        urls: list[str],
        on_business_found=None,
    ) -> list[BusinessRecord]:
        from scrapers.firecrawl_client import FirecrawlClient

        client = FirecrawlClient(self.settings)
        docs = await client.batch_scrape(urls)
        records: list[BusinessRecord] = []

        for doc in docs:
            markdown = doc.get("markdown", "")
            url = doc.get("url", "")
            if not markdown:
                continue
            extracted = await self.generic.extract_from_content(
                markdown, url, "firecrawl"
            )
            for record in extracted:
                if on_business_found:
                    await on_business_found(record)
                records.append(record)

        return records
