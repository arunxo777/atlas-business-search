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

logger = logging.getLogger(__name__)


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

        async def _scrape_one(sr: SearchResult) -> list[BusinessRecord]:
            records = await self.scrape(sr.url, sr.source_type, category, location)
            if on_business_found:
                for record in records:
                    await on_business_found(record)
            return records

        tasks = [_scrape_one(sr) for sr in search_results]

        if self.settings.use_firecrawl and self.settings.firecrawl_api_key:
            top_urls = [
                sr.url
                for sr in sorted(
                    search_results,
                    key=lambda x: x.priority_score,
                    reverse=True,
                )[:20]
            ]
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
