"""Multi-source search agent — DuckDuckGo, directory sites, HTML search."""

from __future__ import annotations

import asyncio
import logging
from urllib.parse import quote_plus, urlparse

import httpx
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

from config import Settings, get_settings
from models import BusinessRecord, SearchResult
from utils.normalizer import normalize_url
from utils.proxy_pool import create_httpx_client
from utils.source_scorer import score_source_type

logger = logging.getLogger(__name__)


class SearchAgent:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def find_urls(self, category: str, location: str) -> list[SearchResult]:
        bing_url = (
            f"https://www.bing.com/search?q={quote_plus(f'{category} in {location}')}"
        )
        tasks = [
            self._search_duckduckgo(category, location),
            self._direct_yellowpages(category, location),
            self._direct_yelp(category, location),
            self._direct_google_maps(category, location),
            self._search_bing(category, location),
        ]
        if self.settings.use_omkar_google_scraper:
            tasks.append(self._search_omkar_google(category, location))
        if self.settings.use_serpapi and self.settings.serpapi_key:
            tasks.append(self._search_serpapi(category, location))
        if self.settings.use_firecrawl and self.settings.firecrawl_api_key:
            tasks.append(self._search_firecrawl(category, location))
        tasks.append(self._category_directories(category, location))

        results_nested = await asyncio.gather(*tasks, return_exceptions=True)

        all_results: list[SearchResult] = [
            SearchResult(url=bing_url, source_type="bing", priority_score=0.85),
        ]
        for result in results_nested:
            if isinstance(result, Exception):
                logger.error("Search task failed: %s", result)
                continue
            all_results.extend(result)

        return self._dedup_urls(all_results)

    async def _search_duckduckgo(
        self, category: str, location: str
    ) -> list[SearchResult]:
        queries = [
            f"{category} in {location}",
            f"{category} {location} site:yelp.com",
            f"{category} {location} site:yellowpages.com",
            f"{category} {location} reviews",
            f"{category} {location} directory",
        ]
        results: list[SearchResult] = []

        def _run_ddg(query: str) -> list[dict]:
            try:
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=10))
            except Exception as exc:
                logger.warning("DDG search failed for '%s': %s", query, exc)
                return []

        for query in queries:
            try:
                await asyncio.sleep(2.5)
                items = await asyncio.to_thread(_run_ddg, query)
                for item in items:
                    url = item.get("href") or item.get("link", "")
                    if not url:
                        continue
                    source_type = self._classify_url(url)
                    results.append(
                        SearchResult(
                            url=url,
                            source_type=source_type,
                            priority_score=score_source_type(source_type),
                        )
                    )
            except Exception as exc:
                logger.error("DDG query error: %s", exc)

        if not results and self.settings.use_serpapi and self.settings.serpapi_key:
            results.extend(await self._search_serpapi(category, location))

        if not results:
            results.extend(await self._search_bing(category, location))
            results.extend(await self._search_bing(f"{category} {location} directory", ""))

        return results

    async def _search_omkar_google(
        self, category: str, location: str
    ) -> list[SearchResult]:
        from scrapers.omkar_google import OmkarGoogleScraper

        client = OmkarGoogleScraper(self.settings)
        return await client.search_urls(category, location)

    async def _search_firecrawl(
        self, category: str, location: str
    ) -> list[SearchResult]:
        from scrapers.firecrawl_scraper import FirecrawlScraper

        scraper = FirecrawlScraper(None, "", self.settings)
        return await scraper.search_urls(category, location)

    async def _search_serpapi(
        self, category: str, location: str
    ) -> list[SearchResult]:
        from scrapers.serpapi_search import SerpAPIClient

        client = SerpAPIClient(self.settings)
        return await client.search_urls(category, location)

    async def fetch_serpapi_businesses(
        self, category: str, location: str, job_id: str
    ) -> list[BusinessRecord]:
        from scrapers.serpapi_search import SerpAPIClient

        client = SerpAPIClient(self.settings)
        return await client.fetch_local_businesses(category, location, job_id)

    async def fetch_free_local_businesses(
        self, category: str, location: str, job_id: str
    ) -> list[BusinessRecord]:
        from scrapers.free_local_search import FreeLocalSearch

        client = FreeLocalSearch()
        return await client.fetch_local_businesses(category, location, job_id)

    async def fetch_bootstrap_businesses(
        self, category: str, location: str, job_id: str
    ) -> list[BusinessRecord]:
        """Bootstrap from all sources simultaneously."""
        tasks = [self.fetch_free_local_businesses(category, location, job_id)]
        if self.settings.use_firecrawl and self.settings.firecrawl_api_key:
            tasks.append(self._fetch_firecrawl_businesses(category, location, job_id))
        if self.settings.use_omkar_google_scraper:
            tasks.append(self._fetch_omkar_google_businesses(category, location, job_id))
        if self.settings.use_serpapi and self.settings.serpapi_key:
            tasks.append(self.fetch_serpapi_businesses(category, location, job_id))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        merged: list[BusinessRecord] = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Bootstrap search failed: %s", result)
                continue
            merged.extend(result)

        return _dedupe_bootstrap(merged)

    async def _fetch_firecrawl_businesses(
        self, category: str, location: str, job_id: str
    ) -> list[BusinessRecord]:
        from scrapers.firecrawl_scraper import FirecrawlScraper

        scraper = FirecrawlScraper(None, job_id, self.settings)
        records = await scraper.search_businesses(category, location)
        for r in records:
            r.job_id = job_id
        return records

    async def _fetch_omkar_google_businesses(
        self, category: str, location: str, job_id: str
    ) -> list[BusinessRecord]:
        from scrapers.omkar_google import OmkarGoogleScraper

        client = OmkarGoogleScraper(self.settings)
        return await client.fetch_businesses(category, location, job_id)

    async def _serpapi_fallback(
        self, category: str, location: str
    ) -> list[SearchResult]:
        query = f"{category} in {location}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "https://serpapi.com/search",
                    params={
                        "q": query,
                        "api_key": self.settings.serpapi_key,
                        "engine": "google",
                        "num": 10,
                    },
                )
                if resp.status_code != 200:
                    return []
                data = resp.json()
                results: list[SearchResult] = []
                for item in data.get("organic_results", []):
                    url = item.get("link", "")
                    if url:
                        source_type = self._classify_url(url)
                        results.append(
                            SearchResult(
                                url=url,
                                source_type=source_type,
                                priority_score=score_source_type(source_type),
                            )
                        )
                return results
        except Exception as exc:
            logger.warning("SerpAPI fallback failed: %s", exc)
            return []

    async def _direct_yellowpages(
        self, category: str, location: str
    ) -> list[SearchResult]:
        url = (
            f"https://www.yellowpages.com/search?"
            f"search_terms={quote_plus(category)}&"
            f"geo_location_terms={quote_plus(location)}"
        )
        return [
            SearchResult(
                url=url,
                source_type="yellowpages",
                priority_score=score_source_type("yellowpages"),
            )
        ]

    async def _direct_yelp(self, category: str, location: str) -> list[SearchResult]:
        url = (
            f"https://www.yelp.com/search?"
            f"find_desc={quote_plus(category)}&"
            f"find_loc={quote_plus(location)}"
        )
        return [
            SearchResult(
                url=url,
                source_type="yelp",
                priority_score=score_source_type("yelp"),
            )
        ]

    async def _direct_google_maps(
        self, category: str, location: str
    ) -> list[SearchResult]:
        query = quote_plus(f"{category} {location}")
        url = f"https://www.google.com/maps/search/{query}"
        return [
            SearchResult(
                url=url,
                source_type="google_maps",
                priority_score=score_source_type("google_maps"),
            )
        ]

    async def _search_bing(self, category: str, location: str) -> list[SearchResult]:
        query = quote_plus(f"{category} in {location}")
        url = f"https://www.bing.com/search?q={query}"
        results: list[SearchResult] = []

        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
                )
            }
            async with await create_httpx_client(timeout=15.0, headers=headers) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return results

                soup = BeautifulSoup(resp.text, "lxml")
                for li in soup.select("li.b_algo, .b_algo, li[class*='algo']"):
                    link = li.select_one("a[href^='http']")
                    if link and link.get("href"):
                        href = link["href"]
                        if "bing.com" in href or "microsoft.com" in href:
                            continue
                        source_type = self._classify_url(href)
                        results.append(
                            SearchResult(
                                url=href,
                                source_type=source_type,
                                priority_score=score_source_type(source_type),
                            )
                        )
                for cite in soup.select("cite, .b_attribution"):
                    text = cite.get_text(strip=True)
                    if text and "." in text and " " not in text:
                        href = f"https://{text.split(' ')[0]}"
                        source_type = self._classify_url(href)
                        results.append(
                            SearchResult(
                                url=href,
                                source_type=source_type,
                                priority_score=score_source_type(source_type),
                            )
                        )
        except Exception as exc:
            logger.warning("Bing scrape failed: %s", exc)

        return results

    @staticmethod
    def _classify_url(url: str) -> str:
        domain = urlparse(url).netloc.lower()
        if "yellowpages.com" in domain:
            return "yellowpages"
        if "yelp.com" in domain:
            return "yelp"
        if "google.com/maps" in url or "maps.google" in domain:
            return "google_maps"
        if "linkedin.com" in domain:
            return "linkedin"
        if any(d in domain for d in ("directory", "biz", "local")):
            return "directory"
        if "bing.com" in domain:
            return "bing"
        if "google.com/search" in url:
            return "google_search"
        return "search_result"

    def _dedup_urls(self, results: list[SearchResult]) -> list[SearchResult]:
        seen: set[str] = set()
        deduped: list[SearchResult] = []
        for r in sorted(results, key=lambda x: x.priority_score, reverse=True):
            normalized = normalize_url(r.url)
            if normalized not in seen:
                seen.add(normalized)
                deduped.append(
                    SearchResult(
                        url=r.url,
                        source_type=r.source_type,
                        priority_score=r.priority_score,
                    )
                )
        return deduped

    async def _category_directories(
        self, category: str, location: str
    ) -> list[SearchResult]:
        from scrapers.directories import get_directory_urls

        return get_directory_urls(category, location)

    async def search_social_profile(self, query: str, platform: str) -> str | None:
        def _run() -> list[dict]:
            try:
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=5))
            except Exception:
                return []

        items = await asyncio.to_thread(_run)
        for item in items:
            url = item.get("href") or item.get("link", "")
            if not url:
                continue
            lower = url.lower()
            if platform == "linkedin" and (
                "linkedin.com/company/" in lower or "linkedin.com/in/" in lower
            ):
                return url.split("?")[0].rstrip("/")
            if platform == "facebook" and "facebook.com" in lower and "/sharer" not in lower:
                return url.split("?")[0].rstrip("/")
        return None

    async def search_website(self, business_name: str, location: str) -> str | None:
        query = f"{business_name} {location} official website"

        def _run() -> list[dict]:
            try:
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=5))
            except Exception:
                return []

        items = await asyncio.to_thread(_run)
        skip_domains = {
            "yelp.com", "yellowpages.com", "facebook.com",
            "linkedin.com", "google.com", "bing.com",
        }
        for item in items:
            url = item.get("href") or item.get("link", "")
            if not url:
                continue
            domain = urlparse(url).netloc.lower()
            if not any(skip in domain for skip in skip_domains):
                return url
        return None


def _dedupe_bootstrap(records: list[BusinessRecord]) -> list[BusinessRecord]:
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
