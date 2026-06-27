"""Proxy pool integration — https://github.com/naiba/proxy-in-a-box"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from config import Settings, get_settings

logger = logging.getLogger(__name__)

_CAPTCHA_MARKERS = (
    "/sorry/",
    "captcha",
    "unusual traffic",
    "cf-challenge",
    "just a moment",
    "access denied",
    "blocked",
)


def get_proxy_url(settings: Settings | None = None) -> str | None:
    """HTTP proxy URL for httpx / Playwright (proxy-in-a-box gateway)."""
    s = settings or get_settings()
    if not s.use_proxy_pool:
        return None
    return s.proxy_pool_http or None


def playwright_proxy(settings: Settings | None = None) -> dict[str, str] | None:
    url = get_proxy_url(settings)
    if not url:
        return None
    return {"server": url}


async def fetch_rotating_proxy(settings: Settings | None = None) -> str | None:
    """Fetch one validated proxy from proxy-in-a-box management API."""
    s = settings or get_settings()
    if not s.use_proxy_pool or not s.proxy_pool_api:
        return get_proxy_url(s)

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{s.proxy_pool_api.rstrip('/')}/get")
            if resp.status_code != 200:
                logger.debug("Proxy pool unavailable — using direct connection")
                return None
            text = resp.text.strip()
            if text.startswith("http"):
                return text
            data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            if isinstance(data, dict):
                for key in ("proxy", "url", "address"):
                    val = data.get(key)
                    if isinstance(val, str) and val.startswith("http"):
                        return val
    except Exception as exc:
        logger.debug("Proxy pool /get failed: %s", exc)

    return None


async def get_pool_stats(settings: Settings | None = None) -> dict[str, Any]:
    s = settings or get_settings()
    if not s.proxy_pool_api:
        return {"enabled": s.use_proxy_pool, "healthy": False}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(f"{s.proxy_pool_api.rstrip('/')}/api/stats")
            if resp.status_code == 200:
                stats = resp.json()
                return {"enabled": True, "healthy": True, "stats": stats}
    except Exception as exc:
        logger.debug("Proxy pool stats failed: %s", exc)
    return {"enabled": s.use_proxy_pool, "healthy": False}


def is_blocked_content(html: str, url: str = "") -> bool:
    lower = (html or "").lower()
    url_lower = (url or "").lower()
    if "/sorry/" in url_lower:
        return True
    return any(marker in lower for marker in _CAPTCHA_MARKERS)


def httpx_client_kwargs(
    settings: Settings | None = None,
    *,
    timeout: float = 30.0,
    use_proxy: bool = True,
    **extra: Any,
) -> dict[str, Any]:
    """Build kwargs for httpx.AsyncClient with optional proxy pool."""
    kwargs: dict[str, Any] = {
        "timeout": timeout,
        "follow_redirects": True,
        **extra,
    }
    if use_proxy:
        proxy = get_proxy_url(settings)
        if proxy:
            kwargs["proxy"] = proxy
    return kwargs


async def create_httpx_client(
    settings: Settings | None = None,
    *,
    use_proxy: bool = True,
    **kwargs: Any,
) -> httpx.AsyncClient:
    client_kwargs = httpx_client_kwargs(settings, use_proxy=use_proxy, **kwargs)
    return httpx.AsyncClient(**client_kwargs)
