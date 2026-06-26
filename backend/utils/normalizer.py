"""Phone, address, email, URL, and business name normalization."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

ABBREVIATIONS = {
    "st": "street",
    "str": "street",
    "ave": "avenue",
    "av": "avenue",
    "blvd": "boulevard",
    "rd": "road",
    "dr": "drive",
    "ln": "lane",
    "ct": "court",
    "pl": "place",
    "sq": "square",
    "hwy": "highway",
    "ste": "suite",
    "apt": "apartment",
    "fl": "floor",
    "bldg": "building",
    "n": "north",
    "s": "south",
    "e": "east",
    "w": "west",
    "ne": "northeast",
    "nw": "northwest",
    "se": "southeast",
    "sw": "southwest",
}

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "ref",
    "source",
    "mc_cid",
    "mc_eid",
}


def normalize_phone(phone: str | None) -> str:
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits


def normalize_email(email: str | None) -> str:
    if not email:
        return ""
    return email.strip().lower()


def normalize_business_name(name: str | None) -> str:
    if not name:
        return ""
    text = name.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    words = text.split()
    expanded = []
    for word in words:
        expanded.append(ABBREVIATIONS.get(word, word))
    return " ".join(expanded)


def normalize_address(address: str | None) -> str:
    if not address:
        return ""
    text = address.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    words = text.split()
    expanded = []
    for word in words:
        expanded.append(ABBREVIATIONS.get(word, word))
    return " ".join(expanded)


def extract_city(address: str | None) -> str:
    if not address:
        return ""
    parts = [p.strip() for p in address.split(",")]
    if len(parts) >= 2:
        city_part = parts[-2] if len(parts) >= 3 else parts[-1]
        city = re.sub(r"\d{5}(-\d{4})?", "", city_part).strip()
        return city.lower()
    return ""


def normalize_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url.strip())
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or ""
    query_params = parse_qs(parsed.query, keep_blank_values=False)
    filtered = {
        k: v for k, v in query_params.items() if k.lower() not in TRACKING_PARAMS
    }
    query = urlencode(filtered, doseq=True)
    return urlunparse((scheme, netloc, path, "", query, ""))
