"""Shared scraper utilities — user agents, delays, robots.txt, crawl4ai helper."""

from __future__ import annotations

import asyncio
import logging
import random
import sys
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from crawl4ai import AsyncWebCrawler, CacheMode
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy

from config import get_settings
from utils.proxy_pool import (
    create_httpx_client,
    fetch_rotating_proxy,
    is_blocked_content,
    playwright_proxy,
)

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

_robots_cache: dict[str, RobotFileParser] = {}


async def random_delay(min_s: float = 1.0, max_s: float = 3.0) -> None:
    await asyncio.sleep(random.uniform(min_s, max_s))


def get_user_agent(index: int | None = None) -> str:
    if index is not None:
        return USER_AGENTS[index % len(USER_AGENTS)]
    return random.choice(USER_AGENTS)


async def check_robots_txt(url: str, user_agent: str | None = None) -> bool:
    """Check robots.txt and log if disallowed. Always returns True (warn-only)."""
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    if base not in _robots_cache:
        rp = RobotFileParser()
        robots_url = f"{base}/robots.txt"
        try:
            async with await create_httpx_client(timeout=8.0) as client:
                resp = await client.get(robots_url)
                if resp.status_code == 200:
                    rp.parse(resp.text.splitlines())
                else:
                    rp.parse([])
        except Exception:
            rp.parse([])
        _robots_cache[base] = rp

    ua = user_agent or USER_AGENTS[0]
    allowed = _robots_cache[base].can_fetch(ua, url)
    if not allowed:
        logger.warning("robots.txt disallows fetching (proceeding anyway): %s", url)
    return True


async def fetch_page_html_httpx(
    url: str,
    user_agent: str,
    proxy_url: str | None = None,
) -> tuple[str, str]:
    """Lightweight HTTP fetch with optional proxy pool."""
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }
    kwargs: dict = {"timeout": 45.0, "follow_redirects": True, "headers": headers}
    if proxy_url:
        kwargs["proxy"] = proxy_url
    elif get_settings().use_proxy_pool:
        from utils.proxy_pool import get_proxy_url

        p = get_proxy_url()
        if p:
            kwargs["proxy"] = p

    async with httpx.AsyncClient(**kwargs) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text
        return html, html


async def fetch_page_html(url: str, user_agent: str) -> tuple[str, str]:
    """Fetch page HTML — Playwright via proxy pool, retry on captcha."""
    settings = get_settings()
    proxy_url = None
    if settings.use_proxy_pool:
        proxy_url = await fetch_rotating_proxy(settings)

    if sys.platform == "win32":
        html, md = await asyncio.to_thread(
            _fetch_sync_playwright, url, user_agent, proxy_url
        )
    else:
        html, md = await _fetch_async_playwright(url, user_agent, proxy_url)

    if html and not is_blocked_content(html, url):
        return html, md

    if settings.use_proxy_pool:
        logger.warning("Blocked/captcha detected for %s — retrying with rotated proxy", url)
        proxy_url = await fetch_rotating_proxy(settings)
        if sys.platform == "win32":
            html, md = await asyncio.to_thread(
                _fetch_sync_playwright, url, user_agent, proxy_url
            )
        else:
            html, md = await _fetch_async_playwright(url, user_agent, proxy_url)
        if html and not is_blocked_content(html, url):
            return html, md

    try:
        return await fetch_page_html_httpx(url, user_agent, proxy_url)
    except Exception as exc:
        logger.warning("httpx fetch failed for %s: %s", url, exc)
        return "", ""


async def _fetch_async_playwright(
    url: str, user_agent: str, proxy_url: str | None
) -> tuple[str, str]:
    try:
        proxy_cfg = {"server": proxy_url} if proxy_url else playwright_proxy()
        strategy = AsyncPlaywrightCrawlerStrategy(
            headless=True,
            user_agent=user_agent,
        )
        async with AsyncWebCrawler(crawler_strategy=strategy) as crawler:
            result = await crawler.arun(
                url=url,
                user_agent=user_agent,
                cache_mode=CacheMode.BYPASS,
                verbose=False,
                page_timeout=45000,
                proxy=proxy_cfg,
            )
            if result.success:
                html = result.html or result.cleaned_html or ""
                markdown = result.markdown
                if hasattr(markdown, "raw_markdown"):
                    markdown = markdown.raw_markdown
                markdown_text = str(markdown or html)
                if html.strip():
                    return html, markdown_text
    except Exception as exc:
        logger.warning("Playwright fetch failed for %s: %s", url, exc)
    return "", ""


def _fetch_sync_playwright(
    url: str, user_agent: str, proxy_url: str | None = None
) -> tuple[str, str]:
    from playwright.sync_api import sync_playwright

    settings = get_settings()
    proxy_cfg = None
    if proxy_url:
        proxy_cfg = {"server": proxy_url}
    elif settings.use_proxy_pool:
        proxy_cfg = playwright_proxy(settings)

    with sync_playwright() as p:
        launch_kwargs: dict = {"headless": True}
        if proxy_cfg:
            launch_kwargs["proxy"] = proxy_cfg
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page(user_agent=user_agent)
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2500)
        html = page.content()
        current = page.url
        browser.close()

    if is_blocked_content(html, current):
        logger.warning("Captcha/block on %s (url=%s)", url, current)
    return html, html
