"""Google Maps results page scraper (no API)."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

from llm.router import LLMRouter
from models import BusinessRecord
from scrapers.base import check_robots_txt, fetch_page_html, get_user_agent, random_delay
from scrapers.generic import GenericScraper
from scrapers.listing_parser import extract_from_google_maps

logger = logging.getLogger(__name__)


class GoogleMapsScraper:
    def __init__(self, llm: LLMRouter, job_id: str) -> None:
        self.llm = llm
        self.job_id = job_id
        self.generic = GenericScraper(llm, job_id)

    def build_search_url(self, category: str, location: str) -> str:
        query = f"{category}+{location}".replace(" ", "+")
        return f"https://www.google.com/maps/search/{quote_plus(query)}"

    async def scrape_search(self, category: str, location: str) -> list[BusinessRecord]:
        url = self.build_search_url(category, location)
        await random_delay()
        ua = get_user_agent()
        await check_robots_txt(url, ua)
        try:
            html, _ = await fetch_page_html(url, ua)
            records = extract_from_google_maps(html, url, self.job_id)
            if records:
                return records
        except Exception as exc:
            logger.warning("Google Maps HTML parse failed: %s", exc)
        return await self.generic.scrape_url(url, "google_maps")

    async def scrape_url(self, url: str) -> list[BusinessRecord]:
        ua = get_user_agent()
        try:
            html, _ = await fetch_page_html(url, ua)
            records = extract_from_google_maps(html, url, self.job_id)
            if records:
                return records
        except Exception as exc:
            logger.warning("Google Maps scrape failed: %s", exc)
        return await self.generic.scrape_url(url, "google_maps")
