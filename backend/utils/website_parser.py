"""Deterministic HTML parsing — no LLM, no hallucination."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from utils.normalizer import normalize_phone

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(
    r"(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}"
)
SOCIAL_PATTERNS = {
    "facebook": re.compile(r"https?://(?:www\.)?facebook\.com/[^\s\"'<>]+", re.I),
    "linkedin": re.compile(r"https?://(?:www\.)?linkedin\.com/(?:company|in)/[^\s\"'<>]+", re.I),
    "twitter": re.compile(r"https?://(?:www\.)?(?:twitter|x)\.com/[^\s\"'<>]+", re.I),
    "instagram": re.compile(r"https?://(?:www\.)?instagram\.com/[^\s\"'<>]+", re.I),
}


def parse_website_html(html: str, base_url: str) -> dict[str, Any]:
    """Extract contact and profile data directly from HTML."""
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)

    emails: set[str] = set()
    phones: set[str] = set()
    social: dict[str, str] = {}
    images: list[str] = []
    working_hours: dict[str, str] | None = None
    address: str | None = None
    license_info: str | None = None
    certifications: list[str] = []
    services: list[str] = []

    for a in soup.select("a[href^='mailto:']"):
        href = a.get("href", "")
        email = href.replace("mailto:", "").split("?")[0].strip()
        if email and EMAIL_RE.match(email):
            emails.add(email.lower())

    for a in soup.select("a[href^='tel:']"):
        raw = a.get("href", "").replace("tel:", "").strip()
        norm = normalize_phone(raw)
        if norm:
            phones.add(norm)

    for match in EMAIL_RE.findall(text):
        if not any(skip in match.lower() for skip in ("example.com", "wixpress", "sentry")):
            emails.add(match.lower())

    for match in PHONE_RE.findall(text):
        norm = normalize_phone(match)
        if norm and len(re.sub(r"\D", "", norm)) >= 10:
            phones.add(norm)

    for link in soup.select("a[href]"):
        href = urljoin(base_url, link["href"])
        for platform, pattern in SOCIAL_PATTERNS.items():
            if pattern.match(href) and platform not in social:
                social[platform] = href.split("?")[0].rstrip("/")

    for meta in soup.select('meta[property="og:image"], meta[name="twitter:image"]'):
        content = meta.get("content", "")
        if content:
            images.append(urljoin(base_url, content))

    for img in soup.select("img[src]")[:8]:
        src = urljoin(base_url, img["src"])
        if src.startswith("http") and not any(
            x in src.lower() for x in ("pixel", "tracking", "1x1", "spacer")
        ):
            if src not in images:
                images.append(src)

    structured = _parse_json_ld(soup)
    if structured.get("address"):
        address = structured["address"]
    if structured.get("working_hours"):
        working_hours = structured["working_hours"]
    if structured.get("phones"):
        phones.update(structured["phones"])
    if structured.get("emails"):
        emails.update(structured["emails"])

    for kw in ("license", "licensed", "license #", "license number"):
        if kw in text.lower():
            for line in text.split("."):
                if kw in line.lower() and 10 < len(line) < 200:
                    license_info = line.strip()
                    break

    for cert_kw in ("board certified", "certified", "accreditation"):
        for line in text.split("."):
            if cert_kw in line.lower() and 5 < len(line) < 150:
                cert = line.strip()
                if cert not in certifications:
                    certifications.append(cert)

    for heading in soup.select("h2, h3, h4"):
        label = heading.get_text(strip=True).lower()
        if any(w in label for w in ("service", "specialt", "practice", "treatment")):
            sibling = heading.find_next_sibling("ul")
            if sibling:
                for item in sibling.select("li")[:12]:
                    svc = item.get_text(strip=True)
                    if svc and len(svc) < 80 and svc not in services:
                        services.append(svc)

    return {
        "email": sorted(emails),
        "phone": sorted(phones),
        "address": address,
        "working_hours": working_hours,
        "social_profiles": social,
        "image_urls": images[:10],
        "license_information": license_info,
        "certifications": certifications[:5],
        "services": services[:15],
    }


def _parse_json_ld(soup: BeautifulSoup) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            types = item.get("@type", "")
            if isinstance(types, list):
                type_str = " ".join(types).lower()
            else:
                type_str = str(types).lower()
            if "localbusiness" not in type_str and "organization" not in type_str:
                if item.get("@graph"):
                    for g in item["@graph"]:
                        if isinstance(g, dict):
                            _merge_ld(result, g)
                continue
            _merge_ld(result, item)
    return result


def _merge_ld(result: dict[str, Any], item: dict[str, Any]) -> None:
    addr = item.get("address")
    if isinstance(addr, dict):
        parts = [
            addr.get("streetAddress", ""),
            addr.get("addressLocality", ""),
            addr.get("addressRegion", ""),
            addr.get("postalCode", ""),
        ]
        line = ", ".join(p for p in parts if p)
        if line:
            result["address"] = line
    elif isinstance(addr, str) and addr:
        result["address"] = addr

    tel = item.get("telephone")
    if tel:
        phones = result.setdefault("phones", set())
        if isinstance(tel, list):
            for t in tel:
                n = normalize_phone(str(t))
                if n:
                    phones.add(n)
        else:
            n = normalize_phone(str(tel))
            if n:
                phones.add(n)

    email = item.get("email")
    if email:
        emails = result.setdefault("emails", set())
        if isinstance(email, list):
            emails.update(str(e).lower() for e in email if e)
        else:
            emails.add(str(email).lower())

    hours = item.get("openingHours") or item.get("openingHoursSpecification")
    if hours:
        parsed = _parse_hours(hours)
        if parsed:
            result["working_hours"] = parsed


def _parse_hours(hours: Any) -> dict[str, str] | None:
    if isinstance(hours, str):
        return {"hours": hours}
    if isinstance(hours, list):
        out: dict[str, str] = {}
        for entry in hours:
            if isinstance(entry, str):
                out[f"hours_{len(out)}"] = entry
            elif isinstance(entry, dict):
                day = entry.get("dayOfWeek", "")
                if isinstance(day, list):
                    day = ", ".join(str(d) for d in day)
                opens = entry.get("opens", "")
                closes = entry.get("closes", "")
                if day and opens:
                    out[str(day)] = f"{opens}-{closes}" if closes else str(opens)
        return out or None
    return None
