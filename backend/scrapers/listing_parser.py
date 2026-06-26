"""Extract business listings from directory HTML without LLM."""

from __future__ import annotations

import re
from uuid import uuid4

from bs4 import BeautifulSoup

from models import BusinessRecord, utcnow
from utils.normalizer import normalize_phone
from utils.source_scorer import score_source_type


def extract_from_yellowpages(html: str, source_url: str, job_id: str) -> list[BusinessRecord]:
    soup = BeautifulSoup(html, "lxml")
    records: list[BusinessRecord] = []
    reliability = score_source_type("yellowpages")

    for card in soup.select(".result, .search-results .v-card, div[class*='result']"):
        name_el = card.select_one(".business-name, a.business-name, h2 a, h3 a")
        if not name_el:
            continue
        name = name_el.get_text(strip=True)
        if not name:
            continue

        address_el = card.select_one(
            ".adr, .street-address, .locality, div[class*='address']"
        )
        address = address_el.get_text(" ", strip=True) if address_el else None

        phones: list[str] = []
        for phone_el in card.select(".phones, .phone, a[href^='tel:']"):
            raw = phone_el.get_text(strip=True) or phone_el.get("href", "").replace("tel:", "")
            norm = normalize_phone(raw)
            if norm and norm not in phones:
                phones.append(norm)

        website_el = card.select_one("a.track-visit-website, a[href*='website']")
        website = website_el.get("href") if website_el else None

        rating_el = card.select_one(".ratings, .rating")
        rating = None
        if rating_el:
            match = re.search(r"(\d+\.?\d*)", rating_el.get_text())
            if match:
                rating = float(match.group(1))

        source_urls: dict[str, list[str]] = {}
        if address:
            source_urls["address"] = [source_url]
        if phones:
            source_urls["phone"] = [source_url]
        if website:
            source_urls["website"] = [source_url]

        records.append(
            BusinessRecord(
                id=str(uuid4()),
                job_id=job_id,
                business_name=name,
                address=address,
                phone=phones,
                website=website,
                rating=rating,
                source_urls=source_urls,
                source_reliability_score=reliability,
                raw_sources=[source_url],
                discovered_at=utcnow(),
                last_updated=utcnow(),
            )
        )

    if not records:
        records = _extract_generic_listings(html, source_url, job_id, "yellowpages")

    return records


def extract_from_yelp(html: str, source_url: str, job_id: str) -> list[BusinessRecord]:
    soup = BeautifulSoup(html, "lxml")
    records: list[BusinessRecord] = []
    reliability = score_source_type("yelp")

    for card in soup.select("[data-testid='serp-ia-card'], .businessName, li[class*='border']"):
        name_el = card.select_one("a[href*='/biz/'], h3 a, h4 a")
        if not name_el:
            continue
        name = name_el.get_text(strip=True)
        if not name:
            continue

        address_el = card.select_one("address, p[class*='address']")
        address = address_el.get_text(strip=True) if address_el else None

        rating_el = card.select_one("[aria-label*='star'], .i-stars")
        rating = None
        if rating_el:
            label = rating_el.get("aria-label", "") or rating_el.get_text()
            match = re.search(r"(\d+\.?\d*)", label)
            if match:
                rating = float(match.group(1))

        source_urls = {"address": [source_url]} if address else {}
        records.append(
            BusinessRecord(
                id=str(uuid4()),
                job_id=job_id,
                business_name=name,
                address=address,
                rating=rating,
                source_urls=source_urls,
                source_reliability_score=reliability,
                raw_sources=[source_url],
                discovered_at=utcnow(),
                last_updated=utcnow(),
            )
        )

    if not records:
        records = _extract_generic_listings(html, source_url, job_id, "yelp")

    return records


def _extract_generic_listings(
    html: str, source_url: str, job_id: str, source_type: str
) -> list[BusinessRecord]:
    """Fallback: find phone numbers and nearby text as business hints."""
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text("\n", strip=True)
    records: list[BusinessRecord] = []
    reliability = score_source_type(source_type)

    phone_pattern = re.compile(
        r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
    )
    seen_phones: set[str] = set()

    for match in phone_pattern.finditer(text):
        phone = normalize_phone(match.group())
        if not phone or phone in seen_phones:
            continue
        seen_phones.add(phone)

        start = max(0, match.start() - 120)
        context = text[start : match.start()].strip()
        lines = [l.strip() for l in context.split("\n") if l.strip()]
        name = lines[-1] if lines else f"Business ({phone})"
        if len(name) > 80 or len(name) < 3:
            continue

        records.append(
            BusinessRecord(
                id=str(uuid4()),
                job_id=job_id,
                business_name=name,
                phone=[phone],
                source_urls={"phone": [source_url]},
                source_reliability_score=reliability,
                raw_sources=[source_url],
                discovered_at=utcnow(),
                last_updated=utcnow(),
            )
        )

    return records[:30]


def extract_from_bing(html: str, source_url: str, job_id: str) -> list[BusinessRecord]:
    """Extract business names and snippets from Bing search results page."""
    soup = BeautifulSoup(html, "lxml")
    records: list[BusinessRecord] = []
    reliability = score_source_type("bing")

    for li in soup.select("li.b_algo, .b_algo"):
        title_el = li.select_one("h2 a, a[href^='http']")
        if not title_el:
            continue
        name = title_el.get_text(strip=True)
        if not name or len(name) < 3:
            continue

        snippet_el = li.select_one(".b_caption p, p, .b_lineclamp2")
        snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""
        href = title_el.get("href", source_url)

        phones: list[str] = []
        for match in re.finditer(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", snippet):
            norm = normalize_phone(match.group())
            if norm:
                phones.append(norm)

        address = None
        if snippet and any(c.isdigit() for c in snippet):
            address = snippet[:200] if len(snippet) > 20 else None

        source_urls: dict[str, list[str]] = {"website": [href]}
        if phones:
            source_urls["phone"] = [source_url]
        if address:
            source_urls["address"] = [source_url]

        records.append(
            BusinessRecord(
                id=str(uuid4()),
                job_id=job_id,
                business_name=name,
                address=address,
                phone=phones,
                website=href if href.startswith("http") else None,
                source_urls=source_urls,
                source_reliability_score=reliability,
                raw_sources=[source_url, href],
                discovered_at=utcnow(),
                last_updated=utcnow(),
            )
        )

    return records[:20]


def extract_from_google_maps(html: str, source_url: str, job_id: str) -> list[BusinessRecord]:
    return _extract_generic_listings(html, source_url, job_id, "google_maps")
