"""RapidAPI Google Scraper API client (from omkarcloud/google-scraper)."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

FAILED_DUE_TO_CREDITS_EXHAUSTED = "FAILED_DUE_TO_CREDITS_EXHAUSTED"
FAILED_DUE_TO_NOT_SUBSCRIBED = "FAILED_DUE_TO_NOT_SUBSCRIBED"
FAILED_DUE_TO_NO_KEY = "FAILED_DUE_TO_NO_KEY"
FAILED_DUE_TO_UNKNOWN_ERROR = "FAILED_DUE_TO_UNKNOWN_ERROR"

RAPIDAPI_HOST = "google-scraper.p.rapidapi.com"
RAPIDAPI_BASE = f"https://{RAPIDAPI_HOST}/search/"


def _do_request(link: str, api_key: str, retry_count: int = 3) -> dict[str, Any]:
    if retry_count == 0:
        return {"data": None, "error": FAILED_DUE_TO_UNKNOWN_ERROR}

    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": RAPIDAPI_HOST,
    }
    try:
        response = requests.get(link, headers=headers, timeout=30)
        response_data = response.json()
    except Exception as exc:
        logger.warning("RapidAPI Google request failed: %s", exc)
        return {"data": None, "error": FAILED_DUE_TO_UNKNOWN_ERROR}

    if response.status_code in (200, 404):
        message = response_data.get("message", "")
        if "API doesn't exists" in message:
            return {"data": None, "error": FAILED_DUE_TO_UNKNOWN_ERROR}
        return {"data": response_data, "error": None}

    message = response_data.get("message", "")
    if "exceeded the MONTHLY quota" in message:
        return {"data": None, "error": FAILED_DUE_TO_CREDITS_EXHAUSTED}
    if "exceeded the rate limit" in message or "many requests" in message:
        time.sleep(2)
        return _do_request(link, api_key, retry_count - 1)
    if "You are not subscribed to this API." in message:
        return {"data": None, "error": FAILED_DUE_TO_NOT_SUBSCRIBED}

    logger.warning("RapidAPI Google error %s: %s", response.status_code, message)
    return {"data": None, "error": FAILED_DUE_TO_UNKNOWN_ERROR}


def search_via_rapidapi(query: str, api_key: str, max_results: int = 20) -> list[dict[str, Any]]:
    """Search Google via RapidAPI (50 free requests/month on free plan)."""
    if not api_key:
        return []

    qp = {"query": query}
    link = f"{RAPIDAPI_BASE}?query={requests.utils.quote(query)}"
    request_data = {"params": {**qp, "link": link}, "key": api_key}

    result = _do_request(link, api_key)
    if result.get("error"):
        logger.warning(
            "RapidAPI Google search failed for '%s': %s", query, result["error"]
        )
        return []

    initial_results = (result.get("data") or {}).get("results") or []

    while (result.get("data") or {}).get("next") and len(initial_results) < max_results:
        next_link = result["data"]["next"]
        result = _do_request(next_link, api_key)
        if result.get("error"):
            break
        more = (result.get("data") or {}).get("results") or []
        initial_results.extend(more)

    return initial_results[:max_results]
