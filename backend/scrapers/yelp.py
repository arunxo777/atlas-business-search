"""Yelp async scraper using crawl4ai."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup

from llm.router import LLMRouter
from models import BusinessRecord
from scrapers.generic import GenericScraper
from scrapers.base import check_robots_txt, fetch_page_html, get_user_agent, random_delay
from scrapers.listing_parser import extract_from_yelp

logger = logging.getLogger(__name__)

YELP_BASE = "https://www.yelp.com"


class YelpScraper:
    def __init__(self, llm: LLMRouter, job_id: str) -> None:
        self.llm = llm
        self.job_id = job_id
        self.generic = GenericScraper(llm, job_id)
        self._ua_index = 0

    def build_search_url(self, category: str, location: str) -> str:
        return (
            f"{YELP_BASE}/search?"
            f"find_desc={quote_plus(category)}&"
            f"find_loc={quote_plus(location)}"
        )

    async def scrape_search(
        self,
        category: str,
        location: str,
        max_pages: int = 10,
    ) -> list[BusinessRecord]:
        search_url = self.build_search_url(category, location)
        all_records: list[BusinessRecord] = []
        seen_urls: set[str] = set()

        current_url = search_url
        for page_num in range(max_pages):
            await random_delay()
            ua = get_user_agent(self._ua_index)
            self._ua_index += 1

            if not await check_robots_txt(current_url, ua):
                break

            try:
                html, _ = await fetch_page_html(current_url, ua)
                parsed = extract_from_yelp(html, current_url, self.job_id)
                if parsed:
                    all_records.extend(parsed)
                detail_urls = self._parse_listing_urls(html)
                if not detail_urls:
                    break

                for detail_url in detail_urls:
                    if detail_url in seen_urls:
                        continue
                    seen_urls.add(detail_url)
                    records = await self.generic.scrape_url(detail_url, "yelp")
                    all_records.extend(records)

                next_url = self._parse_next_page(html)
                if not next_url or next_url == current_url:
                    break
                current_url = next_url
            except Exception as exc:
                logger.error("Yelp page %d error: %s", page_num, exc)
                break

        if not all_records:
            records = await self.generic.scrape_url(search_url, "yelp")
            all_records.extend(records)

        return all_records

    def _parse_listing_urls(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "lxml")
        urls: list[str] = []
        for link in soup.select("a[href*='/biz/']"):
            href = link.get("href", "")
            if href and "/biz/" in href:
                full = urljoin(YELP_BASE, href.split("?")[0])
                if full not in urls:
                    urls.append(full)
        return urls[:30]

    def _parse_next_page(self, html: str) -> str | None:
        soup = BeautifulSoup(html, "lxml")
        next_link = soup.select_one("a.next-link, a[aria-label='Next']")
        if next_link and next_link.get("href"):
            return urljoin(YELP_BASE, next_link["href"])
        return None

    async def scrape_url(self, url: str) -> list[BusinessRecord]:
        return await self.generic.scrape_url(url, "yelp")
