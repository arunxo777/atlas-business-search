"""URL helpers — skip low-value or unsupported scrape targets."""

from __future__ import annotations

from urllib.parse import urlparse

_BLOCKED_DOMAINS = (
    "linkedin.com",
    "facebook.com",
    "fb.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "pinterest.com",
)

_SKIP_PATH_MARKERS = (
    "google.com/search",
    "bing.com/search",
    "facebook.com/login",
    "linkedin.com/posts/",
    "linkedin.com/jobs/",
    "facebook.com/photo.php",
    "facebook.com/posts/",
    "facebook.com/videos/",
)


def is_blocked_scrape_domain(url: str) -> bool:
    domain = urlparse(url).netloc.lower()
    return any(blocked in domain for blocked in _BLOCKED_DOMAINS)


def is_firecrawl_supported(url: str) -> bool:
    if not url:
        return False
    lower = url.lower()
    if any(marker in lower for marker in _SKIP_PATH_MARKERS):
        return False
    return not is_blocked_scrape_domain(url)


def is_high_value_scrape_url(url: str, source_type: str) -> bool:
    """Prefer directories and business sites over social profiles."""
    if is_blocked_scrape_domain(url):
        return False
    if source_type in (
        "yellowpages",
        "yelp",
        "google_maps",
        "bing",
        "directory",
        "firecrawl",
        "official_website",
    ):
        return True
    domain = urlparse(url).netloc.lower()
    if any(
        d in domain
        for d in (
            "yellowpages.com",
            "yelp.com",
            "google.com/maps",
            "justdial.com",
            "indiamart.com",
            "sulekha.com",
        )
    ):
        return True
    if source_type in ("linkedin", "facebook", "search_result"):
        return False
    return True
