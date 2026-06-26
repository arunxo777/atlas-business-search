"""Free Google search via Botasaurus browser (anti-detection)."""

from __future__ import annotations

import logging
import re
from urllib.parse import quote_plus, urlparse

from bs4 import BeautifulSoup
from botasaurus.browser import Driver, browser

logger = logging.getLogger(__name__)

SKIP_DOMAINS = (
    "google.com",
    "gstatic.com",
    "youtube.com",
    "accounts.google",
    "support.google",
    "policies.google",
)


from config import get_settings
from utils.proxy_pool import get_proxy_url


def _browser_proxy(_data: dict) -> str | None:
    return get_proxy_url()


@browser(
    headless=True,
    block_images=True,
    reuse_driver=True,
    close_on_crash=True,
    output=None,
    raise_exception=False,
    proxy=_browser_proxy,
)
def _scrape_google_browser(driver: Driver, data: dict) -> list[dict]:
    query = data["query"]
    max_results = int(data.get("max", 20))
    search_url = (
        f"https://www.google.com/search?q={quote_plus(query)}"
        f"&num={min(max_results, 20)}&hl=en"
    )

    try:
        driver.google_get(search_url, accept_google_cookies=True, timeout=45)
    except Exception as exc:
        logger.warning("Botasaurus Google navigation failed: %s", exc)
        return []

    if "/sorry/" in driver.current_url:
        logger.warning("Google blocked the search request (captcha)")
        return []

    html = driver.page_html or ""
    return _parse_google_html(html, max_results)


def _parse_google_html(html: str, max_results: int) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    results: list[dict] = []
    seen_urls: set[str] = set()

    for block in soup.select("div.g, div[data-hveid]"):
        link_el = block.select_one("a[href^='http']")
        title_el = block.select_one("h3")
        if not link_el or not title_el:
            continue

        href = link_el.get("href", "").split("#")[0]
        title = title_el.get_text(strip=True)
        if not href or not title or _should_skip(href):
            continue
        if href in seen_urls:
            continue

        snippet_el = block.select_one("div[data-sncf], span.st, div.VwiC3b")
        snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""

        seen_urls.add(href)
        results.append(
            {
                "title": title,
                "link": href,
                "snippet": snippet,
                "source": "google_organic",
            }
        )
        if len(results) >= max_results:
            return results

    for card in soup.select("[data-cid], div.rllt__details, div.VkpGBb"):
        name_el = card.select_one("div[role='heading'], span.OSrXXb, div.qBF1Pd")
        if not name_el:
            continue
        name = name_el.get_text(strip=True)
        if not name or len(name) < 2:
            continue

        address = None
        for span in card.select("span"):
            text = span.get_text(strip=True)
            if re.search(r"\d{5}|\b[A-Z]{2}\b", text) and len(text) > 8:
                address = text
                break

        rating = None
        rating_el = card.select_one("span[aria-label*='star'], span.yi40Hd")
        if rating_el:
            match = re.search(r"(\d+\.?\d*)", rating_el.get_text() or rating_el.get("aria-label", ""))
            if match:
                rating = float(match.group(1))

        phones: list[str] = []
        for match in re.finditer(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", card.get_text()):
            phones.append(match.group())

        maps_link = f"https://www.google.com/maps/search/?api=1&query={quote_plus(name)}"
        results.append(
            {
                "title": name,
                "link": maps_link,
                "snippet": address or "",
                "address": address,
                "phone": phones[:1],
                "rating": rating,
                "source": "google_local",
            }
        )
        if len(results) >= max_results:
            break

    return results[:max_results]


def _should_skip(url: str) -> bool:
    domain = urlparse(url).netloc.lower()
    return any(skip in domain for skip in SKIP_DOMAINS)


def search_via_browser(query: str, max_results: int = 20) -> list[dict]:
    """Run Botasaurus browser scrape in sync context."""
    return _scrape_google_browser({"query": query, "max": max_results}) or []
