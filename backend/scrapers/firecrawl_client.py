"""Firecrawl API client — https://github.com/firecrawl/firecrawl"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urlparse

import httpx

from config import Settings, get_settings

logger = logging.getLogger(__name__)

DEFAULT_API_URL = "https://api.firecrawl.dev"


class FirecrawlClient:
    """Async wrapper for Firecrawl v2 search + scrape (LLM-ready markdown)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        return bool(
            self.settings.use_firecrawl and self.settings.firecrawl_api_key
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.firecrawl_api_key}",
            "Content-Type": "application/json",
        }

    def _base_url(self) -> str:
        return self.settings.firecrawl_api_url.rstrip("/")

    async def search(
        self, query: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        if not self.enabled:
            return []

        payload = {
            "query": query,
            "limit": limit,
            "scrapeOptions": {"formats": ["markdown"]},
        }

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(
                    f"{self._base_url()}/v2/search",
                    headers=self._headers(),
                    json=payload,
                )
                if resp.status_code != 200:
                    logger.warning(
                        "Firecrawl search failed %s: %s",
                        resp.status_code,
                        resp.text[:300],
                    )
                    return []
                data = resp.json()
        except Exception as exc:
            logger.warning("Firecrawl search error: %s", exc)
            return []

        return _normalize_search_results(data)

    async def scrape(self, url: str) -> dict[str, Any] | None:
        if not self.enabled:
            return None

        payload = {
            "url": url,
            "formats": ["markdown"],
            "onlyMainContent": True,
        }

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(
                    f"{self._base_url()}/v2/scrape",
                    headers=self._headers(),
                    json=payload,
                )
                if resp.status_code != 200:
                    logger.warning(
                        "Firecrawl scrape failed for %s: %s",
                        url,
                        resp.text[:200],
                    )
                    return None
                data = resp.json()
        except Exception as exc:
            logger.warning("Firecrawl scrape error for %s: %s", url, exc)
            return None

        if not data.get("success", True):
            return None

        inner = data.get("data") or data
        markdown = inner.get("markdown") or ""
        metadata = inner.get("metadata") or {}
        return {
            "url": metadata.get("sourceURL") or metadata.get("url") or url,
            "title": metadata.get("title", ""),
            "markdown": markdown,
            "metadata": metadata,
        }

    async def batch_scrape(
        self, urls: list[str], max_concurrent: int = 5
    ) -> list[dict[str, Any]]:
        if not self.enabled or not urls:
            return []

        sem = asyncio.Semaphore(max_concurrent)
        results: list[dict[str, Any]] = []

        async def _one(u: str) -> None:
            async with sem:
                doc = await self.scrape(u)
                if doc and doc.get("markdown"):
                    results.append(doc)

        await asyncio.gather(*[_one(u) for u in urls[:30]])
        return results


def _normalize_search_results(data: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    for key in ("data", "web", "results"):
        block = data.get(key)
        if isinstance(block, list):
            items.extend(block)
        elif isinstance(block, dict):
            for sub in ("web", "results", "items"):
                if isinstance(block.get(sub), list):
                    items.extend(block[sub])

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in items:
        if not isinstance(item, dict):
            continue
        url = item.get("url") or item.get("link") or ""
        if not url or url in seen:
            continue
        if _skip_url(url):
            continue
        seen.add(url)
        normalized.append(
            {
                "url": url,
                "title": item.get("title") or item.get("name") or "",
                "markdown": item.get("markdown") or item.get("description") or "",
                "snippet": item.get("snippet") or item.get("description") or "",
            }
        )
    return normalized


def _skip_url(url: str) -> bool:
    domain = urlparse(url).netloc.lower()
    return any(
        s in domain
        for s in ("google.com/search", "bing.com/search", "facebook.com/login")
    )
