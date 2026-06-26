"""Unified Google search — RapidAPI (omkarcloud) or free Botasaurus browser."""

from __future__ import annotations

import logging
from typing import Any

from integrations.omkar_google_scraper.browser_search import search_via_browser
from integrations.omkar_google_scraper.rapidapi_search import search_via_rapidapi

logger = logging.getLogger(__name__)


def search_google(
    query: str,
    *,
    max_results: int = 20,
    rapidapi_key: str = "",
    prefer_rapidapi: bool = True,
) -> list[dict[str, Any]]:
    """
    Search Google using omkarcloud/google-scraper integration.

    - With RAPIDAPI_GOOGLE_KEY: uses RapidAPI Google Scraper (50 free/mo)
    - Without key: uses Botasaurus browser scrape (100% free)
    """
    results: list[dict[str, Any]] = []

    if prefer_rapidapi and rapidapi_key:
        results = search_via_rapidapi(query, rapidapi_key, max_results)
        if results:
            logger.info(
                "Omkar Google (RapidAPI): %d results for '%s'", len(results), query
            )
            return results
        logger.info("RapidAPI returned no results, falling back to browser scrape")

    results = search_via_browser(query, max_results)
    logger.info("Omkar Google (browser): %d results for '%s'", len(results), query)
    return results
